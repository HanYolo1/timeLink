"""The Hookshot settings import writes into timeLink's own options file, so it has to agree with the version the game writes.

launcher/Core/HookshotSettings.cs imports a Hookshot game folder's hookshot_options.ini into the build's
timeLink_options.ini. It does not convert the file: it keeps the build's lines, puts the imported keys in place, and
writes Hookshot's options_version into the marker, so that timeLink's own reader migrates the imported rows exactly as
it would migrate a Hookshot file (Merge, and the Migrated table of which rows moved at which version).

That only holds while the numbers agree. Hookshot's settings stop at options_version=4, and the launcher refuses a
newer one on purpose ("This Hookshot settings version has not been checked for timeLink"), because a version it has
not reviewed might carry a row whose meaning moved. The other half is the game's own number, which
gpu/vk/vk_menu.cpp writes on every save. When that goes up, the launcher's comment naming the version it was checked
against - and the Migrated table built on it - are stale, and nothing else would say so.

This check fails when:
  - the game writes a version other than the one HookshotSettings.cs says it was checked against, so a bump of the
    game's format is noticed here instead of silently mis-migrating a player's settings;
  - Hookshot's ceiling moves without the comment that records the review (a new ceiling is a decision, not a typo);
  - the Migrated table names a version above the game's, which cannot happen if both are honest.

It reads the sources by their text, like the other checks in this folder that cut a function out of a file.
"""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "launcher" / "Core" / "HookshotSettings.cs"
MENU = ROOT / "gpu" / "vk" / "vk_menu.cpp"

# (the highest Hookshot options_version the launcher accepts: a reviewed decision, and the comment beside it says so)
CHECKED_HOOKSHOT_CEILING = 4


class OptionsVersion(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SETTINGS.is_file() and MENU.is_file(), "both sources are needed")
        self.settings = SETTINGS.read_text(encoding="utf-8", errors="replace")
        self.menu = MENU.read_text(encoding="utf-8", errors="replace")

    def game_version(self):
        """The options_version the game writes when it saves: fprintf(f, "options_version=6\\n")"""
        found = re.findall(r'"options_version=(\d+)\\n"', self.menu)
        self.assertTrue(found, "vk_menu.cpp no longer writes an options_version line; the import's marker assumes it does")
        writes = {int(v) for v in found}
        self.assertEqual(len(writes), 1, "vk_menu.cpp writes more than one options_version (%s)" % sorted(writes))
        return writes.pop()

    def checked_against(self):
        """The game version HookshotSettings.cs says the import was checked against: 'Checked against timeLink's options_version 6'"""
        found = re.findall(r"Checked against timeLink's options_version (\d+)", self.settings)
        self.assertTrue(found, "HookshotSettings.cs no longer says which timeLink options_version it was checked against")
        return int(found[0])

    def test_the_import_was_checked_against_the_version_the_game_writes(self):
        self.assertEqual(self.checked_against(), self.game_version(),
                         "gpu/vk/vk_menu.cpp writes options_version %d but launcher/Core/HookshotSettings.cs was checked "
                         "against %d: review HookshotSettings.Migrated against the game's reader before shipping"
                         % (self.game_version(), self.checked_against()))

    def test_hookshot_settings_stop_where_they_were_reviewed(self):
        found = re.findall(r'key == "options_version"', self.settings)
        self.assertTrue(found, "the options_version branch is gone from HookshotSettings.cs")
        ceilings = {int(n) for n in re.findall(r"Integer\(value, 0, (\d+)\)", self.settings)}
        self.assertIn(CHECKED_HOOKSHOT_CEILING, ceilings,
                      "Hookshot's accepted options_version changed to %s. A new ceiling is a decision: review what rows "
                      "moved in it, then update CHECKED_HOOKSHOT_CEILING here and the comment beside the check"
                      % sorted(ceilings))
        self.assertIn("has not been checked for timeLink", self.settings,
                      "the refusal message is what tells a player why a newer file was not imported")

    def test_the_migrated_rows_do_not_claim_a_later_version_than_the_game_has(self):
        block = re.search(r"static readonly \(string Key, int Since\)\[\] Migrated =\s*\{(.*?)\};", self.settings, re.S)
        self.assertIsNotNone(block, "the Migrated table is gone; the import no longer knows which rows moved when")
        sinces = [int(n) for n in re.findall(r",\s*(\d+)\)", block.group(1))]
        self.assertTrue(sinces, "the Migrated table names no version")
        self.assertLessEqual(max(sinces), self.game_version(),
                             "Migrated moves a row at version %d, but the game stops at %d: the table names a version "
                             "timeLink has never written" % (max(sinces), self.game_version()))

    def test_the_import_writes_the_builds_file_and_never_hookshots(self):
        """(the adaptation in one line: reads hookshot_options.ini, writes timeLink_options.ini. A name on the write side
        would be Hookshot's layout leaking back in)"""
        target = re.search(r"TargetFiles = \{(.*?)\};", self.settings)
        self.assertIsNotNone(target, "TargetFiles is gone")
        names = set(re.findall(r'"([^"]+)"', target.group(1)))
        self.assertEqual(names, {"timeLink_options.ini", "language.txt"},
                         "the import writes %s; timeLink's own two settings files are timeLink_options.ini and "
                         "language.txt" % sorted(names))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()