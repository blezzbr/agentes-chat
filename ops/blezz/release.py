"""Version selection and release notes for the Blezz GitHub workflow."""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess


FORK = "blezzbr/blezz-agentes-chat"
UPSTREAM = "agentes-chat/agentes-chat"
VERSION = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
BLEZZ = re.compile("blezz-v" + VERSION + r"-r([1-9][0-9]*)")
INDEPENDENT = re.compile("blezz-v" + VERSION)
OFFICIAL = re.compile("v" + VERSION)
LEGACY = re.compile("blezz-v" + VERSION + r"\.([0-9]+)")


def gh(path, *, pages=False):
    command = ["gh", "api", path]
    if pages:
        command.extend(["--paginate", "--slurp"])
    result = json.loads(subprocess.check_output(command, text=True))
    return [item for page in result for item in page] if pages else result


def released(repo):
    return [
        release
        for release in gh(f"repos/{repo}/releases?per_page=100", pages=True)
        if not release["draft"] and not release["prerelease"]
    ]


def version(pattern, tag):
    match = pattern.fullmatch(tag)
    return tuple(map(int, match.groups())) if match else None


def latest(tags, pattern):
    matches = [tag for tag in tags if version(pattern, tag) is not None]
    return max(matches, key=lambda tag: version(pattern, tag), default=None)


def next_tag(tags, upstream):
    base = version(OFFICIAL, f"v{upstream}")
    if base is None:
        raise ValueError("Invalid upstream version.")
    previous = latest(tags, BLEZZ)
    revision = 1
    if previous:
        installed = version(BLEZZ, previous)
        if base < installed[:3]:
            raise ValueError(f"The upstream base cannot go backwards from {previous}.")
        if base == installed[:3]:
            revision = installed[3] + 1
    return f"blezz-v{upstream}-r{revision}"


def read_at(ref, path):
    local = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True
    )
    if local.returncode == 0:
        return json.loads(local.stdout)
    if ref == "HEAD":
        raise ValueError(f"Missing {path} in {ref}.")
    remote = gh(f"repos/{FORK}/contents/{path}?ref={ref}")
    return json.loads(base64.b64decode(remote["content"]))


def upstream_at(ref):
    # The pre-SemVer staging release already declared its base in package.json.
    path = "apps/server/package.json" if LEGACY.fullmatch(ref) else "ops/blezz/upstream.json"
    return read_at(ref, path)["version"]


def upstream_range(releases, previous, current):
    by_version = {
        parsed: release
        for release in releases
        if (parsed := version(OFFICIAL, release["tag_name"])) is not None
    }
    target = version(OFFICIAL, f"v{current}")
    lower = version(OFFICIAL, f"v{previous}") if previous else None
    if target not in by_version or (previous and (lower not in by_version or lower > target)):
        raise ValueError("The upstream release range is unknown or goes backwards.")
    if lower == target:
        return []
    return [
        by_version[item] for item in sorted(by_version)
        if item <= target and (item > lower if lower else item == target)
    ]


def write_notes(args):
    published = released(FORK)
    tags = [release["tag_name"] for release in published]
    target = version(BLEZZ, args.tag)
    if args.existing:
        if args.tag not in tags:
            raise ValueError(f"{args.tag} is not published.")
        earlier = [tag for tag in tags if tag != args.tag]
        if target:
            earlier = [
                tag for tag in earlier
                if not BLEZZ.fullmatch(tag) or version(BLEZZ, tag) < target
            ]
        else:
            earlier = [tag for tag in earlier if not BLEZZ.fullmatch(tag)]
    else:
        if args.tag in tags:
            raise ValueError(f"{args.tag} is already published.")
        earlier = tags

    baseline = latest(earlier, BLEZZ) or latest(earlier, INDEPENDENT) or latest(earlier, LEGACY)
    previous_base = upstream_at(baseline) if baseline else None
    metadata = read_at(args.ref or "HEAD", "ops/blezz/upstream.json")
    current = metadata["version"]
    if previous_base and version(OFFICIAL, f"v{previous_base}") > version(OFFICIAL, f"v{current}"):
        raise ValueError(f"The upstream base cannot go backwards from {baseline}.")

    if not args.existing or target:
        expected = next_tag(earlier, current)
        if expected != args.tag:
            raise ValueError(f"Expected {expected}, received {args.tag}.")
    changes_path = Path(args.changes or f"ops/blezz/changes/{args.tag}.json")
    entries = json.loads(changes_path.read_text())["changes"]
    if not isinstance(entries, list) or any(not isinstance(e, str) or not e.strip() for e in entries):
        raise ValueError("Fork changes must be a list of nonempty descriptions.")

    official_releases = released(UPSTREAM)
    officials = upstream_range(official_releases, previous_base, current)
    same_base = not officials
    if same_base:
        officials = upstream_range(official_releases, None, current)
    if any(not (release["body"] or "").strip() for release in officials):
        raise ValueError("An upstream release in the range is missing its official notes.")

    intro = [
        f"## Base oficial",
        f"Agentes.chat [v{current}](https://github.com/{UPSTREAM}/releases/tag/v{current}), commit `{metadata['revision']}`.",
    ]
    if baseline:
        intro += [
            f"Base anterior da Blezz: [`{baseline}`](https://github.com/{FORK}/releases/tag/{baseline}), Agentes.chat `v{previous_base}`.",
        ]
    if args.image:
        intro.append(f"Imagem Linux amd64 e arm64: `{args.image}`.")
    own = ["## Mudanças da Blezz"]
    own += [f"- {item.strip()}" for item in entries] or ["Sem mudanças próprias nesta release."]
    upstream = ["## Notas oficiais do Agentes.chat"]
    upstream_sources = []
    if same_base:
        unchanged = "A base oficial permaneceu na mesma versão. As notas abaixo ficam como referência."
        upstream.extend(["", unchanged])
        upstream_sources.append(unchanged)
    for release in officials:
        upstream_sources.append(f"- [{release['tag_name']}]({release['html_url']})")
        upstream += [
            "",
            f"### Agentes.chat {release['tag_name']}",
            "",
            f"[Release oficial]({release['html_url']})",
            "",
            release["body"].strip(),
        ]

    front = "\n\n".join(["\n\n".join(intro), "\n\n".join(own)]) + "\n\n"
    full = front + "\n".join(upstream) + "\n"
    Path(args.output).write_text(full)
    if args.github_body:
        # GitHub limits a release body. Keep the complete text as a release asset either way.
        body = full if len(full.encode()) <= 110_000 else (
            front + "## Notas oficiais do Agentes.chat\n\n"
            + "\n".join(upstream_sources)
            + "\n\nAs notas completas estão no arquivo da release `release-notes.md`.\n"
        )
        Path(args.github_body).write_text(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("next-tag")
    notes = commands.add_parser("notes")
    notes.add_argument("tag")
    notes.add_argument("--ref")
    notes.add_argument("--changes")
    notes.add_argument("--image")
    notes.add_argument("--existing", action="store_true")
    notes.add_argument("--output", required=True)
    notes.add_argument("--github-body")
    args = parser.parse_args()
    try:
        if args.command == "next-tag":
            tags = [release["tag_name"] for release in released(FORK)]
            current = json.loads(Path("ops/blezz/upstream.json").read_text())["version"]
            baseline = latest(tags, BLEZZ) or latest(tags, INDEPENDENT) or latest(tags, LEGACY)
            if baseline and version(OFFICIAL, f"v{upstream_at(baseline)}") > version(OFFICIAL, f"v{current}"):
                raise ValueError(f"The upstream base cannot go backwards from {baseline}.")
            print(next_tag(tags, current))
        else:
            write_notes(args)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
