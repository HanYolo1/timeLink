# Releases and updates

How timeLink and the timeLink Launcher are released on GitHub, and how the launcher finds, checks and installs
them. Both are released from one repository, [HanYolo1/timeLink](https://github.com/HanYolo1/timeLink): the launcher
is `launcher/` there (vendored, [VENDORED.md](../VENDORED.md)). How to make a release, step by step, is in **RELEASING.md**
(one file, covering both products).

timeLink's numbers start at **v0.1.0**, and the launcher's do too: one tag names both products' releases. Nothing here reads or writes
GitHub, and nothing is compatible with Hookshot's 2.x updates (NotRexed/Hookshot's history is Hookshot's).

## In short

| | |
|---|---|
| **A release** | A Forgejo release of the repository: a tag, a page with the notes, and the product's files with `SHA256SUMS` and `SHA256SUMS.sig`. Nothing else: no package registry, no pointer files |
| **Two products** | timeLink releases its **builders** (Windows and Linux). The launcher releases **itself**. Both come from this one repository, in one `v*` tag namespace, each with its own versions and its own files: a release belongs to a product by the files it ships (`Core/ReleaseManifest.cs`'s `Ships`) |
| **Three channels each** | `stable` (tag `vX.Y.Z`), `rc` (tag `vX.Y.Z-rc.N`, and every stable), `nightly` (every push to `main`). Read from the release list |
| **One key** | CI signs `SHA256SUMS` with the release key (ECDSA P-256). The launcher has the public key built in |
| **tools.lock** | The builders' build tools, Windows' and Linux's, are not in timeLink's releases: `tools.lock` names each one (URLs, SHA-256, size) |
| **Tags, not release PRs** | A maintainer releases by pushing a tag. CI checks the number against the commits, builds, signs and publishes. Notes by git-cliff |
| **Updates** | The launcher installs and updates the builder of each build, and updates itself, from these releases. The builders and the game look for no update themselves |

## What a release is

Each version is one Forgejo release, made by `.forgejo/workflows/release.yml`:

| timeLink (HanYolo1/timeLink) | The launcher (HanYolo1/TimeLinkLauncher) |
|---|---|
| `timeLinkBuilder-<v>-windows-x64.zip`: the Windows builder (its setup as `timeLinkBuilder.exe`, the builder and timeLink's sources in `timeLinkBuilder\`, `tools.lock`, `VERSION`, and `recomplauncher.json` at the top) | `TimeLinkLauncher-<v>-windows-x64-setup.exe`: one self-contained program that installs itself (below); `TimeLinkLauncher-<v>-windows-x64-portable.zip`: the same program as `timeLinkLauncher.exe` with its `portable` file |
| `timeLink-<v>-x86_64.AppImage`: the Linux builder (the builder, its Python, timeLink's sources, the Vulkan back end, its `tools.lock` and `recomplauncher.json`); its build tools are not inside | `TimeLinkLauncher-<v>-x86_64.AppImage` |
| `tools.lock`: the tools the builders download | |
| `SHA256SUMS`, `SHA256SUMS.sig` | `SHA256SUMS`, `SHA256SUMS.sig` |

`SHA256SUMS` is `sha256sum`'s format, one `<64 hex>  <name>` line per file. `SHA256SUMS.sig` is the base64 of the DER ECDSA
P-256 signature of `SHA256SUMS`'s exact bytes, by the release key. A release's files never change: a fix is the next version.

Release files are release attachments: `[attachment] MAX_SIZE` (2048 MB on MagicBeanDev's Forgejo, whose limits this fork inherits when it uploads to GitHub) caps each file, and
`[repository.release] ALLOWED_TYPES` must stay empty (every type) for `.AppImage`, `.exe`, `.lock` and `SHA256SUMS`. The
site is behind Cloudflare, which refuses uploads over 100 MB: CI uploads to the organization variable `RELEASE_UPLOAD_API` (`FORGEJO_UPLOAD_API` to `release.py`), the instance's address
without Cloudflare in front, when it is set (RELEASING.md, One-time setup). Downloads are not limited.

CI makes each release with the job's own token (`forgejo.token`, given to `release.py` as `RELEASE_TOKEN`), with no
secret and no bot account: on a push or a tag in the
repository, Forgejo 17 gives it write access to that repository's every unit and to no other repository
(`routers/api/v1/permissions/repo_access.go`; read-only for a pull request from a fork). That covers every call
`release.py` makes: create a release, upload its files, edit and publish the draft, delete a nightly's release and its tag
(a tag that isn't protected). Each repository releases into itself only, so no other token or fallback is needed. The token ends with
the job. Forgejo 17 ignores a workflow's `permissions:` key, so the workflows have none.

## The channels

The channels are read from the repository's release list (`GET /api/v1/repos/<repo>/releases`), by the same rules in the
launcher (`Core/ReleaseManifest.cs`, `Newest`) and in `scripts/release.py` (`newest`, `channels`):

| Channel | Offers | For |
|---|---|---|
| `stable` | the newest `vX.Y.Z` that is published and not a pre-release | playing |
| `rc` | the newest `vX.Y.Z-rc.N` or `vX.Y.Z` that is published | trying the next version before it is stable |
| `nightly` | the newest `nightly-<count>-<8 hex>` that is published, by its count | every change, untested |

- A **draft** is on no channel. CI creates each release as a draft, uploads every file, and publishes it last, so a run
  that fails half way shows players nothing.
- **Pulling** a bad version is deleting its release, or setting it back to a draft: its channel then offers the one before
  by itself.
- The **nightlies** past the newest 5 are deleted, with their tags, by the run that makes a new one. Nothing else is pruned.
- Anything else in the list is on no channel: a 2.x tag, a git describe name. (The builders' tools are not releases:
  they are packages, below.)
- A nightly's count is the number of commits: for timeLink since the fork (e2a4d45, "Rename the project to timeLink"), for
  the launcher since its first commit.

**Each build has its channel, and the launcher has its own.** In the launcher, *Settings > Channel for new builds* picks
the channel a new build follows (each build keeps its own). *Settings > Launcher updates* picks the channel the launcher
updates **itself** from: TimeLinkLauncher's stable, rc or nightly, independent of any build's. It defaults to the channel
of the launcher the player installed (a stable launcher follows stable).

**No downgrades, no replays.** There is no pointer file to replay: the list is what it is. The launcher never updates a
build or itself to a lower version than the one it has on that channel, and never goes down by itself; going down is the
player's choice (building another channel's version, or `--rollback`). A server that serves an old list can only hold
updates back, not undo them.

## Signing

One release key signs every release of both products, in CI, from the organization secret `RELEASE_SIGNING_KEY`.

1. CI writes `SHA256SUMS` over the release's files, signs it (`scripts/release.py sign`), then checks the signature with
   the key the launcher is built with (`verify`, from `Core/ReleaseTrust.cs` or timeLink's `scripts/release_keys.json`):
   a key the launcher does not trust stops the release in CI, not in every player's launcher.
2. The launcher checks the signature of `SHA256SUMS` with its built-in key (`SignedSums`), then each file it downloads
   against the SHA-256 `SHA256SUMS` gives, and, for the Windows builder, each tool against the SHA-256 `tools.lock` gives.
   A release without a valid signature is refused, and the window says why.

**Why ECDSA P-256:** the launcher checks signatures with .NET's own crypto (no package; .NET 10 has no Ed25519), and CI and
maintainers sign with the `openssl` command line, so `scripts/release.py` needs no Python package. Hand-written signature
code is how updaters get broken.

**Why one key in CI:** it is simple and every release, nightlies included, is signed the same way. The risk is a leaked
secret or runner: the key would then sign anything. A second, **offline** key for stables only (the launcher requiring it
for `vX.Y.Z`) can be added later without changing the files: a second signature file beside `SHA256SUMS.sig`.

Rotating the key: RELEASING.md, "Rotate the key".

## tools.lock (timeLink)

The builders need build tools that are not timeLink's own code. Windows (`windows-x64` lines): llvm-mingw, Python with the
prompt packages, emsdk, the CPM cache (FFmpeg, Vulkan and SPIR-V headers, VMA, dav1d), wgpu-native, the prebuilt files of
`third_party` (a64emit.dll, lld-link.exe, SDL2/SDL3, zbic.dll), and the play profile when there is one (optional: without
it the game is built all the same, a little slower in play). Linux (`linux-x64` lines): LLVM's clang
and lld (`emsdk`), the glibc 2.35 `sysroot`, `ffmpeg` with dav1d, `sdl2` and the Vulkan, SPIR-V and VMA headers (`cpm`).
They are not in the release: `tools.lock` names them.

```
tool <name> <version> <system> <sha256> <size> <dest> <prefix> <url> [<url> ...]
tool llvm-mingw 20261104 windows-x64 5521…40f 191037046 timeLinkBuilder/tools/llvm-mingw llvm-mingw-20261104-ucrt-x86_64 https://github.com/mstorsjo/llvm-mingw/releases/download/20261104/llvm-mingw-20261104-ucrt-x86_64.zip
```

- **Installing.** The Windows builder's setup (`builder/setup/setup.c`), the Linux AppImage (`builder/linux/linux_tools.py`)
  and the launcher (`Core/ToolsLock.cs`, `Toolchains`) download each tool of their system from the first URL that answers
  with the right bytes. They check its size and SHA-256 and unpack the archive's
  `<prefix>` folder as `<dest>` in the install. A `<dest>` the builder already has (the Windows zip's
  `timeLinkBuilder/tools/third_party`, the sources the `third-party` tool's prebuilt files go among) gets the tool's files
  merged in, file by file; a file both have is refused, never replaced. A tool another installed version has, with the
  same SHA-256 and unpacked the same way, is taken from it and not downloaded again (the Windows setup excepts a merged
  tool: it comes from its archive each time). `scripts/tools.py install` does the same, for CI and developers.
- **Where the archives are: the `tools` release.** Every tool is downloaded first from timeLink's own copy, an asset of the
  **`tools` release** on `HanYolo1/timeLink-tools`, named `<sha256>-<name>.zip`:
  `https://github.com/HanYolo1/timeLink-tools/releases/download/tools/<sha256>-<name>.zip`. That repository is **public**
  and holds nothing but these archives: a private repository's release assets are not served at `releases/download/` at
  all, not even with a token, so the builder's setup and the AppImage could not fetch them. The name carries the digest and
  `tools.lock` checks it, so a replaced asset is caught; GitHub lets an asset be deleted and uploaded again, so never reuse
  a version string. Nothing prunes the release, so an older version's tools stay downloadable. Where an archive came from
  (upstream for llvm-mingw, NotRexed/Hookshot's `builder-parts` release for those taken from Hookshot) is its fallback URL,
  so no install depends on a repository we do not control alone. An archive timeLink makes itself (the CPM cache with dav1d,
  the prebuilt `third_party` files, the Linux tools) has no upstream: its release asset is the only copy.

  The launcher has no Cloudflare edge in front of it any more (`CdnFetcher` went with MagicBeanDev's Forgejo), so a release
  file and a release list come from GitHub directly. `Core/Toolchains.cs` reads `tools.lock` like the builder does, so the
  launcher installs from the same public release.
- **Bumping a tool** is a pull request that edits `tools.lock`, with the archive uploaded by `scripts/tools.py mirror`,
  `add` or `assemble`: a new asset in the `tools` release, then the line (RELEASING.md, "Bump a tool"). The release workflow
  refuses a `tools.lock` whose assets are not there with their size, or that lacks a tool the
  builder needs (`tools.py check --require`), in its first job, before anything is built.
- **Today's lock.** Windows: Python, emsdk and wgpu-native are taken as they are from Hookshot v2.1.0's Windows builder
  (NotRexed/Hookshot's `builder-parts` release), with their SHA-256; llvm-mingw is upstream's; the CPM cache is Hookshot
  v2.1.0's with dav1d added (`scripts/windows/dav1d.sh`), and `third-party` the prebuilt files of Hookshot v2.1.0's
  `third_party` part (`assemble third-party`). Linux: `scripts/linux/deps.sh tools`'s. The lock has no play profile:
    play profiles are committed in `assets/profiles/`.
- **Linux.** The AppImage carries only the builder: its Python (the tools' download and `make_game.py` run on it,
  and its packages follow `requirements.txt`, which changes with the version), timeLink's sources and the prebuilt Vulkan
  back end. Each `linux-x64` tool's `dest` is where the AppImage had it (`usr/lib/timeLink/emsdk`, `usr/share/timeLink/cpm`,
  ...). The launcher unpacks them beside the unpacked AppImage, as on Windows. An AppImage started by itself
  (`builder/linux/AppRun`) finds them there, or in the launcher's copy of the same version, or in
  `$XDG_DATA_HOME/timeLink/builder/toolchains/<v>/`; what is missing its first `--cli` downloads there, its progress on
  stderr, linking a tool another version there has. Once there, no connection is needed.
  `scripts/linux/deps.sh tools` makes the Linux archives from its pinned downloads (`scripts/tools.py pack`: modes and
  relative links kept).

## How the launcher reads it

`Core/Releases.cs`, `ReleaseManifest.cs`, `ReleaseTrust.cs`, `ToolsLock.cs`, `ToolsSource.cs`, `Toolchains.cs`,
`SelfUpdate.cs`:

1. **At start, and on Retry.** It reads timeLink's release list and its own. For each of timeLink's channels and for its
   own launcher channel, it takes the newest version (rules above). It opens that release's `SHA256SUMS` and checks the
   signature. A channel whose newest release is refused offers nothing, and the home says why.
2. **Builds.** Each build is offered its channel's newest timeLink version when that is newer.
   - Windows: building a version downloads its `timeLinkBuilder-<v>-windows-x64.zip` and its `tools.lock`, each checked
     against `SHA256SUMS`, then installs the zip and each tool (above) into `<home>/toolchains/<v>.part`. The folder is
     renamed when complete.
   - Linux: it downloads `timeLink-<v>-x86_64.AppImage`, checks it, and unpacks it with its own `--appimage-extract`, then
     installs the `linux-x64` tools of the `tools.lock` inside it (covered by the AppImage's checksum) into the same folder,
     each checked by its SHA-256, as on Windows. An AppImage with no `tools.lock` inside (one that carried its tools) needs
     none.
3. **Itself.** The launcher's own channel offers a newer launcher, or, after the player picked another channel, that
   channel's newest. *Update the launcher* downloads it beside the current file as `<name>.new` and checks it against
   `SHA256SUMS`. It starts it with `--self-check` (it must print `TimeLinkLauncher <version>` and exit 0 within a minute),
   then swaps the files:
   - Linux: one `rename()` over the AppImage.
   - Windows: the running exe is renamed aside, then the new one moved in; on failure the old one is put back.

   It then starts the new launcher and closes. `--rollback` puts the previous launcher back (`<name>.old`). A build from a
   checkout is `dev` and never updates itself.

### Installing the launcher

There is no installer program: the launcher installs itself (the launcher's README, *Installing*; `Core/Installer.cs`,
`LauncherLayout.cs`).

- **Windows, the setup file.** Its first start asks: **Install** copies it to
  `%LOCALAPPDATA%\Programs\TimeLinkLauncher\timeLinkLauncher.exe` for the user (no administrator rights), with a Start
  menu shortcut and an *Apps & features* entry, its data in `%LOCALAPPDATA%\TimeLinkLauncher`; **Run portable** puts a
  file named `portable` beside the program and keeps everything in `timeLinkLauncher-data` beside it, with no registry
  or shortcut. `--install` installs without asking; `--uninstall` (what *Apps & features* runs) removes the program, its
  shortcuts and its entry, and asks before deleting its data (never a build's game folder or the saves).
- **Windows, the portable zip.** `timeLinkLauncher.exe` with the `portable` marker already beside it, so it never asks.
- **Linux.** The AppImage needs no installing. *Settings > Applications menu > Add to applications menu* writes a
  `.desktop` entry that starts the AppImage where it is. Portable is the AppImage convention: a folder named
  `<AppImage>.home` beside it holds its data.
- **Updates keep the kind.** An installed launcher updates from the release's setup file, a portable one from the
  portable zip, in place beside its `portable` file; the file keeps its name.

`TIMELINK_LAUNCHER_TRUST=<public key .pem>` trusts one more key, to try a release signed with a test key.

## CI

Both products are now released from this one repository, so its workflows in `.forgejo/workflows/` cover both, on Forgejo
Actions. The launcher's are scoped to `launcher/` by path:

| Workflow | Covers |
|---|---|
| `ci.yml` | timeLink: every pull request and push to main, the PR title and every game-free check (`tests/run_all.py`, on Linux) |
| `launcher.yml` | the launcher, on pull requests and pushes that touch `launcher/`: compile, `tests/test_launcher_core.py`, `tests/test_release.py` |
| `release.yml` | timeLink's release: tags `v*`, the version, the two builders (`build-linux.yml`, `build-windows.yml`) and the launcher (`build-launcher.yml`), sign and publish |
| `build-launcher.yml` | the launcher's release programs (`scripts/package.sh`), called by `release.yml` |
| `third-party.yml` | the `third_party` rule (`scripts/check_third_party.py`) |

One release, one tag, both products: `release.yml` builds the builders and the launcher and publishes every file together.
A product's releases are told apart by the files they carry, not by the tag's number (`launcher/Core/ReleaseManifest.cs`,
`Ships`). Only `release.yml` takes a push to main, so one commit produces one nightly.

timeLink also keeps `build-linux.yml` and `build-windows.yml` (also run on pull requests that change code) and
`vulkan-dlss.yml` (the upscalers' build checks). A tag on a commit CI has released already (its nightly, or a stable's
release candidate) is still built again, since every file carries its version (a release never ships a file that names
another), but `release.py released-as` finds that release, checks its signed `SHA256SUMS` (one that does not check stops
the run), and the build checks that ship no file and passed in its run are not run again. Every job runs on Linux: timeLink's Windows files are cross-built there,
and what only Windows can check is a tester's (RELEASING.md, *Needs a Windows tester*). The runners are in timeLink's [docs/forgejo-runners.md](https://github.com/HanYolo1/timeLink/blob/main/docs/forgejo-runners.md).

## The version a tag must have

Pull requests are squash-merged, and their titles are Conventional Commits, so the commits on `main` say what changed. For
a tag, `scripts/release.py check-tag` (in `release.yml`, before anything is built) refuses:

- a name that is not `vX.Y.Z` or `vX.Y.Z-rc.N` of the product's numbers;
- a tag that is not on `main`;
- a tag that is not above every release there is (a stable `vX.Y.Z` is above its own `vX.Y.Z-rc.N`, so a stable tagged on
  the same commit as a release candidate is the normal way);
- a number lower than the commits since the last stable call for:

| Since the last stable | At least |
|---|---|
| a `!` after the type (`feat(vk)!:`) or a `BREAKING CHANGE:` footer | the next major (`v4.0.0` after `v3.2.1`) |
| a `feat` | the next minor (`v3.3.0`) |
| `fix`, `perf`, or anything else | the next patch (`v3.2.2`) |

The first release of each product only needs its first number (both `v0.1.0`).
`python -I scripts/release.py next` prints the number and the notes before tagging.

## Release notes

git-cliff writes them at release time from the commit titles since the previous tag, with the repository's `cliff.toml`.
For a stable, that is since the previous stable, so its notes cover its release candidates. The headings are Features,
Fixes, Performance, Reverted, Documentation, Code, Build and Tests; `ci` and `chore` are left out. The notes go on the
release page only: nothing is committed back to `main`, and there is no changelog file to keep up (Hookshot's is in
NotRexed/Hookshot).

`release.py publish` puts a header above the notes (`release_page`), so a player who lands on a release page downloads the
right thing:

- **The launcher's releases** start with big download links to that release's own files: *Download for Windows* (the
  installer), *Download for Linux* (the AppImage), and a small link to the portable zip, each to the file on GitHub's
  release itself (`https://github.com/<owner>/<repo>/releases/download/<tag>/<name>`).
- **timeLink's releases** start with "To play, get the timeLink Launcher", linking the fork's **release list** (both
  products sit on it, newest first), then "Don't download the files below": they are the builders the launcher installs.

## Download links

There is no website in front of the releases. The launcher used to be published by a project whose site
(`timeLink.magicbean.dev`, a Cloudflare worker) gave a permanent link to the newest build of each channel; this fork does
not own that domain and `release.py` no longer writes those links, because a release made with them would send players
somewhere this fork cannot answer for. The one address is the releases list:

| Link | Goes to |
|---|---|
| `https://github.com/HanYolo1/timeLink/releases` | every release of both products, newest first |

A player picks by the file name: the launcher's are `timeLinkLauncher-*`, the builder's `timeLinkBuilder-*` and
`timeLink-*`; `-windows-x64-setup.exe` is the Windows installer, `-windows-x64-portable.zip` the portable, `.AppImage`
the Linux one. `release.py` tells the two products' releases apart the same way (`ships`, and `ReleaseManifest.Ships` at
runtime), not by the tag, since both share the `v*` namespace. The launcher's own update check reads this list through
GitHub's API (`https://api.github.com/repos/HanYolo1/timeLink/releases`) and needs no website either.

## RecompLauncher (timeLink)

[RecompLauncher](https://recomplauncher.com) is the other way to install timeLink. It installs a recomp from a release
file, then runs its `recomplauncher.json` (the game it needs, how to build and start it). timeLink keeps that file
(`recomplauncher.json`, `tests/test_recomplauncher_json.py`) inside both builders, which are the same files the launcher
installs:

| File | What RecompLauncher does with it |
|---|---|
| `timeLinkBuilder-<v>-windows-x64.zip` | *prepare* runs `timeLinkBuilder.exe --cli --prepare --game <your copy>`: the setup installs the builder and the tools of the `tools.lock` beside it (no release lookup), then builds; *start* runs it with `--play` |
| `timeLink-<v>-x86_64.AppImage` | the same `--cli --prepare` and `--play` |

**What RecompLauncher cannot do yet.** It finds releases only on GitHub. Its guide says it "installs and updates your recomp
straight from your GitHub releases", its `repo` is a GitHub `owner/name`, and its schema has no field for another forge or
a URL. So `recomplauncher.json` names no `repo`, and RecompLauncher cannot find timeLink by itself. It needs either a
GitHub repository that mirrors these releases (there is none), or Forgejo support in RecompLauncher (a request to its
makers). Until then a player can add a downloaded zip or AppImage to RecompLauncher by hand, as a local build.

So there are two ways to install: **the timeLink Launcher** (recommended: it follows channels, checks signatures and
updates everything), or **RecompLauncher**, with the same builder files.

## Why this design

- **Forgejo releases, not a package store and pointer files.** A release is what Forgejo already shows people: a tag, notes
  and files. The channels follow from the list, so there is nothing else to publish, keep in step or replay. Drafts make a
  release appear all at once.
- **A signature on the checksums.** HTTPS says a file came from GitHub. A stolen token, a compromised runner or a
  mistake on the server would otherwise reach every player's PC, and the launcher runs what it installs. One signature
  over `SHA256SUMS` covers every file, however large.
- **tools.lock, not the tools in every release.** The tools change rarely and weigh gigabytes. A lock file in the repository
  says exactly which bytes each version needs; reviewers see a tool change as a one-line diff; installs share a tool
  across versions; and a release holds only timeLink's own files.
- **Tags and computed numbers, not release PRs.** A maintainer tags; CI checks the number against what was merged and
  writes the notes. Nothing is committed back to `main`, so there is no release branch or bot commit to review.
- **The builders do not update themselves.** One updater, the launcher's, with one set of rules, instead of three (the
  game, the Windows builder, the Linux builder). The builders have no window any more; their `--cli --update <folder>`
  rebuilds a game with their own tools.
