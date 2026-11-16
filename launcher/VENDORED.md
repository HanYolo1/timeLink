# Vendored from MagicBeanDev/LongshotLauncher

Vendored from `MagicBeanDev/LongshotLauncher` at commit `1fba5f397594fc316f9f7c3b1cf8fd7874735b9a`, 2026-11-15.
GPL-3.0-or-later. Modified for timeLink: see the git history of `launcher/`.

`App/Assets/timeLink.png` and `App/Assets/timeLink.ico` are timeLink's own artwork, supplied by HanYolo1 on
2026-11-16 and replacing the Longshot logo that came with the vendored launcher. The repository's
`assets/PROVENANCE.md` records where the picture came from and what replacing it takes.

## What this is

The timeLink Launcher: the guided flow a player uses (install the builder, choose
their own game files, build, prepare the shaders, then play and update). It was a
separate repository; this is a one-time copy into timeLink, not a submodule or a
subtree, because timeLink no longer tracks that upstream (the rename to timeLink
guarantees the two have diverged).

## GPL-3.0 obligations, and how they are met

- `LICENSE` is the launcher's own, unchanged.
- Every source file keeps its copyright header as it was written.
- The changes made after the copy are recorded here and in the git history of
  `launcher/`: the copy is its own first commit, so `git log --follow` on any file
  shows what changed and why.

## What changed after the copy

The launcher shipped as "Longshot Launcher" for "Longshot". Everything a player
sees or that names a repository, a file or an install path is timeLink's:

- `Core/ReleaseManifest.cs` — the server and its API's path (GitHub's
  `/repos/{owner}/{repo}/releases`, not Forgejo's), the products' repositories
  (both are released from `HanYolo1/timeLink`), the release file names
  (`timeLinkLauncher-*`, `timeLinkBuilder-*`, `timeLink-*`), and `Ships`/`FilePrefix`,
  which tell one product's releases from the other's now that both share a repository
  and a tag namespace.
- `Core/ReleaseTrust.cs` — **the release key was removed, not renamed.** The one
  built in was MagicBeanDev's (id `5e18330371d7f5aa`), which signs MagicBeanDev's
  releases; a launcher of this fork must not take those. `ReleaseKeys.BuiltIn` is
  empty and `scripts/release_keys.json` lists none, so until a maintainer makes a
  key (`launcher/RELEASING.md`, One-time setup, and `scripts/release.py keygen`), a
  release signed by any key is refused. That is the safe way round.
  `TIMELINK_LAUNCHER_TRUST` still takes a test key.
- `Core/LauncherLayout.cs` — the program's name (`timeLinkLauncher.exe`), its data
  folder and its install folder.
- `App/TimeLinkLauncher.csproj` — the assembly, product and company names.
- `Core/HookshotSaves.cs`, `Core/HookshotSettings.cs` — the previous products'
  save and settings layouts that players may still have. Not a rename: see the
  notes in those files.
- `scripts/package.sh`, `scripts/release.py`, `tests/` — the file names the
  launcher builds and looks for are one spelling in both (`timeLinkLauncher-*`);
  `scripts/release.py` reads GitHub's API, and both scripts tell the two products'
  releases apart by the files a release ships, not by its tag (they share `v*`).

## How it is built, checked and released here

It is a directory of timeLink, not a repository of its own:

- `.github/workflows/launcher.yml` compiles it and runs `launcher/tests/` when a
  change touches `launcher/`. Its core tests check what the launcher copies from
  timeLink (make_game.py's languages, the SDK commits the licence texts name, the
  first-import save's player ID) against the checkout `launcher/` sits in, so they
  need no separate clone.
- `.github/workflows/build-launcher.yml` builds it for a release, called by
  `release.yml` beside the builders: one tag, one release, both products' files.

## What is deliberately unchanged

`tools.lock` is timeLink's, and the launcher reads it the same way the builder
does: a tool is fetched from the first URL that answers, checked by its SHA-256.
Its archives are not in this repository (they are large binaries), so a build
needs them where `tools.lock` says they are.
