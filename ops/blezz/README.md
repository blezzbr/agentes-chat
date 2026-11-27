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
Changes limited to documentation do not trigger the workflow. The release
workflow runs explicitly when a tag of the form `blezz-vMAJOR.MINOR.PATCH` is
pushed. A manual run on `blezz` builds and tests both architectures without
publishing. Both workflows use standard GitHub-hosted runners.

The Blezz tag is independent of the upstream version. The release notes, the
delivery bundle's `upstream.json` and the image labels carry the source revision
and upstream base. Each release publishes the verified Linux amd64 and arm64
images under one versioned Docker Hub tag and pins the index by digest in the
delivery bundle. The bundle also includes the matching Compose and runner.

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
