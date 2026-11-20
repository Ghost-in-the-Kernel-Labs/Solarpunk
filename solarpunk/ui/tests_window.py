"""The Manage tests window (9.8, SP-030): every script in the remote tests' folder with its kinds, clauses and the codes
a failure suggests, a script that cannot load listed in red with its reason rather than stopping the window. "Open
folder" opens the folder in the system's file manager, "New test" writes the scaffold `solarpunk test add` writes, and
"Reload" reads the folder again, so a script dropped in appears. A test is a Python script (SP-020). The words are
tests_text.py's, over two project calls; the class only lays them out (SP-010: it imports project and the leaf alone)."""
import subprocess
import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import tests_text

TITLE = "Manage tests"
OPEN_FOLDER, NEW_TEST, RELOAD = "Open folder", "New test", "Reload"
NEW_TITLE = "New test"
NAME, KINDS, CLAUSE, CREATE = "Name", "Kinds (blank: the maintenance list's)", "Clause", "Create"
BROKEN_COLOUR = "#b00020"
Opener = Callable[[list[str]], None]


def start(command: list[str]) -> None:
    """Starts a command and leaves it running: start(["xdg-open", "/x"]) opens /x in the file manager."""
    subprocess.Popen(command)  # the file manager outlives the call; nothing waits on it


class ManageTestsWindow(tk.Toplevel):
    """ManageTestsWindow(root) lists solarpunk/remote/tests/; a test hands it another folder and an opener that keeps
    the command rather than starting a file manager."""

    def __init__(self, parent: tk.Misc, folder: Path | None = None, opener: Opener = start) -> None:
        """Lays out the buttons, the line and the list, then reads the folder."""
        super().__init__(parent)
        self.folder = folder or project.remote_tests_folder()
        self.opener = opener
        self.title(TITLE)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        self.open_button = ttk.Button(bar, text=OPEN_FOLDER, command=self.open_folder)
        self.new_button = ttk.Button(bar, text=NEW_TEST, command=lambda: NewTestWindow(self, self.folder, self.created))
        self.reload_button = ttk.Button(bar, text=RELOAD, command=self.reload)
        for button in (self.open_button, self.new_button, self.reload_button):
            button.pack(side="left")
        self.line = ttk.Label(self)
        self.line.pack(fill="x", padx=8)
        self.tree = ttk.Treeview(self, columns=tests_text.COLUMNS, show="headings", height=12)
        for column in tests_text.COLUMNS:
            self.tree.heading(column, text=column)
            self.tree.column(column, stretch=column == "Problem")
        self.tree.tag_configure(tests_text.BROKEN, foreground=BROKEN_COLOUR)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.reload()

    def reload(self) -> None:
        """Reads the folder again and lists every script, a broken one in red with its reason."""
        self.tree.delete(*self.tree.get_children())
        entries = project.survey_remote_tests(self.folder)
        rows = [tests_text.row_of(found) for found in entries]
        for found, row in zip(entries, rows):
            tags = (tests_text.BROKEN,) if found.test is None else ()
            self.tree.insert("", "end", iid=found.name, values=row, tags=tags)
        measure = tkfont.nametofont("TkDefaultFont").measure
        for column, width in zip(tests_text.COLUMNS, tests_text.widths(rows, measure)):
            self.tree.column(column, width=width, minwidth=width)
        self.line.configure(text=tests_text.summary(entries, self.folder))

    def open_folder(self) -> None:
        """Opens the folder in the system's file manager; a file manager that cannot start is said in the line."""
        try:
            self.opener(tests_text.open_command(sys.platform, self.folder))
        except OSError as error:
            self.line.configure(text=tests_text.cannot_open(self.folder, error))

    def created(self, path: Path) -> None:
        """After New test writes a script: the list read again, the new row chosen and the line saying what next."""
        self.reload()
        if self.tree.exists(path.stem):
            self.tree.selection_set(path.stem)
            self.tree.see(path.stem)
        self.line.configure(text=tests_text.written(path))


class NewTestWindow(tk.Toplevel):
    """The New test form: a name, its kinds (blank for the maintenance list's) and a clause; Create writes the scaffold
    and hands its path to on_created, or says in red why it cannot, writing nothing."""

    def __init__(self, parent: tk.Misc, folder: Path, on_created: Callable[[Path], None]) -> None:
        """Lays out the three fields, Create and the line for a refusal."""
        super().__init__(parent)
        self.folder = folder
        self.on_created = on_created
        self.title(NEW_TITLE)
        self.name, self.kinds, self.clause = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for row, (words, variable) in enumerate(((NAME, self.name), (KINDS, self.kinds), (CLAUSE, self.clause))):
            ttk.Label(self, text=words).grid(row=row, column=0, sticky="w", padx=8, pady=3)
            ttk.Entry(self, textvariable=variable, width=32).grid(row=row, column=1, sticky="ew", padx=8, pady=3)
        self.create_button = ttk.Button(self, text=CREATE, command=self.create)
        self.create_button.grid(row=3, column=1, sticky="e", padx=8, pady=6)
        self.line = ttk.Label(self, foreground=BROKEN_COLOUR, wraplength=360)
        self.line.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

    def create(self) -> None:
        """Writes the scaffold, then closes; a refusal (a taken name, an unknown kind, no clause) stays open with its
        reason."""
        try:
            path = project.add_remote_test(self.name.get().strip(), tests_text.kinds_of(self.kinds.get()),
                                           tests_text.words_of(self.clause.get()), self.folder)
        except ValueError as error:
            self.line.configure(text=str(error))
            return
        self.destroy()
        self.on_created(path)
