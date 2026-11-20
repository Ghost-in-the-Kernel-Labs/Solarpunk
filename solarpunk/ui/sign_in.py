"""The sign-in dialog (12.3, SOL-16, SP-032): in a store that holds an active account the windows open on it, and the
fleet window opens only after a good sign-in; closing the dialog closes the program. A failed sign-in says so in red,
in words that tell nobody which part was wrong, and is kept with the account named and its instant, never the password
(project.sign_in). A store with no account opens the fleet window at once, as it did before accounts. The words are
cells.py's; the class only lays them out (SP-010: it imports project and the leaf alone)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timezone
from tkinter import ttk

from solarpunk import project
from solarpunk.ui import cells

TITLE = "Sign in to Solarpunk"
EMAIL, PASSWORD, SIGN_IN = "Email", "Password", "Sign in"
REFUSED_COLOUR = "#b00020"
OnSigned = Callable[[project.Account | None], None]


def start(root: tk.Tk, conn: sqlite3.Connection, on_signed: OnSigned) -> "SignInWindow | None":
    """Hands on_signed the account at the window: at once with None in a store with no account; else after the dialog
    signs one in, the root hidden till then. Returns the dialog, or None when none was needed."""
    # Decision: SP-032 (no accounts, no sign-in)
    if not project.needs_sign_in(conn):
        on_signed(None)
        return None
    root.withdraw()
    return SignInWindow(root, conn, on_signed)


class SignInWindow(tk.Toplevel):
    """SignInWindow(root, conn, on_signed): an email, a password shown as dots, Sign in, and a line for a refusal."""

    def __init__(self, root: tk.Tk, conn: sqlite3.Connection, on_signed: OnSigned) -> None:
        """Lays out the fields, Enter signing in as the button does, and closing the dialog closing the program."""
        super().__init__(root)
        self.root, self.conn, self.on_signed = root, conn, on_signed
        self.title(TITLE)
        self.email, self.password = tk.StringVar(), tk.StringVar()
        for row, (words, variable, show) in enumerate(((EMAIL, self.email, ""), (PASSWORD, self.password, "•"))):
            ttk.Label(self, text=words).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            entry = ttk.Entry(self, textvariable=variable, width=32, show=show)
            entry.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            if row == 0:
                entry.focus_set()
        self.sign_in_button = ttk.Button(self, text=SIGN_IN, command=self.sign_in)
        self.sign_in_button.grid(row=2, column=1, sticky="e", padx=8, pady=6)
        self.line = ttk.Label(self, foreground=REFUSED_COLOUR, wraplength=320)
        self.line.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))
        self.bind("<Return>", lambda _event: self.sign_in())
        self.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def sign_in(self) -> None:
        """Checks the email and password: a good pair closes the dialog, shows the root and hands on the account; a bad
        one empties the password and says so, the failure kept."""
        found = project.sign_in(self.conn, self.email.get(), self.password.get(), datetime.now(timezone.utc))
        self.password.set("")
        if found is None:
            self.line.configure(text=cells.NO_MATCH)
            return
        self.destroy()
        self.root.deiconify()
        self.on_signed(found)
