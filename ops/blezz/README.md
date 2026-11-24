# Blezz builds

The `blezz` branch starts at an official server release. Keep each product patch in
its own commit. For the next upstream release, fetch its tag, start a candidate
from that tag, and replay the deployment files and any patches still needed.
Retire a local patch after its fix ships upstream. Keep the remote `main` branch
available for upstream synchronization.

## Validate and publish

Open a pull request against `blezz` to run the Blezz Compose and runner checks.
To publish the reviewed commit, push the specific tag
`blezz-v<upstream-version>.<revision>`, for example `blezz-v0.1.13.1`. The
workflow builds and tests Linux amd64, publishes the tested image to
`ghcr.io/blezzbr/agentes-chat`, and attaches a deployment bundle to a GitHub
Release. The bundle contains the matching Compose, image digests, runner and
checksums. Never move a published tag.

## Staging

On the Linux amd64 host, unpack the approved release bundle in its own directory,
check `SHA256SUMS` and run `sudo bash stage.sh`. It brings up the selected digest
on loopback port 3300 in the separate `blezz-agentes-staging` Compose project.
To open it remotely, forward local port 3300 to host port 3300 via SSH. The
database and files volumes are independent. Each fresh installation uses its
own runtime secrets and an empty PostgreSQL database.

CI rehearses migrations and a PostgreSQL dump and restore with synthetic data.
For an end-to-end subscription or runner test, use a staging-only runner
identity and a staging account. Production service state, provider sign-ins,
tunnels and storage destinations must remain private. If the GHCR package is restricted, use the release's image archive:
`sudo bash stage.sh /path/to/blezz-image-linux-amd64.tar.gz`. Staging verifies
the archive's checksum and the loaded image ID against the release bundle.

## Production promotion

Use the exact tested release bundle and pinned image digests. Use the
operations repository to verify the live deployment, back up PostgreSQL and
files, rehearse restore and migration, and retain the accepted Compose and
runner pairing. Plan rollback against the matching backup before applying a
database migration. Production credentials and the promotion operation stay
on the deployment host.
