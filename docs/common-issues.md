# Help

Find what you see below and follow its steps: each fix comes from the [manual](../README.md#if-something-goes-wrong),
with the exact message, file or setting to look for. Nothing fits, or the fix didn't work? [Still stuck?](#still-stuck)
says where the log is and how to ask.

- [Installing and building](#installing-and-building)
- [Starting the game](#starting-the-game)
- [In game: graphics](#in-game-graphics)
- [In game: performance and freezes](#in-game-performance-and-freezes)
- [In game: controls, saves and language](#in-game-controls-saves-and-language)
- [Downloads and antivirus](#downloads-and-antivirus)
- [Still stuck?](#still-stuck)

## Installing and building

### The launcher says "This version isn't supported"

Or: "timeLink supports build e0f3ccfa". timeLink builds from one version of the game only.

1. **Check the version.** You need program `0400486024DEC000` with update **v131072** (build `e0f3ccfa`); see
   [what you need](../README.md#what-you-need). The game without its update, or with another one, won't build.
2. **Check the files you chose.** Use a `.nup` file, or the `romfs` and `exefs` folders. The launcher looks for `.nup`
   files in your Downloads, Desktop and Documents folders; if the right one isn't listed, point it at the file.

[Search version reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+version)

### "Your antivirus removed part of the build tools"

A false alarm on unsigned programs: timeLink isn't code-signed yet.

1. **Get the files back.** Restore them from Windows Security's **Protection history**, and add the launcher's folders
   to its exclusions: `%LOCALAPPDATA%\timeLink Launcher` (its data: each version's builder and build tools, in
   `toolchains`, and the build files) and `%LOCALAPPDATA%\Programs\timeLink Launcher` (the launcher itself). The portable
   launcher keeps its data in `timeLinkLauncher-data` beside `timeLinkLauncher.exe` instead.
2. **Build again.** If a file is still missing, delete that version's folder in
   `%LOCALAPPDATA%\timeLink Launcher\toolchains` (it is named after the version, such as `v0.1.0`): the next build
   downloads it again and checks it.

The steps below show each one, and how to check first that the download is genuine.

[Search antivirus reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+antivirus)

### The build is very slow, or runs out of space

1. **Expect about 15 minutes on a 12-core desktop, and longer on a slower PC.** Most of the time is compiling and
   preparing shaders, which use every CPU thread, so a 6-core PC can take twice as long or more (an estimate, not a
   measurement). A hard drive works, but builds are much slower than on an SSD.
2. **Free about 60 GB** before building. The build's own files (about 4 GB) are deleted once the game is ready.

[Search build reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+build)

### Linux: the launcher or the build won't start

1. **Let the launcher run as a program.** In your file manager, open its **Properties** and turn on "Allow executing
   file as program", or run `chmod +x timeLinkLauncher-*-x86_64.AppImage`.
2. **Check your system.** Linux needs glibc 2.35 or newer (Ubuntu 22.04, Debian 12 or newer). A CPU without AVX2
   builds and plays too: the game and its renderer are built for your processor.

[Search Linux reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+Linux)

## Starting the game

### The game opens and closes, shows a black screen, or the log says "device lost"

1. **Update your graphics driver.** On Linux, update Mesa or the NVIDIA driver.
2. **Check your graphics card.** timeLink needs **Vulkan 1.3**; see [what you need](../README.md#what-you-need). A
   driver update can't add it to an older card that doesn't have it.
3. **AMD cards** have known crashes. To try the other drawing path, add the line
   `RX_VK_MESH_SHADERS=compute` to `timeLink_env.txt` in the game folder (usually a little slower; delete the line to
   undo it).
4. **Read the end of the log.** `timeLink_log.txt` in the game folder's `logs` folder has the last run; its last lines usually say what
   failed.

[Search crash reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+crash) · [Search black-screen reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+black-screen)

### Linux: the game doesn't start, or the picture is broken

1. **Check Vulkan and mesh shaders.** `vulkaninfo | grep mesh` should list `VK_EXT_mesh_shader`. The game needs a
   Vulkan 1.3 driver, ideally with mesh shaders.
2. **Update Mesa or the NVIDIA driver** if it doesn't.

[Search Linux reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+Linux)

### Linux: Play closed before the game's log appeared

Wait for the game to exit, then open `timeLink_startup.log` in the game folder's `logs` folder: it has up to 64 KiB of the game's
startup errors and its exit status. Started from a terminal, the game prints there instead.

[Search startup reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+startup)

## In game: graphics

### Parts of the picture are missing, or a message says your card has no mesh shader support

Without mesh shaders, timeLink draws through its compute fallback, which leaves some draws out.

1. **Update your graphics driver:** a card and driver with mesh shaders draw everything. NVIDIA RTX 20 series and
   newer, AMD RX 6000 series and newer, and Intel Arc have them.
2. **Check your card** against [what you need](../README.md#what-you-need).

[Search graphics reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+graphics)

### One place has a wrong texture, or a floor or wall is missing

1. **Look for `timeLink_damaged_files.txt`** in the game folder. The build writes it when your dump of the game is
   incomplete (about 23.3 GB instead of 23.8 GB), listing each damaged file and what was put in its place.
2. **Dump the game again** and build from the new dump. The file is removed once the dump is whole.

[Search texture reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+texture)

### AMD: blocky textures, solid rectangles in the sky, or dark courtyard surfaces

1. **Turn on ASTC as RGBA8:** open the menu (<kbd>F1</kbd>), go to the **Debug** tab, and under **Developer** turn on
   **ASTC as RGBA8**. Restart the game.
2. **Watch the memory.** It can use much more graphics memory, and stalls when the card runs out. To undo it, turn the
   row off and restart.

If the row can't be changed, `timeLink_env.txt` sets it: remove its `RX_VK_ASTC_RGBA8=1` line. The
[AMD texture workaround](../README.md#amd-texture-workaround) has the details.

[Search AMD reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+AMD)

## In game: performance and freezes

### It stutters the first time you see something

Normal for now: the game prepares each new shader the first time it needs it, and it is smooth the next time you pass.
You can help remove it for everyone: [send your pipeline list](../README.md#send-your-pipeline-list) (**Debug → Save my
pipeline list** in the menu).

[Search stutter reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+stutter)

### Windows, NVIDIA: it stutters on every start, in places you have seen

The driver's shader cache is too small to keep them all (the first start builds about 2 GB). Open the **NVIDIA Control
Panel**, then **Manage 3D settings**, and set **Shader Cache Size** to **Unlimited** (or 10 GB). On Linux the game raises
the driver's limit itself.

[Search stutter reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+stutter)

### Low FPS, or it slows down after a while

1. **Match the preset to your card.** In the menu's **Graphics** tab, pick the **Quality preset** for your graphics
   memory: Minimum (4GB), Low (6GB), Balanced (8GB) and so on. If the log says
   `vk: over the driver's video-memory allowance`, choose a lower one.
2. **Walk through the same spot twice** once the shaders are prepared. Note whether the slowdown clears the second time,
   or lasts until you restart.
3. **Compare fairly.** Turn off **Frame generation**, so the FPS counts the game's own frames, and keep the resolution,
   upscaler and frame rate cap the same between runs.
4. **Keep the log from the slow run** (and from the earlier version, after an update), and say where the FPS dropped.
   The [low FPS checklist](../README.md#low-fps-or-stutter) lists the log lines that matter, and a switch that times
   each GPU pass.

[Search performance reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+performance)

### Steam Deck: the game freezes and closes in the starting area or first dungeon

`journalctl -k` shows `gfx_0.0.0 timeout`. Add the line `RX_VK_MESH_NOCULL=2c56dc1006942f74` to `timeLink_env.txt` in
the game folder: it turns off the culling pass that runs for seconds there, and every model is still drawn.

[Search Steam Deck reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+Steam%20Deck)

## In game: controls, saves and language

### The menu won't open

Press <kbd>F1</kbd>: it always works. <kbd>Insert</kbd> and <kbd>Esc</kbd> do too, unless **Controls → Menu shortcut**
was changed. On a controller, press Home, or Select and Start together; on a DualShock 4 or DualSense, click the
touchpad.

[Search menu reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+menu)

### A and B are swapped, or a button does the wrong thing

1. **Check the layout.** In the menu, open **Controls → Controls** and check **Layout preset**: the default layout has A on the
   right face button, Xbox / PC and Swap Face put it on the bottom one.
2. **Rebind a button** on that page: choose its row and the Gamepad or Keyboard column, press <kbd>Enter</kbd>, then the
   new button. <kbd>Esc</kbd> cancels, <kbd>Delete</kbd> clears it, and **Reset to defaults** puts them all back.
3. **Wrong icons?** **Button prompts** on the same page picks the icons the game shows. It doesn't change what a button
   does.

The [controls reference](../README.md#controls) covers the keyboard, the mouse and rumble.

[Search controller reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+controller)

### A save is missing, or a save transfer or update went wrong

1. **Close the game** and stop copying, so nothing else is overwritten.
2. **Copy the save folder somewhere safe:** `user` in the game folder on Windows, `~/.local/share/timeLink` on Linux.
3. **Put the backup back.** Every copy the launcher makes backs up the save it replaces first:
   [undo a copy](saves.md#undo-a-copy) shows where. An update keeps your saves; the
   [updates guide](updates-and-saves.md) says what else it keeps.

Keep save files private: don't post them.

[Search save reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+save)

### The game is in the wrong language

Change the code in `language.txt` in the game folder: the file lists them all, and an update keeps the one you set.

[Search language reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+language)

## Downloads and antivirus

### Windows Defender or the browser flags the download

timeLink isn't code-signed yet, so Defender often guesses `Trojan:Win32/Wacatac.H!ml` or `Wacatac.B!ml`: the `!ml`
means a guess, not a known virus.

1. **Check where it came from.** Only [timeLink's releases](https://github.com/HanYolo1/timeLink/releases) are official.
2. **Let it through safely.** Check the file against the release's signed `SHA256SUMS`, restore it from Windows
   Security's Protection history, and exclude only timeLink's folders.

[Search antivirus reports](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue+antivirus)

## Still stuck?

1. **Make a bug report.** Open the menu (<kbd>F1</kbd>), go to **Gameplay** and choose **Bug report**. It saves a folder
   in `bug-reports` in the game folder with the log, a picture and `report.txt`, which ends with a link that opens the
   report form already filled in. Your home folder and user name are taken out.
2. **Or find the log yourself,** if the game doesn't get that far: `timeLink_log.txt` in the game folder's `logs` folder is the last
   run, and `timeLink_log.1.txt` to `.4.txt` the four before it. On Linux, `timeLink_startup.log` has the startup
   errors.
3. **Search the reports.** [Someone may have had it already](https://github.com/HanYolo1/timeLink/issues?q=is%3Aissue),
   with a workaround.
4. **Report it** with the [report form](https://github.com/HanYolo1/timeLink/issues/new): your version,
   where you were in the game, your graphics card and driver, the log and a screenshot.
   [What to include](reporting-and-contributing.md) has the details.

Never share game files, keys or saves.
