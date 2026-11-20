"""The desktop shortcut (9.7, SP-030): `solarpunk --shortcut` writes Solarpunk's icon to the user's own application
folder and puts a shortcut named Solarpunk on the desktop that starts the windows on the store in the folder it was made
from, wearing the icon. On Windows it is a .lnk made by PowerShell's WScript.Shell (part of Windows, no dependency),
pointing at solarpunk.cmd; on Linux a .desktop entry. The icon is drawn by icon.py, never kept in the repository. The
texts are pure functions, tested headless; make() runs the one command a platform needs, through a runner a test
replaces."""
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from solarpunk.ui import icon

NAME = "Solarpunk"
REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "solarpunk.cmd"
MINIMIZED = 7
Runner = Callable[[list[str]], int]


def quoted(text: str) -> str:
    """A PowerShell single-quoted string: quoted("O'Neil") is "'O''Neil'"."""
    return "'" + text.replace("'", "''") + "'"


def app_folder(env: Mapping[str, str], home: Path, windows: bool) -> Path:
    """Where the icon is kept: %LOCALAPPDATA%\\Solarpunk on Windows, ~/.local/share/solarpunk elsewhere."""
    if windows:
        return Path(env.get("LOCALAPPDATA", str(home / "AppData" / "Local"))) / NAME
    return home / ".local" / "share" / "solarpunk"


def desktop_folder(env: Mapping[str, str], home: Path) -> Path:
    """The desktop: %USERPROFILE%\\Desktop (or OneDrive's, when that is the one that exists), else ~/Desktop."""
    profile = Path(env.get("USERPROFILE", str(home)))
    for candidate in (profile / "OneDrive" / "Desktop", profile / "Desktop", home / "Desktop"):
        if candidate.is_dir():
            return candidate
    return home / "Desktop"


def windows_script(link: Path, workdir: Path, icon_file: Path) -> str:
    """The PowerShell that makes the .lnk: it runs solarpunk.cmd in the store's folder, minimized (its console out of
    the way), with Solarpunk's icon."""
    return "; ".join((
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + quoted(str(link)) + ")",
        "$s.TargetPath = " + quoted(str(LAUNCHER)),
        "$s.WorkingDirectory = " + quoted(str(workdir)),
        "$s.IconLocation = " + quoted(str(icon_file)),
        f"$s.WindowStyle = {MINIMIZED}",
        "$s.Description = " + quoted("Solarpunk: the fleet window"),
        "$s.Save()",
    ))


def desktop_entry(python: str, workdir: Path, icon_file: Path) -> str:
    """The Linux .desktop entry: the windows run from the store's folder with the repository on PYTHONPATH."""
    return "\n".join((
        "[Desktop Entry]", "Type=Application", f"Name={NAME}", "Comment=Solarpunk: the fleet window",
        f'Exec=env PYTHONPATH="{REPO}" "{python}" -m solarpunk.ui', f"Path={workdir}", f"Icon={icon_file}",
        "Terminal=false", "",
    ))


def run_command(command: list[str]) -> int:
    """Runs one command and gives its exit code."""
    return subprocess.run(command, check=False).returncode


def make(workdir: Path, env: Mapping[str, str], home: Path, windows: bool, run: Runner = run_command) -> list[str]:
    """Writes the icon and the shortcut and gives the lines saying where: on Windows solarpunk.ico and Solarpunk.lnk, on
    Linux solarpunk.png and Solarpunk.desktop; a PowerShell that fails raises OSError naming its exit code."""
    folder = app_folder(env, home, windows)
    folder.mkdir(parents=True, exist_ok=True)
    desktop = desktop_folder(env, home)
    if windows:
        icon_file = folder / "solarpunk.ico"
        icon_file.write_bytes(icon.ico())
        link = desktop / f"{NAME}.lnk"
        code = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", windows_script(link, workdir, icon_file)])
        if code != 0:
            raise OSError(f"PowerShell could not make the shortcut (exit {code})")
    else:
        icon_file = folder / "solarpunk.png"
        icon_file.write_bytes(icon.png(256))
        link = desktop / f"{NAME}.desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        link.write_text(desktop_entry(sys.executable, workdir, icon_file), encoding="utf-8")
        link.chmod(0o755)
    return [f"shortcut: icon {icon_file}", f"shortcut: {link}, starting Solarpunk in {workdir}"]
