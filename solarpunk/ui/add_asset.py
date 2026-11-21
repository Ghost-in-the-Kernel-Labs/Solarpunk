"""The add-asset window (3.3, SP-007): id, name, site, parent, type, rated kW, location, engineer email, IP address and
port; Save registers through project and shows the fleet's refusal verbatim, never swallowing it; Ping reads the saved
asset's feed once through project. The form's text becomes an Asset in pure functions tested headless; the window only
lays out widgets and calls them. Imports project and the leaf alone (SP-010, MOD-06)."""
import sqlite3
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from solarpunk import project
from solarpunk.leaf.asset_types import KIND_BY_NAME
from solarpunk.leaf.assets import Asset, parse_asset_id
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample

TITLE = "Add an asset"
NO_PARENT = "<none>"
DEFAULT_KIND = "INVERTER"
ERROR_COLOUR = "#b00020"
OK_COLOUR = "#1b5e20"
PORT_NOT_WHOLE = "port must be a whole number"
RATED_NOT_NUMBER = "rated kW must be a number"
UNKNOWN_TYPE = "{name!r} is not an asset type"
SAVED = "Saved {asset_id}"
SAVED_BUTTON = "Saved"
PING_NONE = "Ping: no records"
PING_SOME = "Ping: {count} {noun}, first at {first}"
FIRST_GAP = "{at}, a gap"
FIRST_VALUES = "{at}, irradiance {irradiance} W/m2, power {power} kW"
RECORD = "record"
RECORDS = "records"
SAVE = "Save"
CANCEL = "Cancel"
PING = "Ping"
REFRESH = "Refresh parents"
TYPE_LABEL = "Type"
PARENT_LABEL = "Parent"
# The text entries, in the form's order: (key, label). The type and parent are dropdowns placed after "site".
ENTRIES_BEFORE: tuple[tuple[str, str], ...] = (("id", "Id"), ("name", "Name"), ("site", "Site"))
ENTRIES_AFTER: tuple[tuple[str, str], ...] = (
    ("rated_kw", "Rated kW"), ("location", "Location"), ("email", "Engineer email"),
    ("host", "IP address"), ("port", "Port"),
)


def optional(text: str) -> str | None:
    """The trimmed text, None when nothing is left: optional("  Pad A ") is "Pad A"; optional("  ") is None."""
    trimmed = text.strip()
    return trimmed or None


def port_of(text: str) -> int | None:
    """The port as a whole number, None when blank: port_of(" 5020 ") is 5020; port_of("") is None; port_of("50.5")
    raises ValueError("port must be a whole number")."""
    found = optional(text)
    if found is None:
        return None
    if not found.isdigit():
        raise ValueError(PORT_NOT_WHOLE)
    return int(found)


def rated_of(text: str) -> float | None:
    """The rated kW as a number, None when blank: rated_of("100") is 100.0; rated_of("") is None; rated_of("lots")
    raises ValueError("rated kW must be a number")."""
    found = optional(text)
    if found is None:
        return None
    try:
        return float(found)
    except ValueError as error:
        raise ValueError(RATED_NOT_NUMBER) from error


def kind_named(name: str) -> AssetKind:
    """The kind a type name in the dropdown names: kind_named("TRACKER") is AssetKind.TRACKER; kind_named("PANEL")
    raises ValueError("'PANEL' is not an asset type")."""
    if name not in KIND_BY_NAME:
        raise ValueError(UNKNOWN_TYPE.format(name=name))
    return KIND_BY_NAME[name]


def asset_from_form(values: dict[str, str]) -> Asset:
    """The form's text as a leaf Asset, the leaf's refusals propagating: {"id": "OAHE-INV-009", "name": "Inverter 9",
    "site": "OAHE", "parent": "OAHE-SIT-001", "type": "INVERTER", "rated_kw": "100", "location": "Pad C", "email":
    "a@b.org", "host": "10.0.0.9", "port": "5020"} is that inverter; a parent "<none>" is None; a port without a host
    raises ValueError("…: host and port come together")."""
    parent = optional(values["parent"])
    return Asset(
        asset_id=values["id"].strip(),
        kind=kind_named(values["type"]),
        site=values["site"].strip(),
        parent_id=None if parent == NO_PARENT else parent,
        name=values["name"].strip(),
        rated_kw=rated_of(values["rated_kw"]),
        host=optional(values["host"]),
        port=port_of(values["port"]),
        location=optional(values["location"]),
        engineer_email=optional(values["email"]),
    )


def kind_names(kinds: tuple[AssetKind, ...]) -> tuple[str, ...]:
    """The dropdown's names, in the list's order: kind_names((AssetKind.SITE, AssetKind.INVERTER)) is ("SITE",
    "INVERTER")."""
    return tuple(kind.name for kind in kinds)


def default_kind(names: tuple[str, ...]) -> str:
    """The type the form opens with: INVERTER when the list holds it, else the list's first: default_kind(("SITE",
    "INVERTER")) is "INVERTER"; default_kind(("SITE",)) is "SITE"."""
    return DEFAULT_KIND if DEFAULT_KIND in names else names[0]


def site_of(asset_id: str) -> str | None:
    """The site an id names, None for an id of another shape: site_of("OAHE-INV-001") is "OAHE"; site_of("x") None."""
    try:
        return parse_asset_id(asset_id)[0]
    except ValueError:
        return None


def parent_choices(asset_ids: tuple[str, ...], site: str) -> tuple[str, ...]:
    """The parent dropdown: "<none>" first, then the ids at the site, or every id while the site is blank:
    parent_choices(("OAHE-SIT-001", "FALL-SIT-001"), "OAHE") is ("<none>", "OAHE-SIT-001")."""
    wanted = site.strip()
    return (NO_PARENT,) + tuple(found for found in asset_ids if not wanted or site_of(found) == wanted)


def first_record(sample: Sample) -> str:
    """The first record in words: a reading gives "2026-06-01T10:05:00+00:00, irradiance 812.0 W/m2, power 78.4 kW",
    a gap "2026-06-01T10:05:00+00:00, a gap"."""
    instant = sample.moment.isoformat()
    if sample.gap:
        return FIRST_GAP.format(at=instant)
    return FIRST_VALUES.format(at=instant, irradiance=sample.irradiance_w_m2, power=sample.power_kw)


def ping_summary(samples: tuple[Sample, ...]) -> str:
    """What Ping shows: no samples give "Ping: no records"; one gives "Ping: 1 record, first at <first_record>"; 24
    give "Ping: 24 records, first at <first_record of the first>"."""
    if not samples:
        return PING_NONE
    noun = RECORD if len(samples) == 1 else RECORDS
    return PING_SOME.format(count=len(samples), noun=noun, first=first_record(samples[0]))


def message_colour(succeeded: bool) -> str:
    """The message Label's colour: message_colour(True) is the green "#1b5e20", message_colour(False) the red
    "#b00020"."""
    return OK_COLOUR if succeeded else ERROR_COLOUR


class AddAssetWindow(tk.Toplevel):
    """The add-asset window: AddAssetWindow(root, conn) opens "Add an asset" over the store; filling it and pressing
    Save registers the asset through project, says "Saved <id>", calls on_saved(id) and enables Ping."""

    def __init__(self, parent: tk.Misc, conn: sqlite3.Connection,
                 on_saved: Callable[[str], None] = lambda asset_id: None) -> None:
        """Builds the form over the store: AddAssetWindow(root, conn).type_box.get() is "INVERTER"."""
        super().__init__(parent)
        self.title(TITLE)
        self.conn = conn
        self.on_saved = on_saved
        self.saved_id: str | None = None
        self.entries: dict[str, ttk.Entry] = {}
        row = self.add_entries(ENTRIES_BEFORE, 0)
        row = self.add_dropdowns(row)
        row = self.add_entries(ENTRIES_AFTER, row)
        self.add_buttons(row)
        self.message = ttk.Label(self, text="")
        self.message.grid(row=row + 1, column=0, columnspan=4, sticky="w")
        self.refresh_parents()

    def add_entries(self, fields: tuple[tuple[str, str], ...], row: int) -> int:
        """Lays out a Label and an Entry per field from a row, returning the next free row: the three first from 0
        return 3."""
        for key, label in fields:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w")
            self.entries[key] = ttk.Entry(self)
            self.entries[key].grid(row=row, column=1, columnspan=2, sticky="we")
            row += 1
        return row

    def add_dropdowns(self, row: int) -> int:
        """Lays out the type and parent dropdowns from a row, returning the next free row: from 3 it returns 5."""
        names = kind_names(project.kinds())
        ttk.Label(self, text=TYPE_LABEL).grid(row=row, column=0, sticky="w")
        self.type_box = ttk.Combobox(self, values=names, state="readonly")
        self.type_box.set(default_kind(names))
        self.type_box.grid(row=row, column=1, columnspan=2, sticky="we")
        ttk.Label(self, text=PARENT_LABEL).grid(row=row + 1, column=0, sticky="w")
        self.parent_box = ttk.Combobox(self, state="readonly")
        self.parent_box.grid(row=row + 1, column=1, sticky="we")
        ttk.Button(self, text=REFRESH, command=self.refresh_parents).grid(row=row + 1, column=2)
        self.entries["site"].bind("<FocusOut>", lambda event: self.refresh_parents())
        return row + 2

    def add_buttons(self, row: int) -> None:
        """Lays out Save, Cancel and Ping on a row, Ping disabled until a Save succeeds."""
        self.save_button = ttk.Button(self, text=SAVE, command=self.save)
        self.save_button.grid(row=row, column=0)
        self.cancel_button = ttk.Button(self, text=CANCEL, command=self.destroy)
        self.cancel_button.grid(row=row, column=1)
        self.ping_button = ttk.Button(self, text=PING, command=self.ping, state="disabled")
        self.ping_button.grid(row=row, column=2)

    def refresh_parents(self) -> None:
        """Fills the parent dropdown with the site's assets from project.asset_rows, "<none>" first and chosen."""
        ids = tuple(row.asset_id for row in project.asset_rows(self.conn))
        self.parent_box.configure(values=parent_choices(ids, self.entries["site"].get()))
        self.parent_box.set(NO_PARENT)

    def values(self) -> dict[str, str]:
        """The form's text by key: after typing "OAHE" in Site, values()["site"] is "OAHE"."""
        found = {key: entry.get() for key, entry in self.entries.items()}
        found["type"] = self.type_box.get()
        found["parent"] = self.parent_box.get()
        return found

    def say(self, text: str, succeeded: bool) -> None:
        """Shows a line in the message Label, green when succeeded, red when a refusal: say("Saved X", True)."""
        self.message.configure(text=text, foreground=message_colour(succeeded))

    def save(self) -> None:
        """Registers the form's asset through project; a refusal is shown verbatim and the window stays open."""
        try:
            asset = asset_from_form(self.values())
            project.register_asset(self.conn, asset)
        except ValueError as refusal:  # RegistryError, MalformedAssetId and the leaf's refusals are ValueErrors
            self.say(str(refusal), False)
            return
        self.saved_id = asset.asset_id
        self.say(SAVED.format(asset_id=asset.asset_id), True)
        self.save_button.configure(text=SAVED_BUTTON, state="disabled")
        self.ping_button.configure(state="normal")
        self.on_saved(asset.asset_id)

    def ping(self) -> None:
        """Reads the saved asset's feed once through project, showing the summary or the FeedError's message."""
        if self.saved_id is None:
            return
        try:
            samples = project.ping_asset(self.conn, self.saved_id)
        except (project.FeedError, project.UnknownAsset) as refusal:
            self.say(str(refusal), False)
            return
        self.say(ping_summary(samples), True)
