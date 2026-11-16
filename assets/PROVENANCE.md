The start-up screen's logo and the launcher's icon: `timeLink.png` here, and `launcher/App/Assets/timeLink.png`
and `timeLink.ico` (the same picture, and the icon made from it by `launcher/scripts/make_icon.py`).

**This is not timeLink's own artwork.** It is Longshot's logo, inherited through the fork and renamed. It is
recorded here because it ships in every build and its origin was previously misstated.

## Where it came from

`assets/branding/longshot.png` in the upstream repository, added by commit `f7e694e8` "feat(website): add Longshot
player site and team pages (#104)", 2026-11-13, authored by `bibiburl <bibiburl@noreply.git.magicbean.dev>`.

It was renamed to `assets/timeLink.png` in `b2bbf5ee` "refactor: rename the product to timeLink, keeping the
attribution". The bytes were not changed: the git blob is `e1a3d996b9396cbbd016b652e30847900cfc1710` both before and
after the rename, and `launcher/App/Assets/timeLink.png` is the same blob.

## Licence

**None granted.** The upstream `assets/branding/PROVENANCE.txt` said of these files, in its own words: "Copied
byte-for-byte, with no image modifications. No license or authorship inferred." The GPL-3.0-or-later in `LICENSE`
covers the code; it says nothing about artwork, and no separate grant exists for this image.

That file also described the assets as "user-supplied" and dated them November 12, 2026. That was written by an
upstream contributor about their own team's files. It was not true of this fork's maintainer, who supplied no
artwork, and it has been deleted along with the other `assets/branding/` images.

## What this means

The image is redistributed as it arrived with the fork, with its origin recorded rather than a licence claimed for
it. It should be replaced with artwork this project owns before it is treated as timeLink's identity.

## Replacing it

`assets/timeLink.png` is read by:

- `nx2/logo_rgba.py` — compiles it into the Vulkan back end as the start-up screen's logo. If the file is absent it
  emits an empty header and the screen shows the wordmark alone, so a build without it still works.
- `nx2/make_game.py` — copies it beside the game as the Linux window's icon, only when the file exists.
- `scripts/linux/appimage.sh` — copies it into the AppImage and its icon theme directory. This one does not check
  for the file, so removing it without editing the script fails the AppImage build.
- `launcher/App/Assets/timeLink.png` and `timeLink.ico` — the launcher's window icon and its Windows executable
  icon. `TimeLinkLauncher.csproj` lists both as `AvaloniaResource` and `ApplicationIcon`, so the launcher does not
  build without them.

A replacement must be a PNG that `nx2/logo_rgba.py` can decode (8-bit, non-interlaced, RGB or RGBA), and the
launcher's `.ico` is regenerated from the PNG with `python -I launcher/scripts/make_icon.py`.

sha256 of the files as they are now:

```
9186c5ea9c3c5d4b22725d3dbffd4eb81a8965f66cebbcfa1c492423b9defb2b  timeLink.png
```
