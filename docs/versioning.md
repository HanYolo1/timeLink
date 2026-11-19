# Versioning

timeLink follows [Semantic Versioning 2.0.0](https://semver.org/). Its first version is **v0.1.0**, and the timeLink
Launcher's is too: one tag names both products' releases, which ship different files. Version numbers from before the
fork are not timeLink versions. How a version is built, signed and
published, and how the timeLink Launcher installs it, is in [releases.md](releases.md).

## Versions and channels

| Channel | Versions | Made by |
|---|---|---|
| `stable` | `vX.Y.Z` | a tag `vX.Y.Z` pushed on a commit of `main` |
| `rc` | `vX.Y.Z-rc.N`, and the stables: it offers the newest of both | a tag `vX.Y.Z-rc.N` on `main` (a stable moves it too) |
| `nightly` | `nightly-<commits since the fork>-<8 hex of the commit>`, e.g. `nightly-412-1a2b3c4d` | a manual run of the Release workflow (Actions > Release > Run workflow) |

The `v` belongs to the tag, not to the version. Build metadata is not used. A nightly's count starts at the fork, the commit
that renamed the project (`e2a4d45`), so it says how far timeLink is past it. A build from a checkout is named by
`git describe --tags --long` (`v0.1.0-3-g1a2b3c4`) or `dev`: it is on no channel, and the launcher never offers it as an
update.

One version covers the game (`timeLink.exe` / `timeLink`), the Vulkan back end, the lift pipeline and its scripts, and the
builders: they are built from the same commit and released together. The **timeLink Launcher is released from the same
repository and the same tag**, with the same numbers (from v0.1.0) on the same three channels: a release ships both
products' files, and each product's releases are told apart by the files they carry.

The order (the launcher's `Core/Versions.cs`): stables and release candidates in semver order (`v0.2.0-rc.1` <
`v0.2.0-rc.2` < `v0.2.0`), nightlies by their count. A nightly and a stable are not ordered: the launcher never offers one
as an update of the other, and a build stays on its channel unless the player picks another.

The "public" surface the rules protect is the command line of `make_game.py` and the builders, the `RX_` and `HOS_`
switches, the files a build writes into a game folder (`timeLink_options.ini`, `timeLink_env.txt`, `language.txt`,
`timeLink_version.txt`), saves, the release files' names, `SHA256SUMS` and `tools.lock`, `recomplauncher.json`, and the format of
`timeLink_log.txt`. The C sources and internal headers are not an API and may change in any release.

## Choosing the next version

There are no release pull requests: a maintainer pushes a tag, and CI does the rest
([RELEASING.md](../RELEASING.md)). Pull requests are squash-merged and their titles are
[Conventional Commits](https://www.conventionalcommits.org/) (`.github/workflows/ci.yml`,
[CONTRIBUTING.md](../CONTRIBUTING.md#pull-request-titles)), so the commits on `main` say what changed, and CI
(`scripts/release.py check-tag`) refuses a tag lower than they call for:

| Since the last stable | The next version is at least |
|---|---|
| any `!` or `BREAKING CHANGE:` | the next major: `v1.0.0` after `v0.2.1` |
| a `feat` | the next minor: `v0.3.0` |
| only `fix`, `perf` and the rest | the next patch: `v0.2.2` |

It also refuses a tag that is not on `main` or not above every release there is. Every stable is first a release
candidate: `vX.Y.Z-rc.1`, then `-rc.2` and so on while fixes come in, then `vX.Y.Z` on the candidate that was good (the
same commit). `python -I scripts/release.py next` prints the number and the notes before tagging.

## Where the version appears

| Place | Where it comes from |
|---|---|
| the tag | the maintainer; the source of truth |
| `timeLink_log.txt` and the Insert menu | `nx2/version.py`: `TIMELINK_VERSION`, then `VERSION`/`version.txt`, then `git describe --tags --match "v[0-9]*"` |
| `timeLink_version.txt` in a build | the `VERSION` file written when the tools are packaged (`nx2/make_game.py`) |
| the Windows builder's `VERSION` | the release workflow's name for the version (`scripts/builder_package.py zip`) |
| the release | its tag; the release page and its files are named after it (docs/releases.md) |

`nx2/version.py` also appends a fingerprint of the source files, `(source 1a2b3c4d)`. It is not a version: it tells two
builds of the same release apart, and it is the only identifier a build from a modified checkout has.

## The changelog

timeLink keeps no changelog file. Its changes are on each release's page, written by git-cliff (`cliff.toml`,
`scripts/release.py notes`) when it is released; nothing is committed back to `main`.

## Rules

- Do not move or reuse a tag. A version's files never change: a fix is the next version.
- Do not put game files, keys, builds or anything made from a dump in a release (CONTRIBUTING.md).
