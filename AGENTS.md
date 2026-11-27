# Blezz Agentes.chat fork

Respond to Klaus in Brazilian Portuguese. Write technical documentation, commands and identifiers in English.

This is the Blezz fork of `agentes-chat/agentes-chat`. The canonical public source is
`blezzbr/blezz-agentes-chat`, the default working branch is `blezz`, and the local Git remotes
are `origin` (Blezz) and `upstream` (Agentes.chat). Upstream issues and pull requests remain
upstream. Infrastructure records and private operating details live in the separate
`agentes-chat-gerenciamento` workspace. Read its `AGENTS.md` and runbook before deployment.

## Upstream changes

- Base releases on an explicit upstream stable server tag. Read the upstream release notes for
  intermediate versions too when advancing several releases at once. Use that tag's Dockerfile
  and Compose and keep the product diff focused on the changes Klaus requested.
- Check whether each upstream PR is already in the chosen tag before backporting it. Keep local
  backports traceable to their upstream PR and commit and retire duplicate patches when adopting
  a stable version that includes them.
- Update [upstream.json](ops/blezz/upstream.json) with the base revision, server version,
  backports and relevant fixes shipped in the base. The first Blezz release uses upstream
  `v0.1.18`, which includes the Antigravity 1.5.x Lodi fix (#1132 via #1535) and plan connection
  for administrators who manage an agent (#1517). Verify both login and execution when working
  on provider changes.

## Build and delivery

- Use `blezz-v<upstream-version>-r<N>` tags. Run `python3 ops/blezz/release.py next-tag`
  to get the next number. A new upstream base starts at `r1`; the same base increments
  its latest published revision. Preserve historical and published tags. The server reports
  the upstream application version.
- Commit `ops/blezz/changes/<tag>.json` after reviewing the fork diff. List Blezz changes
  since the prior release or use an empty changes array if the release only adopts upstream.
  CI validates the tag, puts Blezz changes in their own section and includes the full official
  notes for every published server version adopted since the prior base.
- Keep [CI](.github/workflows/blezz-ci.yml) selective by changed area. Documentation-only edits
  should skip the builds. The explicit tag runs the [release workflow](.github/workflows/blezz-release.yml)
  on standard cloud GitHub Actions runners for Linux amd64 and arm64.
- Publish tested images to `docker.io/klausgibin/blezz-agentes-chat` using the repository
  secret `DOCKERHUB_TOKEN`. Keep the public image associated with its corresponding source,
  attribution and AGPL license. Never print credentials, copy user data into the fork or image,
  or use a mutable `latest` or `edge` tag for a deployment.
- Verify the published manifest, both architectures, build checks and upstream provenance.
  The GitHub release provides the matching Compose, runner, metadata, image digest and checksums.
  Use [the release and staging runbook](ops/blezz/README.md) for the exact flow.

## Deployment

Validate the release in the separate staging Compose project. Preserve the database and files,
check backup restoration, boot migrations, health and the bundled runner. Real provider sign-in
needs a staging account and a system-mode runner on a separate host or VM because isolation
rules are host-wide. Use manual production promotion with the verified migration and recovery
plan from the management workspace.
