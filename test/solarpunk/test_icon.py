"""Solarpunk's icon and desktop shortcut (9.7, SP-030, SP-031): each size's PNG and the ICO headless (icon.py has
no tkinter), the shortcut's texts and make() with a runner standing in for PowerShell and temporary folders standing in
for the user's own, then, under a display, every window wearing the icon. Skips "no tkinter" or "no display" as
test_ui.py does. PowerShell is never run here."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from solarpunk.ui import icon, shortcut

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import __main__ as entry

FAKE_PNG = b"\x89PNG fake"
FAKE_ICO = b"\x00\x00\x01\x00 fake"


def header_of(data: bytes) -> tuple[int, int, int, int, int]:
    """A PNG's width, height, bit depth, colour type and interlace from its IHDR: (16, 16, 8, 6, 0) for the 16 px art,
    8-bit RGBA, not interlaced (what Tk and Windows both read)."""
    width, height, depth, colour, _compression, _filter, interlace = struct.unpack(">IIBBBBB", data[16:29])
    return width, height, depth, colour, interlace


class TheIcon(unittest.TestCase):
    def test_every_size_is_its_own_rgba_png(self) -> None:
        for size in icon.SIZES:
            with self.subTest(size=size):
                data = icon.png(size)
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(data[12:16], b"IHDR")
                self.assertEqual(header_of(data), (size, size, 8, 6, 0))

    def test_a_size_with_no_art_says_so(self) -> None:
        with self.assertRaisesRegex(ValueError, "no icon at 20 px"):
            icon.png(20)

    def test_the_art_folder_holds_the_sizes_and_their_sources_and_nothing_else(self) -> None:
        names = sorted(p.name for p in icon.ART.iterdir())
        pngs = [f"solarpunk_{size}.png" for size in icon.SIZES]
        self.assertEqual(names, sorted(pngs + ["solarpunk.svg", "solarpunk_small.svg", "solarpunk_tiny.svg"]))
        for source in icon.ART.glob("*.svg"):  # plain drawing: nothing that runs or reaches out
            text = source.read_text(encoding="utf-8").lower()
            self.assertNotIn("<script", text)
            self.assertNotIn("href=\"http", text)

    def test_the_ico_lists_each_size_and_where_its_png_starts(self) -> None:
        data = icon.ico((16, 256))
        self.assertEqual(struct.unpack("<HHH", data[:6]), (0, 1, 2))
        entries = [struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i]) for i in range(2)]
        self.assertEqual([(e[0], e[1], e[5]) for e in entries], [(16, 16, 32), (0, 0, 32)])  # 256 is written 0
        for side, entry in zip((16, 256), entries):
            self.assertEqual(data[entry[7]:entry[7] + entry[6]], icon.png(side))
        self.assertEqual(entries[1][7], entries[0][7] + entries[0][6])
        self.assertEqual(struct.unpack("<H", icon.ico()[4:6]), (7,))


class TheShortcutsWords(unittest.TestCase):
    def test_powershell_quoting(self) -> None:
        self.assertEqual(shortcut.quoted("O'Neil"), "'O''Neil'")

    def test_the_folders(self) -> None:
        home = Path("/home/ana")
        self.assertEqual(shortcut.app_folder({"LOCALAPPDATA": r"C:\Users\ana\AppData\Local"}, home, True),
                         Path(r"C:\Users\ana\AppData\Local") / "Solarpunk")
        self.assertEqual(shortcut.app_folder({}, home, False), home / ".local" / "share" / "solarpunk")
        with tempfile.TemporaryDirectory() as name:
            profile = Path(name)
            self.assertEqual(shortcut.desktop_folder({"USERPROFILE": name}, profile), profile / "Desktop")
            (profile / "OneDrive" / "Desktop").mkdir(parents=True)
            self.assertEqual(shortcut.desktop_folder({"USERPROFILE": name}, profile), profile / "OneDrive" / "Desktop")

    def test_the_windows_script_points_at_the_launcher_with_the_icon(self) -> None:
        script = shortcut.windows_script(Path("D/Solarpunk.lnk"), Path("W"), Path("A/solarpunk.ico"))
        self.assertIn("CreateShortcut('" + str(Path("D/Solarpunk.lnk")) + "')", script)
        self.assertIn("$s.TargetPath = '" + str(shortcut.LAUNCHER) + "'", script)
        self.assertIn("$s.IconLocation = '" + str(Path("A/solarpunk.ico")) + "'", script)
        self.assertIn("$s.WindowStyle = 7", script)
        self.assertTrue(script.endswith("$s.Save()"))

    def test_the_desktop_entry_runs_the_windows_from_the_store_folder(self) -> None:
        text = shortcut.desktop_entry("/usr/bin/python3", Path("/srv/oahe"), Path("/icons/solarpunk.png"))
        lines = text.splitlines()
        self.assertEqual(lines[0], "[Desktop Entry]")
        self.assertIn(f'Exec=env PYTHONPATH="{shortcut.REPO}" "/usr/bin/python3" -m solarpunk.ui', lines)
        self.assertIn("Path=/srv/oahe", lines)
        self.assertIn("Icon=/icons/solarpunk.png", lines)


@mock.patch.object(shortcut.icon, "ico", lambda: FAKE_ICO)
@mock.patch.object(shortcut.icon, "png", lambda size: FAKE_PNG)
class MakingIt(unittest.TestCase):
    def setUp(self) -> None:
        """A temporary home with a Desktop, and the commands make() would run."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        (self.home / "Desktop").mkdir()
        self.commands: list[list[str]] = []

    def runner(self, code: int) -> shortcut.Runner:
        """A runner that keeps each command and exits with code."""
        def run(command: list[str]) -> int:
            """Keeps the command and exits: run(["powershell", ...]) is code, the command kept."""
            self.commands.append(command)
            return code
        return run

    def test_on_windows_the_ico_and_one_powershell(self) -> None:
        env = {"LOCALAPPDATA": str(self.home / "Local"), "USERPROFILE": str(self.home)}
        lines = shortcut.make(Path("W"), env, self.home, True, self.runner(0))
        icon_file = self.home / "Local" / "Solarpunk" / "solarpunk.ico"
        self.assertEqual(icon_file.read_bytes(), FAKE_ICO)
        (command,) = self.commands
        self.assertEqual(command[:4], ["powershell", "-NoProfile", "-NonInteractive", "-Command"])
        self.assertIn(str(self.home / "Desktop" / "Solarpunk.lnk"), command[4])
        self.assertEqual(lines, [f"shortcut: icon {icon_file}",
                                 f"shortcut: {self.home / 'Desktop' / 'Solarpunk.lnk'}, starting Solarpunk in W"])

    def test_a_failing_powershell_says_so(self) -> None:
        with self.assertRaisesRegex(OSError, r"exit 1\)"):
            shortcut.make(Path("W"), {"USERPROFILE": str(self.home)}, self.home, True, self.runner(1))

    def test_on_linux_the_png_and_a_desktop_entry_and_no_command(self) -> None:
        lines = shortcut.make(Path("/srv/oahe"), {}, self.home, False, self.runner(0))
        entry_file = self.home / "Desktop" / "Solarpunk.desktop"
        self.assertEqual((self.home / ".local" / "share" / "solarpunk" / "solarpunk.png").read_bytes(), FAKE_PNG)
        self.assertIn("Path=/srv/oahe", entry_file.read_text(encoding="utf-8").splitlines())
        self.assertTrue(entry_file.stat().st_mode & 0o100)
        self.assertEqual((self.commands, len(lines)), ([], 2))


@unittest.skipUnless(HAS_TKINTER, "no tkinter")
class TheWindowWearsIt(unittest.TestCase):
    def test_the_root_and_its_windows_take_the_icon(self) -> None:
        try:
            root = tkinter.Tk()
        except tkinter.TclError:
            self.skipTest("no display")
        self.addCleanup(root.destroy)
        root.withdraw()
        entry.wear_icon(root)
        self.assertEqual([(i.width(), i.height()) for i in root.icon_images], [(64, 64), (32, 32)])
        self.assertTrue(root.icon_images[1].transparency_get(0, 0))  # a clear corner outside the badge
        self.assertFalse(root.icon_images[1].transparency_get(16, 16))

    def test_shortcut_opens_no_window(self) -> None:
        out: list[str] = []
        with mock.patch.object(entry.shortcut, "make", return_value=["shortcut: made"]) as made, \
                mock.patch.object(entry.tkinter, "Tk") as tk:
            self.assertEqual(entry.main(["--shortcut"], mock.Mock(write=out.append)), 0)
        made.assert_called_once()
        tk.assert_not_called()
        self.assertEqual(out, ["shortcut: made\n"])


if __name__ == "__main__":
    unittest.main()
