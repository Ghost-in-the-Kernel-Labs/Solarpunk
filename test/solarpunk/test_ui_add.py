"""The add-asset window (3.3): the form's text becomes a leaf Asset or the leaf's refusal, Ping's summary reads in
words, and, under a display, Save registers through project, a refusal is shown and the window stays open, Ping reads
the saved asset's feed or shows the FeedError, Cancel registers nothing. The widget tests skip with "no display"."""
import socket
import sqlite3
import threading
import unittest
from datetime import timedelta

try:  # a Python built without Tk (the fast loop's python3 here) has no tkinter: the window cannot be imported at all
    import tkinter
except ModuleNotFoundError as missing:
    raise unittest.SkipTest("no tkinter") from missing

from solarpunk import project
from solarpunk.feed import simulate
from solarpunk.leaf.asset_types import kinds
from solarpunk.leaf.assets import Asset, MalformedAssetId
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.leaf.telemetry import Sample, gap
from solarpunk.ui import add_asset
from solarpunk.ui.add_asset import (
    AddAssetWindow,
    asset_from_form,
    default_kind,
    first_record,
    kind_named,
    kind_names,
    message_colour,
    parent_choices,
    ping_summary,
    port_of,
    rated_of,
    site_of,
)

LOCAL = "127.0.0.1"
NOON = at(2026, 6, 1, 12)
SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD")
INVERTER_FORM = {
    "id": " OAHE-INV-009 ", "name": " Inverter 9 ", "site": " OAHE ", "parent": "OAHE-SIT-001", "type": "INVERTER",
    "rated_kw": " 100 ", "location": " Pad C ", "email": " a@b.org ", "host": " 10.0.0.9 ", "port": " 5020 ",
}
SITE_FORM = {
    "id": "FALL-SIT-001", "name": "Fall", "site": "FALL", "parent": "<none>", "type": "SITE",
    "rated_kw": "", "location": " ", "email": "", "host": "", "port": "",
}


def display_available() -> bool:
    """True when tkinter can open a root window: under xvfb-run True, in a session with no DISPLAY False."""
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        return False
    root.destroy()
    return True


def form(key: str, text: str) -> dict[str, str]:
    """The inverter form with one key changed: form("port", "x")["port"] is "x"."""
    return {**INVERTER_FORM, key: text}


def reading(minutes: int) -> Sample:
    """A reading of OAHE-INV-009 some minutes after noon: reading(5).at is 12:05 UTC."""
    return Sample("OAHE-INV-009", NOON + timedelta(minutes=minutes), 812.0, 78.4, False)


def free_port() -> int:
    """A port nothing listens on: bound once to 0 and released, so a connection to it is refused."""
    with socket.socket() as probe:
        probe.bind((LOCAL, 0))
        return probe.getsockname()[1]


class TheForm(unittest.TestCase):
    def test_a_full_inverter_is_trimmed_into_the_leafs_asset(self) -> None:
        expected = Asset("OAHE-INV-009", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 9", 100.0,
                         "10.0.0.9", 5020, "Pad C", "a@b.org")
        self.assertEqual(asset_from_form(INVERTER_FORM), expected)

    def test_a_site_with_nothing_optional_has_nones(self) -> None:
        self.assertEqual(asset_from_form(SITE_FORM), Asset("FALL-SIT-001", AssetKind.SITE, "FALL", None, "Fall", None))

    def test_a_blank_parent_is_none_too(self) -> None:
        self.assertIsNone(asset_from_form(form("parent", "  ")).parent_id)

    def test_a_port_that_is_not_whole_is_refused(self) -> None:
        for text in ("50.5", "x", "-1", "5 020"):
            with self.assertRaisesRegex(ValueError, "^port must be a whole number$"):
                asset_from_form(form("port", text))

    def test_the_leafs_refusals_come_through(self) -> None:
        with self.assertRaisesRegex(ValueError, "^OAHE-INV-009: host and port come together$"):
            asset_from_form(form("host", ""))
        with self.assertRaisesRegex(ValueError, "^OAHE-INV-009: port 0 is not 1 to 65535$"):
            asset_from_form(form("port", "0"))
        with self.assertRaisesRegex(ValueError, "^OAHE-INV-009: 'nobody' is not an email address$"):
            asset_from_form(form("email", "nobody"))

    def test_a_rated_kw_that_is_not_a_number_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "^rated kW must be a number$"):
            asset_from_form(form("rated_kw", "lots"))
        self.assertEqual(rated_of("2.5"), 2.5)
        self.assertIsNone(rated_of("  "))

    def test_a_port_is_a_whole_number_or_none(self) -> None:
        self.assertEqual(port_of(" 65535 "), 65535)
        self.assertIsNone(port_of(""))

    def test_an_unknown_type_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "^'PANEL' is not an asset type$"):
            kind_named("PANEL")
        self.assertIs(kind_named("TRACKER"), AssetKind.TRACKER)

    def test_a_bad_id_shape_is_the_registrys_refusal_after_the_form(self) -> None:
        asset = asset_from_form(form("id", "OAHE-INV-9"))
        conn = project.open_store()
        self.addCleanup(conn.close)
        with self.assertRaisesRegex(MalformedAssetId, "is not of the shape SITE-KIND-nnn"):
            project.register_asset(conn, asset)


class TheDropdowns(unittest.TestCase):
    def test_the_type_names_follow_the_lists_order(self) -> None:
        self.assertEqual(kind_names((AssetKind.SITE, AssetKind.INVERTER)), ("SITE", "INVERTER"))
        self.assertEqual(kind_names(kinds()), tuple(kind.name for kind in kinds()))

    def test_the_type_opens_on_inverter_or_the_first(self) -> None:
        self.assertEqual(default_kind(("SITE", "INVERTER")), "INVERTER")
        self.assertEqual(default_kind(("SITE", "METER")), "SITE")

    def test_the_parents_are_the_sites_assets_after_none(self) -> None:
        ids = ("FALL-SIT-001", "OAHE-INV-001", "OAHE-SIT-001")
        self.assertEqual(parent_choices(ids, " OAHE "), ("<none>", "OAHE-INV-001", "OAHE-SIT-001"))
        self.assertEqual(parent_choices(ids, ""), ("<none>",) + ids)
        self.assertEqual(parent_choices(ids, "NONE"), ("<none>",))

    def test_the_site_of_an_id(self) -> None:
        self.assertEqual(site_of("OAHE-INV-001"), "OAHE")
        self.assertIsNone(site_of("x"))


class ThePingSummary(unittest.TestCase):
    def test_none_one_and_many(self) -> None:
        first = "2026-06-01T12:00:00+00:00, irradiance 812.0 W/m2, power 78.4 kW"
        self.assertEqual(ping_summary(()), "Ping: no records")
        self.assertEqual(ping_summary((reading(0),)), f"Ping: 1 record, first at {first}")
        self.assertEqual(ping_summary((reading(0), reading(5), reading(10))), f"Ping: 3 records, first at {first}")

    def test_a_gap_reads_as_a_gap(self) -> None:
        self.assertEqual(first_record(gap("OAHE-INV-009", NOON)), "2026-06-01T12:00:00+00:00, a gap")

    def test_the_message_colours(self) -> None:
        self.assertEqual(message_colour(True), "#1b5e20")
        self.assertEqual(message_colour(False), "#b00020")
        self.assertEqual(add_asset.TITLE, "Add an asset")


@unittest.skipUnless(display_available(), "no display")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """A hidden root, a store holding the OAHE site, and the window over it; all closed when a test ends."""
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.conn: sqlite3.Connection = project.open_store()
        self.addCleanup(self.conn.close)
        project.register_asset(self.conn, SITE)
        self.saved: list[str] = []
        self.window = AddAssetWindow(self.root, self.conn, self.saved.append)
        self.root.update()

    def fill(self, values: dict[str, str]) -> None:
        """Types the values into the window's entries and dropdowns: fill(INVERTER_FORM) fills every field."""
        for key, entry in self.window.entries.items():
            entry.delete(0, "end")
            entry.insert(0, values[key])
        self.window.refresh_parents()
        self.window.type_box.set(values["type"])
        self.window.parent_box.set(values["parent"])
        self.root.update()

    def message(self) -> str:
        """The message Label's text: "" before any button is pressed."""
        return str(self.window.message.cget("text"))

    def test_it_opens_on_inverter_with_the_lists_types_and_the_sites_parents(self) -> None:
        self.assertEqual(self.window.title(), "Add an asset")
        self.assertEqual(tuple(self.window.type_box.cget("values")), tuple(k.name for k in project.kinds()))
        self.assertEqual(self.window.type_box.get(), "INVERTER")
        self.assertEqual(tuple(self.window.parent_box.cget("values")), ("<none>", "OAHE-SIT-001"))
        self.assertEqual(self.window.parent_box.get(), "<none>")
        self.assertEqual(str(self.window.ping_button.cget("state")), "disabled")
        self.assertEqual(self.window.save_button.cget("text"), "Save")
        self.assertEqual(self.window.cancel_button.cget("text"), "Cancel")

    def test_save_registers_through_project_and_enables_ping(self) -> None:
        self.fill(INVERTER_FORM)
        self.window.save_button.invoke()
        self.root.update()
        self.assertEqual(project.asset_detail(self.conn, "OAHE-INV-009").asset, asset_from_form(INVERTER_FORM))
        self.assertEqual(self.message(), "Saved OAHE-INV-009")
        self.assertEqual(self.saved, ["OAHE-INV-009"])
        self.assertEqual(str(self.window.save_button.cget("state")), "disabled")
        self.assertEqual(self.window.save_button.cget("text"), "Saved")
        self.assertEqual(str(self.window.ping_button.cget("state")), "normal")

    def test_a_duplicate_shows_the_registrys_refusal_and_stays_open(self) -> None:
        self.fill({**SITE_FORM, "id": "OAHE-SIT-001", "site": "OAHE", "name": "Oahe"})
        self.window.save_button.invoke()
        self.root.update()
        self.assertEqual(self.message(), "OAHE-SIT-001 is already registered")
        self.assertEqual(str(self.window.message.cget("foreground")), "#b00020")
        self.assertTrue(self.window.winfo_exists())
        self.assertEqual(self.saved, [])
        self.assertEqual(str(self.window.ping_button.cget("state")), "disabled")

    def test_a_form_refusal_is_shown_too(self) -> None:
        self.fill(form("port", "x"))
        self.window.save_button.invoke()
        self.assertEqual(self.message(), "port must be a whole number")
        self.assertEqual(len(project.asset_rows(self.conn)), 1)

    def test_ping_reads_the_saved_assets_feed(self) -> None:
        fed = (reading(0), reading(5))
        server = simulate.make_server(fed, LOCAL, 0)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.fill({**INVERTER_FORM, "host": LOCAL, "port": str(server.server_address[1])})
        self.window.ping_button.invoke()
        self.assertEqual(self.message(), "")
        self.window.save_button.invoke()
        self.window.ping_button.invoke()
        self.root.update()
        self.assertEqual(self.message(), ping_summary(fed))
        self.assertEqual(str(self.window.message.cget("foreground")), "#1b5e20")

    def test_ping_against_a_dead_port_shows_the_feed_error(self) -> None:
        port = free_port()
        self.fill({**INVERTER_FORM, "host": LOCAL, "port": str(port)})
        self.window.save_button.invoke()
        self.window.ping_button.invoke()
        self.root.update()
        self.assertEqual(self.message(), f"{LOCAL}:{port} is unreachable")
        self.assertEqual(str(self.window.message.cget("foreground")), "#b00020")

    def test_the_site_losing_focus_refreshes_the_parents(self) -> None:
        project.register_asset(self.conn, Asset("FALL-SIT-001", AssetKind.SITE, "FALL", None, "Fall", None))
        self.window.entries["site"].insert(0, "FALL")
        self.window.entries["site"].event_generate("<FocusOut>")
        self.root.update()
        self.assertEqual(tuple(self.window.parent_box.cget("values")), ("<none>", "FALL-SIT-001"))

    def test_cancel_closes_and_registers_nothing(self) -> None:
        self.fill(INVERTER_FORM)
        self.window.cancel_button.invoke()
        self.root.update()
        self.assertFalse(self.window.winfo_exists())
        self.assertEqual([row.asset_id for row in project.asset_rows(self.conn)], ["OAHE-SIT-001"])
        self.assertEqual(self.saved, [])
