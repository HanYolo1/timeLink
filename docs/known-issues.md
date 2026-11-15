# Known issues

What is known to be broken or unfinished in **this fork**, and what to do about it. This is not
[common-issues.md](common-issues.md), which is help for players, nor [worklist.md](worklist.md), which is the scored list of
game bugs. This file is about timeLink as a project: its releases, its launcher, and the parts of the fork that do not work
yet.

Last checked: 2026-11-15, at `b3e24f80` plus the version-0.1.0 and one-release work (uncommitted at the time).

## Blocks a release

These stop `v0.1.0` from being shippable. Nothing else on this page does.

| # | Issue | Why it blocks | Owner |
|---|---|---|---|
| 1 | ~~**`third-party` archive is incomplete: 3 of 11 kits**~~ — **misdiagnosed, and the real bug is fixed.** The archive is *correct*: it carries only the prebuilt files (`a64emit.dll`, `lld-link.exe`, `SDL2.dll`, `SDL3.dll`, `zbic.dll`), and the builder zip carries the 11 kits' sources. The real failure was `place_tool` in `builder/setup/setup.c`: it refused **any** file present on both sides, and `SDL2.dll`/`SDL3.dll` are byte-identical in both, so every install stopped at tool 6 of 6. It now compares SHA-256 and accepts identical bytes (the builder's copy stays); different bytes are still refused. Covered by `tests/test_setup_tool_merge.py` | — | done |
| 2 | ~~**`tools.lock` names GitHub assets that do not exist yet**~~ — **done**: all 11 archives are uploaded to the `tools` release of **`HanYolo1/timeLink-tools`**, a public repository that holds nothing but these archives, and every `tools.lock` line names it first. Verified unauthenticated: `curl` gets 200 and the right byte count, and `scripts/tools.py fetch sdl2` / `fetch third-party` both download and check their SHA-256 with no token. The tools could not live in `HanYolo1/timeLink` itself: that repository is private, and GitHub does not serve `releases/download/` for a private repository at all — not even with a token (the API asset endpoint works, but the builder's setup, the AppImage and the launcher all use the plain URL) | — | done |
| 3 | **No release key secret yet** | The public key is in `launcher/Core/ReleaseTrust.cs` (id `774f1dc88462b913`), but `RELEASE_SIGNING_KEY` must be set in the repository's Actions secrets, and `release.pem` backed up offline. Without the secret the publish job stops at *SHA256SUMS, signed* | the repository owner |

## Verified 2026-11-15: the installer, end to end

Run: extracted `timeLinkBuilder-v3.0.0-rc.3-100-g16ecbc19-windows-x64.zip` and ran its `timeLinkBuilder.exe --cli`.

```
error Could not set up tool 6 of 6 (timeLinkBuilder/tools/third_party:
      no third_party in its archive, or a file the builder has already?).
```

**What works.** The installer starts headless, forwards its command line to the builder (`setup.c:812`), inherits
stdout and stderr so progress reaches the caller, installs the builder, and downloads and verifies tools 1-5 of 6
(`llvm-mingw`, `python`, `emsdk`, `cpm`, `wgpu-native`). It fails on the sixth, `third-party`.

**Why it failed, and it was not the URL.** The `third-party` archive downloads and verifies fine, and it is **correct**: it
carries only the prebuilt files (`a64emit.dll`, `lld-link.exe`, `SDL2.dll`, `SDL3.dll`, `zbic.dll`), while the builder zip
carries the 11 kits' sources (`a64-kit`, `fidelityfx`, `fidelityfx-sdk`, `fonts`, `imgui`, `kenney_input`,
`kenney_input_keyboard`, `opus`, `sdl2`, `zbic`, `zstd`). The two are meant to merge.

The bug was in `place_tool` (`builder/setup/setup.c`): it refused **any** file present on both sides, and `SDL2.dll` and
`SDL3.dll` are byte-identical in the archive and the builder zip. So the merge stopped at the first of them and every
install failed at tool 6 of 6. It now hashes both sides and accepts identical bytes (the builder's copy stays); different
bytes are still refused, as is a file against a folder. `tests/test_setup_tool_merge.py` covers both cases.

**The fix was in the source but not in the binary.** `timeLinkBuilder-Setup.exe` still predated the change, so re-running
the shipped installer still failed. Rebuilt with the command in the file's own header:

```
clang -O2 -mwindows -municode setup.c setup_rc.o -lwinhttp -lbcrypt -lcomctl32 -lshell32 -lole32 -o timeLinkBuilder-Setup.exe
```

**Re-verified end to end** with that binary, on the same zip. The installer now passes all six tools and hands over to the
builder, which then asks for game files — the correct behaviour with none given:

```
build: up to 16 compilers at once (one per CPU thread), as the memory allows; TIMELINK_JOBS=<n> to change
@@error needs --out, and --nup or --romfs with --exefs
```

State after the run: one complete version folder (no `.part`), `current.txt` written, `parts.txt` holding all **six** tool
SHA-256s including `third-party`, `tools/third_party` with all **11** kits, and `zbic/zbic.dll` plus `zbic/zbic.lib` — which
the archive carries and the zip does not — merged in from the tool. That is the merge working as designed.

## Verified 2026-11-15: shader pre-compilation

**The chain works.** `MakeGameCommand.cs:56` omits `--compile-shaders` (there is no C# flag for it) and relies on
`make_game.py:1374` `compile_level()` defaulting to `"most"`. `prepare_skipped()` returns `None` for a native Windows
build, so `make_game.py:2608` runs `timeLink.exe --prepare-shaders --compile-shaders most`. The launcher exposes the choice
to the player (`SettingsStepViewModel.cs:189-198`, "Adds about 8 min here, so the game starts smoother"), defaulting on
(`LauncherSettings.cs:25`), and `BuildStepViewModel.cs:74` shows it while building.

**Proof it ran**, from a real build in `C:\Users\iceha\timeLink-build\game`:

| Artifact | Size | Meaning |
|---|---|---|
| `cache\timeLink_vk_pipelines.bin` + `.stamp` | 1.22 GB | the pre-compiled Vulkan pipelines |
| `cache\timeLink_pipelines.bin` + `.built` | 649 MB | the prepared pipeline set |
| `cache\timeLink_prepared.bin` | 48 B | the marker the update reads |
| `timeLink_shaders.bin` | 514 MB | shipped shader set |
| `timeLink_pipeline_states_shipped.bin` | 22 MB | shipped pipeline states |

`timeLink_options.ini` holds `compile_shaders=0`, the ini's own encoding of a level — not a build failure; the caches above
are what the preparation produced.

## The tools re-host: done

All 11 archives were downloaded from MagicBeanDev's store and verified against `tools.lock`'s SHA-256 and size
(`scripts/rehost_tools.py stage`), then uploaded to the `tools` release of **`HanYolo1/timeLink-tools`** — a public
repository that holds nothing but these archives. Every `tools.lock` line names it first, keeping third-party upstream URLs
behind it where a line had them.

**Why a separate repository.** The tools could not live in `HanYolo1/timeLink`: that repository is private, and GitHub does
not serve `releases/download/` for a private repository at all. Measured:

| Request | Result |
|---|---|
| `releases/download/…` on the private repo, no auth | 404 |
| `releases/download/…` on the private repo, Bearer token | 404 |
| `releases/download/…` on the private repo, Basic auth | 404 |
| `api.github.com/…/releases/assets/<id>`, token, `Accept: application/octet-stream` | 200 |
| `releases/download/…` on the public `timeLink-tools`, no auth | **200** |
| Control: a public repo's asset, same URL shape | 200 |

The API endpoint works, but the builder's setup (`WinHttp`), the AppImage (`urllib`) and the launcher all fetch the plain
URL, and none of them can carry a token. So the archives live where a plain URL works.

**Verified end to end, with no token:** `curl` gets 200 and the right byte count; `scripts/tools.py fetch sdl2` and
`fetch third-party` both download and check their SHA-256.

**Every one of the 11 lines checked independently**, unauthenticated — status 200 and `Content-Length` equal to
`tools.lock`'s size, to the byte:

| Tool | Bytes |
|---|---|
| `llvm-mingw` (win) | 191,037,046 |
| `python` (win) | 55,961,280 |
| `emsdk` (win) | 120,100,315 |
| `cpm` (win) | 19,771,824 |
| `wgpu-native` (win) | 2,162,194 |
| `emsdk` (linux) | 141,542,909 |
| `ffmpeg` (linux) | 9,796,808 |
| `sdl2` (linux) | 889,975 |
| `sysroot` (linux) | 15,857,135 |
| `cpm` (linux) | 2,343,062 |
| `third-party` (win) | 26,639,578 |

The release API confirms `draft=false`, `prerelease=false`, 11 assets, readable with no token.

**Two defects found in the upload path and fixed** (`scripts/tools.py`), both of which would have kept the URLs dead even
after a successful upload:

1. **The release was created as a draft and never published.** `release_id()` posts `"draft": True`, and nothing flipped
   it. A draft's assets answer 404 to everyone without a token. Added `publish_tools()`, reachable as
   `python -I scripts/tools.py publish`, which PATCHes `"draft": False` once the uploads are in — the same step
   `release.py` already does for normal releases.
2. **`exists()` read an auth failure as "not there".** It caught `URLError`, which `HTTPError` subclasses, so a 401 from a
   bad token returned `(False, None, None)` and `store()` tried to upload again. It now passes 404 through as "not there"
   and fails loudly on 401/403, naming the token.

**Bumping a tool** is unchanged: `scripts/tools.py mirror` (or `add`/`assemble`) uploads the new asset, then the line
changes. `scripts/tools.py publish` publishes the release if it was a draft.

**A BOM is a silent trap here.** PowerShell 5.1's `Set-Content -Encoding utf8` writes a UTF-8 BOM. Python tolerates one in a
`.py`, but `tools.lock` is read line by line, so a BOM makes the first `tool` line stop matching and that tool becomes
invisible — the install then fails on a tool the lock appears to list. BOMs were stripped from `tools.lock`,
`tests/test_tools_lock.py`, `docs/known-issues.md` and `scripts/tools.py`, and
`Copies.test_no_release_file_starts_with_a_byte_order_mark` now guards the files that matter.

## Release process

| Issue | Detail | Mitigation |
|---|---|---|
| **One tag now means one channel** | Since both products share `v0.1.0` and one release, a launcher hotfix needs a new tag that also rebuilds the game and its builders | Accepted trade of one-release; stated in [versioning.md](versioning.md) |
| **`check_tag` says "from v0.0.0"** | `"%d.0.0" % first_major` with `first_major = 0`. Cosmetic: no test asserts it | Leave it. Changing the text breaks RELEASING.md, versioning.md and anything matching the message, for no behaviour change |
| ~~**`FIRST_VERSION` is global**~~ — **done** | It was decided from `first_major` alone, so a product starting at `v0.1.0` was indistinguishable from one starting at `v1.0.0`. Each `PRODUCTS` entry now carries its own `first_version`, and `first_version()` falls back to `FIRST_VERSION`, then to `v<major>.0.0`, so a caller asking for a higher floor keeps the old answer. `required`, `check_tag` and `next_tag` take the product | done |
| **Pre-fork tags still sort as versions** | With the floor at 0, `is_version` accepts `v3.0.0`, so a numerically higher pre-fork tag wins `max()`. `after_fork()` excludes tags before `e2a4d45`, which handles the `v2.x` ones. A `v3.x` tag *after* the rename still counts — correct for a real release, wrong for a bogus local tag | Do not re-tag old commits. Note that `origin` carries 81 upstream tags, so `git fetch --tags origin` restores them |

## Launcher

| Issue | Detail |
|---|---|
| **`HookshotSaves.cs` / `HookshotSettings.cs`: already a fork, not a rename** | Correcting an earlier note that called these untouched: they read Hookshot's layout and write timeLink's. `TargetFiles` is `timeLink_options.ini` and `language.txt`, never a `hookshot*` name; the backup folder is `hookshot-settings-<stamp>` on purpose, so a restore is recognisable. They are wired into the UI (`HookshotImportViewModel`, `HookshotSettingsViewModel`, `Views.cs`) and covered by 64 launcher-core checks (`HookshotChecks.cs` 19, `HookshotSettingsChecks.cs` 45). Both merely *accept* the strings `hookshot` and `Hookshot`; nothing is converted. What is genuinely open is narrower: no check asserts a Hookshot-authored ini lands as `timeLink_options.ini` end to end |
| **Icon and branding assets** | `Assets/timeLink.ico` and `timeLink.png` are the vendored ones renamed, not redrawn. `scripts/make_icon.py` regenerates from the png |
| **No CDN** | `CdnFetcher` was deleted (it fronted MagicBeanDev's Cloudflare edge). Release files and lists now come from GitHub directly. No replacement is needed, but a slow GitHub is not cached |
| **Shaders are not forced by the launcher** | The launcher passes no `--compile-shaders`, so the level comes from `make_game.py`'s default or the build folder's own `compile_shaders=`. It works (`most`), but an explicit flag would make the choice visible in the command line and immune to a future change of default |
| **Fixtures name a key that is not trusted** | `launcher/tests/fixtures/release/test-key.pem` is deliberately public; `ReleaseKeys.BuiltIn` is asserted not to list it |

## Test suite

| Issue | Detail |
|---|---|
| **`launcher/tests/test_release.py`: 1 failure + 5 errors on Windows** | Pre-existing and environmental: CRLF handling in a fixture upload, and jobs that need `Bash`. Identical on unmodified upstream. Not a regression from any fork change |
| **`test_launcher_core.py --strict` covers 990 checks** | Was 1033 before `CdnFetcher` went; the 43 removed assertions tested the deleted edge only |
| **Tests that read source by marker strings** | Many checks cut a function out of a source file by its text. Renaming a helper can break a check far from the change — run `python -I -B tests/run_all.py` and fix the check in the same change |

## Where `magicbean` may still appear, and why

Not every reference is a defect. Swept the tree; the remaining ones fall in four groups, and only the first was a bug.

| Where | Why it stays |
|---|---|
| **`scripts/forge.py`, `test_requests.py`, `check_pr_description.py`, `docs/forge.md`, `docs/forgejo-runners.md`** | The *team's* Forgejo at `git.magicbean.dev` is where Longshot's own pull requests, test requests and Discord sign-in live. That is not a dependency of the game; it is the collaboration tooling. Rewriting it would break the team's workflow |
| **`longshot.magicbean.dev` in `README.md`, `docs/common-issues.md`, `docs/getting-started.md`, `docs/tested*`** | These are *not* dead: the upstream site still serves them (`HEAD https://longshot.magicbean.dev/` is 200), so the report searches and the antivirus guide work today. The fork has **no deployed site** of its own to point them at (`https://hanyolo1.github.io/timeLink/` is not up), so rewriting them now would replace working links with broken ones. They become a defect the day that site goes away; rewrite them when the fork has one. 24 in `common-issues.md`, 20 in `README.md` |
| **`docs/releases.md`, `RELEASING.md`, `launcher/VENDORED.md`, `ReleaseTrust.cs`** | History: where the fork came from, which key was removed, which Forgejo mechanics no longer apply. Accurate as prose |
| **`builder/timeLinkBuilder/Program.cs`** | **Was a bug, now fixed** — see the Fixed table. A shipped binary was telling players to download the launcher from a domain this fork does not own |

## Inherited from upstream, not caused by this fork

| Issue | Detail |
|---|---|
| **Eleven translation catalogs lack one string** | `"Your game settings from your other versions now apply to this one too."` shows in English. Zero translator faults. Present in unmodified upstream |
| **`RELEASING.md` still describes Forgejo in places** | The repository, upload and runner steps were rewritten for GitHub where they act, but some Forgejo mechanics remain as history. Not user-facing |
| **`launcher/scripts/release.py` is not dead code** | Asked twice whether its `publish`/`check-tag` should be deleted now that one tag names both products. No: `.forgejo/workflows/launcher.yml` runs with `working-directory: launcher` (line 36) and calls `python3 -I -B tests/test_release.py` (line 50), which tests *that* copy, while `release.yml` calls the root copy. Both are live, for different repositories. Reviewed and kept |
| **The launcher copy's product key was half-renamed** | `launcher/scripts/release.py` renamed the `PRODUCTS` key to `timelink` but left `FILE_PREFIX` and `product_of()` saying `longshot`, so `ships()` raised `KeyError: 'timelink'` for any launcher release — every product check failed. Found because the suite went from 5 to 17 errors when the copies were regenerated; fixed by renaming all three, so the copies now differ in exactly the product key and nothing else. The remaining 1 failure + 5 errors are the pre-existing Windows/environmental ones above |
| **13 checks fail on Windows, all older than this fork's release work** | Measured 2026-11-15 with `python -I -B tests/run_all.py`: 494 passed, 14 failed, 70 skipped. The same 13 fail on `b3e24f80`, the commit before any of this work, so none is a regression: `test_cpm_discovery` (6 errors), `test_lift_cleanup_error` (5), `test_make_game_cache` (6), `test_linux_preflight`, `test_appimage_player_build`, `test_tested_configurations`, `test_walk_key`, `test_fpx_sticky`, `test_spawn_emit`, `test_env_on`, `test_readback_late`, `test_vram_budget_row`, `test_oot_state_tap`. Causes seen: the CPython 3.12 `cpm.tool.find` seam this machine lacks, `a64emit` not building here, CRLF in a piped fixture, a check needing a live game socket, several needing a Vulkan device. The fourteenth was introduced by this fork (a builder URL, `test_no_release_lookup`) and is fixed. Re-measure on Linux before blaming any of them on a change |

## Fixed (kept so it is not re-broken)

| Issue | Fixed by |
|---|---|
| Launcher trusted MagicBeanDev's release key (`5e18330371d7f5aa`) | Removed, then replaced with this fork's own (`774f1dc88462b913`) |
| `ReleaseManifest.cs` and `package.sh` disagreed on release file names (`TimeLinkLauncher-` vs `timeLinkLauncher-`), which a self-update would fail on | One spelling everywhere; a `FileNames` test holds them together |
| `release.py` wrote download links to `timeLink.magicbean.dev` / `longshot.magicbean.dev`, domains this fork does not own | `SITE` and `DOWNLOADS` now GitHub; a `ReleasePage` test fails if either names a foreign host |
| The root `scripts/release.py` still queried MagicBeanDev's Forgejo (`SERVER`, both `repo:` entries) while `release.yml` calls it | Repointed to `https://api.github.com` and `HanYolo1/timeLink`, in both copies |
| A launcher would take a builder's `v3` release for a newer launcher | Products are told apart by the files a release ships (`ReleaseManifest.Ships`, `release.py ships`), not by the tag |
| `v2.9.0` fixture depended on the old floor of 3 | Now `v2.9.0-beta`; the C# harness was red at 990 checks until fixed |
| `launcher/docs/releases.md` still described Forgejo packages, the Cloudflare edge and "seven tools not re-hosted", and `docs/known-issues.md` said `CdnFetcher` "went" when it is deleted | Both corrected against the tree: the `tools` release on `HanYolo1/timeLink-tools`, no CDN, no missing archives. Found by sweeping the docs for wording the code had outgrown — the same one-copy-fixed-one-not bug as `release.py` |
| **A shipped builder sent players to MagicBeanDev's domain** | `builder/timeLinkBuilder/Program.cs` told players to get the launcher at `https://longshot.magicbean.dev/download` in the text a `timeLinkBuilder.exe` prints when run with no arguments | `LauncherDownload` is now this fork's own releases page |
| The website linked GitHub through Forgejo paths | `website/src/site.ts` built `/src/branch/main/` and `/_edit/main/` against a GitHub repository, so every source and edit link 404d. Now `/blob/main/` and `/edit/main/`; the four anchors that read "on Forgejo" while pointing at GitHub say GitHub. Verified by importing the module and printing its URLs |
| `required(0)` returned `v0.0.0` | Returns `FIRST_VERSION` (`v0.1.0`); covered by `test_the_first_release_of_a_product_that_starts_at_zero` |
