"""Prepare a reviewable update from the latest official server release."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from release import FORK, OFFICIAL, UPSTREAM, gh, latest, released, upstream_range, version


METADATA = Path("ops/blezz/upstream.json")
MAIN = "main"
WORKFLOWS = ".github/workflows"


def git(*args, capture=False, check=True):
    result = subprocess.run(["git", *args], check=check, text=True, capture_output=capture)
    return result.stdout.strip() if capture and check else result


def record_base(tag, revision):
    metadata = json.loads(METADATA.read_text())
    current = tag.removeprefix("v")
    if json.loads(Path("apps/server/package.json").read_text())["version"] != current:
        raise ValueError("Server package version does not match the upstream tag.")
    metadata["version"] = current
    metadata["revision"] = revision
    fixed = []
    pending = []
    for fix in metadata["backports"]:
        # An upstream merge may absorb a backport. Keep those still carried locally.
        integrated = git("merge-base", "--is-ancestor", fix["revision"], revision, check=False)
        if integrated.returncode == 0:
            fixed.append(fix)
        else:
            pending.append(fix)
    metadata["backports"] = pending
    if fixed:
        metadata.setdefault("included_fixes", []).extend(fixed)
    METADATA.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")


def summary(message):
    print(message, flush=True)
    if path := os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a") as file:
            file.write(message + "\n")


def sync(dry_run=False):
    metadata = json.loads(METADATA.read_text())
    current = metadata["version"]
    official = released(UPSTREAM)
    tag = latest([item["tag_name"] for item in official], OFFICIAL)
    if tag is None:
        raise ValueError("No stable upstream server release found.")
    if version(OFFICIAL, tag) <= version(OFFICIAL, f"v{current}"):
        summary(f"A branch main já usa a versão oficial v{current}. Nenhum PR necessário.")
        return

    branch = f"sync/agentes-{tag}"
    path = f"repos/{FORK}/pulls?state=open&base={MAIN}&head=blezzbr%3A{branch}"
    if not dry_run and (existing := gh(path)):
        summary(f"PR já aberto: {existing[0]['html_url']}")
        return

    git("fetch", "--no-tags", f"https://github.com/{UPSTREAM}.git",
        f"refs/tags/{tag}:refs/tags/{tag}")
    revision = git("rev-parse", f"{tag}^{{commit}}", capture=True)
    base = git("rev-parse", "HEAD", capture=True)
    merge = git("merge", "--no-commit", "--no-ff", revision, check=False)
    unresolved = git("diff", "--name-only", "--diff-filter=U", capture=True)
    if merge.returncode != 0 and not unresolved:
        raise RuntimeError("git merge failed without a content conflict.")

    # The fork owns its CI. Keep upstream workflow changes out of automated pushes.
    git("restore", f"--source={base}", "--staged", "--worktree", "--", WORKFLOWS)
    conflicts = git("diff", "--name-only", "--diff-filter=U", capture=True).splitlines()
    if conflicts:
        git("merge", "--abort")
        git("switch", "--detach", revision)
        git("restore", f"--source={base}", "--staged", "--worktree", "--", WORKFLOWS)
        if git("diff", "--cached", "--quiet", check=False).returncode:
            git("commit", "-m", "Retain Blezz workflows for upstream review")
    else:
        record_base(tag, revision)
        git("add", str(METADATA))
        git("commit", "-m", f"Sync Agentes.chat {tag}")

    notes = [
        f"Atualiza a base oficial de **v{current}** para **{tag}**.",
        "",
        "### Releases oficiais adotadas",
    ]
    notes.extend(
        f"- [{item['tag_name']}]({item['html_url']})"
        for item in upstream_range(official, current, tag.removeprefix("v"))
    )
    if conflicts:
        notes.extend(["", "### Conflitos", *[f"- `{name}`" for name in conflicts], "",
                      "Resolva os conflitos e atualize `ops/blezz/upstream.json` conforme o runbook antes de marcar como pronto."])
    notes.extend(["", "Revise o diff e use **Create a merge commit** para preservar o histórico upstream.",
                  "Os workflows em `.github/workflows` seguem os da Blezz. A geração da imagem e o deploy são etapas separadas."])

    if dry_run:
        summary("\n".join(notes))
        return

    remote = git("ls-remote", "--heads", "origin", f"refs/heads/{branch}", capture=True)
    if not remote:
        git("push", "origin", f"HEAD:refs/heads/{branch}")
    else:
        git("fetch", "--no-tags", "origin", f"refs/heads/{branch}")
        git("merge-base", "--is-ancestor", revision, "FETCH_HEAD")

    with tempfile.TemporaryDirectory() as directory:
        body = Path(directory) / "pull-request.md"
        body.write_text("\n".join(notes) + "\n")
        pr = subprocess.run(
            ["gh", "pr", "create", "--repo", FORK, "--base", MAIN, "--head", branch,
             "--title", f"Atualizar base Agentes.chat para {tag}", "--body-file", str(body)]
            + (["--draft"] if conflicts else []),
            text=True, capture_output=True,
        )
    if pr.returncode == 0:
        summary(f"PR de atualização: {pr.stdout.strip()}")
        return

    print(pr.stderr, flush=True)
    if "not permitted to create" not in pr.stderr and "Resource not accessible" not in pr.stderr:
        pr.check_returncode()
    mode = " em rascunho" if conflicts else ""
    summary(f"A branch foi publicada. [Abra o PR{mode} pelo GitHub]"
            f"(https://github.com/{FORK}/compare/{MAIN}...{branch}?expand=1).\n\n"
            + "\n".join(notes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--dry-run", action="store_true")
    options.add_argument("--record", metavar="OFFICIAL_TAG")
    args = parser.parse_args()
    if args.record:
        if not OFFICIAL.fullmatch(args.record):
            parser.error("--record expects an official stable server tag")
        record_base(args.record, git("rev-parse", f"{args.record}^{{commit}}", capture=True))
    else:
        sync(args.dry_run)
