# Moving your saves

Your adventure is a handful of small files, the same in timeLink, Hookshot and the emulators that run the game, so it
moves between them as it is. The **timeLink Launcher** does it for you, from its **Saves** page: open **Saves** on the
launcher's home page, under the default version.

Every copy **backs up the save it replaces first**, and the launcher won't copy while timeLink, Hookshot or an emulator is
running, since a running game can write its save again and undo the copy. A copy replaces the other side's slots: it
doesn't merge two adventures.

## Before you start

1. **Save and quit.** Save in the game, then quit it (and the emulator) from its own menu, so it finishes writing.
2. **Know which adventure you want.** Note the slot and roughly when you last played: the launcher lists every save it
   finds with its slots and when each was saved.

## Import a save into timeLink

### From an emulator

1. Start timeLink once and save, so its save folder exists, then quit it.
2. On the **Saves** page, choose **Import from emulator**. The launcher lists the emulators whose saves it found on this
   PC (Lichii, Eden, Eglantine, Orchid, PokeDinner, Frizti and NX2navi), with their slots and save times.
3. Pick the save you want. If it isn't listed (a portable install, a copy on another drive), use **Choose a folder** and
   pick the save folder, or a folder that holds one.
4. Start timeLink and load your slot.

### From Hookshot

Hookshot, the project timeLink continues, writes the same save files, so a Hookshot adventure carries on in timeLink.

1. On the **Saves** page, choose **Import from Hookshot…**. (When the launcher finds Hookshot saves, its home page also
   offers this once.)
2. Pick the save. The launcher looks where Hookshot keeps them; for anywhere else, use **Choose a folder…**.
3. If timeLink already has a save, the launcher asks before replacing it, backs it up whole, and tells you where.

Hookshot's own saves stay exactly as they were: nothing in its folders is moved or changed.

## Export a save from timeLink

1. Start the emulator you're going to, save once so its folders exist, then quit it. Close timeLink too.
2. On the **Saves** page, choose **Export to emulator**, and pick the emulator, or **Choose a folder** for anywhere else.
3. Open the emulator and load your slot.

The emulator's save is backed up before it's replaced. The launcher doesn't export to Hookshot; the
[save script](#for-advanced-users-the-save-script) can.

## Between timeLink builds

- **Windows:** each build keeps its own saves. On the destination build's **Saves** page, choose **Copy saves from
  another build**. A new build or an update can also take your default build's saves itself: **Move my saves**, in the
  build wizard's second step.
- **Linux and Steam Deck:** every build already shares the same saves, so there's nothing to copy.

## Where timeLink keeps them

| | Your saves | The launcher's backups |
|---|---|---|
| Windows | `<game folder>\user\save\` (the game folder is `%USERPROFILE%\Games\timeLink` unless you chose another) | `%LOCALAPPDATA%\timeLink\oot-save-backups` |
| Linux and Steam Deck | `~/.local/share/timeLink/save/` | `~/.local/share/oot-save-backups` |

To keep your own copy, copy the save folder while the game is closed. Keep save files private.

## Undo a copy

Each copy's backup is a folder in the backups folder above, named by when it was made. Close the game, then put that
folder's contents back into the save folder, the whole set of slots at once. If something looks wrong, stop before
copying again and [open an issue](https://github.com/HanYolo1/timeLink/issues/new), without posting your save files.

## For advanced users: the save script

timeLink has the same transfers on the command line: [`scripts/oot_saves.py`](../scripts/oot_saves.py), which needs only
Python 3. It also exports to Hookshot, handles custom folders, portable installs and several profiles, and previews a
copy with `--dry-run`:

```sh
python -I scripts/oot_saves.py list              # every save it finds, its slots and when each was saved
python -I scripts/oot_saves.py import lichii     # Lichii -> timeLink
python -I scripts/oot_saves.py export lichii     # timeLink -> Lichii
```

[Saves: the files, the script and the emulators](saves-script.md) has every command and option, where each emulator
keeps its saves, copying by hand and troubleshooting.
