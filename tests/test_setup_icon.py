"""builder/setup/timeLink.ico is the builder's setup program's icon, and nothing regenerated it.

It was a third picture, not the logo: the Hookshot item artwork (a blue hookshot with a chain), from `89cfc229` by
NotRexed, while `assets/timeLink.png` and `launcher/App/Assets/timeLink.png` held the Longshot logo. So the repository
carried two different identities, and the setup program - the first thing a Windows player runs - showed the older one.
`setup.rc` names the file and no check read it, so replacing the logo left it behind and nothing said so.

This check holds the setup icon to the logo it is supposed to be, the way `launcher/tests/launcher_core/IconChecks.cs`
holds the launcher's. It reads the tree, so it catches the class: any future logo change that forgets this file fails
here rather than shipping.

    python -I -B tests/test_setup_icon.py
"""
import struct
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "assets" / "timeLink.png"
SETUP_ICON = ROOT / "builder" / "setup" / "timeLink.ico"

# (nx2/make_icon.py's SIZES: the setup icon is that script's output, not the launcher's 10)
SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_pixels(data, size):
    """An 8-bit RGBA PNG's pixels, not interlaced (what the logo and the icon's 256 are)"""
    at, idat = 8, b""
    while at < len(data):
        n, kind = struct.unpack(">I4s", data[at:at + 8])
        if kind == b"IDAT":
            idat += data[at + 8:at + 8 + n]
        elif kind == b"IEND":
            break
        at += 12 + n
    raw, stride = zlib.decompress(idat), size * 4
    out, prev = bytearray(), bytearray(stride)
    for y in range(size):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += line
        prev = line
    return bytes(out)


def ico_entries(data):
    """(size, bytes) of each image in an .ico, in the order the file lists them"""
    count = struct.unpack("<H", data[4:6])[0]
    out = []
    for i in range(count):
        at = 6 + 16 * i
        size = data[at] or 256
        length, offset = struct.unpack("<II", data[at + 8:at + 16])
        out.append((size, data[offset:offset + length]))
    return out


class TheSetupIcon(unittest.TestCase):
    def test_the_setup_program_has_an_icon(self):
        self.assertTrue(SETUP_ICON.is_file(), "builder/setup/timeLink.ico is missing: setup.rc names it")

    def test_it_has_every_size_nx2_make_icon_writes(self):
        sizes = tuple(size for size, _ in ico_entries(SETUP_ICON.read_bytes()))
        self.assertEqual(sizes, SIZES, "builder/setup/timeLink.ico's sizes: %s" % (sizes,))

    def test_its_256_is_the_logo(self):
        """The old Hookshot artwork differs by about 60 of 255; the logo by under 1"""
        entries = dict(ico_entries(SETUP_ICON.read_bytes()))
        self.assertIn(256, entries, "the setup icon has no 256 image")
        icon = png_pixels(entries[256], 256)
        logo = png_pixels(LOGO.read_bytes(), 512)
        diff = 0.0
        for y in range(256):
            for x in range(256):
                for ch in range(4):
                    at = (y * 2 * 512 + x * 2) * 4 + ch
                    average = (logo[at] + logo[at + 4] + logo[at + 2048] + logo[at + 2052]) / 4.0
                    value = icon[(y * 256 + x) * 4 + ch]
                    # (colour weighted by the icon's own alpha, as IconChecks.cs does: a transparent pixel's colour is
                    # not what anyone sees)
                    diff += abs(average - value) * (1.0 if ch == 3 else value / 255.0)
        mean = diff / len(icon)
        self.assertLess(mean, 8, "builder/setup/timeLink.ico's 256 is not assets/timeLink.png "
                                 "(differs by %.1f of 255)" % mean)

    def test_setup_rc_names_it(self):
        rc = (ROOT / "builder" / "setup" / "setup.rc").read_text(encoding="utf-8")
        self.assertIn('ICON "timeLink.ico"', rc, "setup.rc no longer names timeLink.ico")


if __name__ == "__main__":
    unittest.main()
