# Blezz Workspace releases

Blezz Workspace is a server build of the agentes.chat fork, built with the
upstream Dockerfile. Based on agentes.chat by AGENTESCHAT, LLC. The corresponding
source, including the build scripts, is in this repository under the AGPL-3.0-only
license and the terms in NOTICE.

## Track upstream

The `blezz` branch is the release branch. Fetch the exact upstream stable tag
and merge it when adopting that version. Update `upstream.json` with the server
version, upstream commit and backports that remain in the build. If upstream
ships a backport, review the merge and remove its entry. Intermediate versions
can be skipped for deployment. Read their official release notes and check the
migration path from the version actually installed.

## Validate and publish

Pull requests to `blezz` run checks for affected areas and changed test files.
Ordinary documentation edits skip the workflow. A manual run on `blezz`
builds and tests both architectures without publishing. Both workflows use
standard GitHub-hosted runners.

Set the stable upstream base in `upstream.json`, then run:

```sh
python3 ops/blezz/release.py next-tag
```

The result is `blezz-v<upstream-version>-r<N>`. A new base starts at `r1`. On
the same base the script increments the highest published revision. For example,
`blezz-v0.1.18-r2` becomes `blezz-v0.1.18-r3`, or `blezz-v0.1.19-r1` after a
base update. The earlier `blezz-v1.0.0` tag remains valid and is the starting
point for the release note comparison. For an unpublished release, keep the same
tag and retry its workflow.

Before pushing a release tag, commit
`ops/blezz/changes/<tag>.json` with a `changes` array describing the Blezz
changes since the preceding published release. Review the fork diff and include
product or operations changes. Use `{"changes":[]}` when only the upstream base
changed. Preview the notes before release:

```sh
python3 ops/blezz/release.py notes "$tag" --output /tmp/blezz-release-notes.md
```

CI validates the calculated revision and generates two distinct sections.
The first lists Blezz changes. The second copies the complete official server
release notes in version order from after the previous base through the new
base, even when intermediate versions were skipped for deployment. A release
on the same base records that fact and includes its notes for reference. If the GitHub body limit is reached, the
complete Markdown remains available in the attached `release-notes.md`.

Each release publishes the tested Linux amd64 and arm64 images under the
versioned Docker Hub tag, pins the index by digest, and carries the source
revision, upstream base, matching Compose and runner in the delivery bundle.

Publishing needs a Docker Hub token with read/write access stored in the GitHub
repository secret `DOCKERHUB_TOKEN`. Pulls from the public repository require no
deployment credential. Keep tags immutable and use the release bundle's digest
for deployment.

## Staging and promotion

Download `blezz-delivery.tar.gz` from an approved release. Unpack it in a
dedicated directory, check `SHA256SUMS` and run `sudo bash stage.sh` on the Linux
amd64 staging host. It uses port 3300 on loopback and a distinct Compose project,
database and files volume. Access it using SSH forwarding. Use synthetic data
and staging-only accounts. System-mode runner verification needs an isolated
host or VM because its network rules are host-wide.

Production promotion uses the exact tested artifacts. Verify the current
deployment, back up PostgreSQL and files, rehearse restore and migration, and
pair the runner with the release. Recovery after a database migration needs
the matching verified backup and recovery plan.
