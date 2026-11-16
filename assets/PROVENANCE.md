The start-up screen's logo and the launcher's icon: `timeLink.png` here, and `launcher/App/Assets/timeLink.png`
and `timeLink.ico` (the same picture, and the icon made from it by `launcher/scripts/make_icon.py`).

**This artwork is timeLink's own.** It was supplied by the maintainer, HanYolo1, on 2026-11-16, replacing the
Longshot logo that arrived with the fork. It is recorded here because it ships in every build and because the
picture it replaced had no licence at all.

## Where it came from

Supplied by the maintainer as a 768×768 PNG: a green disc on a white field, fully opaque. It was converted to the
512×512 RGBA that ships here by masking the disc with a 4×-supersampled ellipse and resizing with LANCZOS. The mask
is needed because the source is opaque: the start-up screen's background is `rgb(14,10,6)`, so an unmasked square
would render as a white box behind the disc. The mask radius is inset 1.5px from the disc's measured edge so the
antialiased boundary never samples the white field.

## Licence

Copyright © 2026 HanYolo1. Supplied by the project's own maintainer for use as timeLink's identity, so it carries no
third-party claim. The GPL-3.0-or-later in `LICENSE` covers the code; this image is the project's own mark.

## What it replaced

`assets/branding/longshot.png` in the upstream repository, added by commit `f7e694e8` "feat(website): add Longshot
player site and team pages (#104)", 2026-11-13, authored by `bibiburl <bibiburl@noreply.git.magicbean.dev>`. It was
renamed to `assets/timeLink.png` in `b2bbf5ee` "refactor: rename the product to timeLink, keeping the attribution"
without changing a byte — the git blob was `e1a3d996b9396cbbd016b652e30847900cfc1710` both before and after, and
`launcher/App/Assets/timeLink.png` was the same blob.

That image carried **no licence**. The upstream `assets/branding/PROVENANCE.txt` said of it, in its own words:
"Copied byte-for-byte, with no image modifications. No license or authorship inferred." It also described the assets
as "user-supplied" and dated them November 12, 2026 — written by an upstream contributor about their own team's
files, and not true of this fork's maintainer, who supplied no artwork. That file and the other `assets/branding/`
images have been deleted. None of that artwork ships here any more.

## Replacing it again

`assets/timeLink.png` is read by:

- `nx2/logo_rgba.py` — compiles it into the Vulkan back end as the start-up screen's logo. If the file is absent it
  emits an empty header and the screen shows the wordmark alone, so a build without it still works.
- `nx2/make_game.py` — copies it beside the game as the Linux window's icon, only when the file exists.
- `scripts/linux/appimage.sh` — copies it into the AppImage and its icon theme directory. This one does not check
  for the file, so removing it without editing the script fails the AppImage build.
- `launcher/App/Assets/timeLink.png` and `timeLink.ico` — the launcher's window icon and its Windows executable
  icon. `TimeLinkLauncher.csproj` lists both as `AvaloniaResource` and `ApplicationIcon`, so the launcher does not
  build without them.

A replacement must be a PNG that `nx2/logo_rgba.py` can decode (8-bit, non-interlaced, RGB or RGBA) and must be
512×512: `launcher/tests/launcher_core/IconChecks.cs` averages it down 2× to compare against the icon's 256, so a
different size breaks that test. The launcher's `.ico` is regenerated from the PNG with
`python -I launcher/scripts/make_icon.py`.

sha256 of the files as they are now:

```
1f98be64769edf1837d92d1b4f4a8ebb235d2cf2015e7615463db892c212300c  timeLink.png
1f98be64769edf1837d92d1b4f4a8ebb235d2cf2015e7615463db892c212300c  launcher/App/Assets/timeLink.png
c38e6604279e7a3a5ce0ad8e5724ccec9998a0382eec7e6aed1c5ae8fabf221d  launcher/App/Assets/timeLink.ico
```
