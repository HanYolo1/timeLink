# Notes for AI coding agents

Follow [CONTRIBUTING.md](CONTRIBUTING.md): its rules apply to agents as to everyone, above all that no game files, saves or
anything made from them leave the PC. [README.md](README.md) has the layout and the commands, [docs/releases.md](docs/releases.md)
how releases are made and checked, and [docs/saves.md](docs/saves.md) the saves, with what is imported from Hookshot (its
saves, and its compatible game settings).

What agents trip on:

- **Clean break.** Only Hookshot's saves (`Core/HookshotSaves.cs`) and the compatible game settings explicitly selected for
  a timeLink build (`Core/HookshotSettings.cs`) are imported. Keep its launcher settings, channels, versions and caches
  separate. Don't add compatibility with Hookshot's 2.x builders.
- **Tests read the source.** Run `python -I tests/test_launcher_core.py` and `python -I tests/test_release.py` before a pull
  request; update a check in the same pull request rather than weakening it.
- **One repository, two copies.** The launcher lives in timeLink's repository (`launcher/`). `launcher/scripts/release.py`
  and `launcher/docs/releases.md` are copies of timeLink's `scripts/release.py` and `docs/releases.md`; a change to either
  goes to both (`tests/test_release.py` checks the scripts). The trusted key is in `Core/ReleaseTrust.cs` and in timeLink's
  `scripts/release_keys.json`.
- **Never make or commit a real signing key**, and never publish a release by hand: tags and the release workflow do it
  ([RELEASING.md](RELEASING.md)).
- **jj or git**: `main` is protected; push a branch and open a pull request on HanYolo1/timeLink. Never push to `main`
  directly.

Pull requests: **open the description with why the PR is needed**, in one or two plain sentences, and include
screenshots when the change shows on screen.
