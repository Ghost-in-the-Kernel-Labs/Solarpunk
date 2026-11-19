"""The fleet list's sort and filter (9.4, SP-023): worst first, a column's sort, and the rows a search, a status and a
kind keep, headless; then the window: the filter row, Esc, a heading's click, F5, and the selection moved by Up and
Down and opened by Enter. The store is the OAHE fleet with an outage on OAHE-INV-002 and a pushed SEN-001 on
OAHE-SEN-001. Skips "no tkinter" or "no display" as test_ui.py does."""
import importlib.util
import sqlite3
import unittest

from solarpunk import project
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.ui import order

HAS_TKINTER = importlib.util.find_spec("tkinter") is not None
if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import app

ENGINEER = "site@oahe.example"
INV1, INV2, SEN = "OAHE-INV-001", "OAHE-INV-002", "OAHE-SEN-001"


def display_available() -> bool:
    """Whether a Tk window can open here: False with no tkinter or no DISPLAY."""
    if not HAS_TKINTER:
        return False
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        return False
    return True


def store() -> sqlite3.Connection:
    """The OAHE fleet, OAHE-INV-002 red with an INV-001, OAHE-SEN-001 yellow with a pushed SEN-001, the rest green."""
    conn = project.open_store()
    project.load_fleet(conn, project.demo_fleet())
    project.assign_fault(conn, INV2, "INV-001", at(2026, 6, 1, 11, 30), ENGINEER)
    project.suggest_pushed(conn, SEN, "SEN-001", at(2026, 6, 1, 12))
    return conn


class Click:
    """A stand-in for a click event, holding only the x and y the window reads."""

    def __init__(self, x: int, y: int) -> None:
        """Click(45, 10) is a click on the first heading."""
        self.x = x
        self.y = y


class TheOrder(unittest.TestCase):
    def setUp(self) -> None:
        """The three-colour store's rows, in id order."""
        conn = store()
        self.addCleanup(conn.close)
        self.rows = project.asset_rows(conn)

    def test_worst_first_is_red_then_yellow_then_green_ties_by_id(self) -> None:
        ordered = order.worst_first(self.rows)
        self.assertEqual([r.asset_id for r in ordered[:3]], [INV2, SEN, INV1])
        greens = [r.asset_id for r in ordered[2:]]
        self.assertEqual(greens, sorted(greens))

    def test_a_column_sorts_by_its_words_and_status_sorts_worst_first(self) -> None:
        self.assertEqual(order.sorted_by(self.rows, 0), self.rows)
        self.assertEqual(order.sorted_by(self.rows, 3), order.worst_first(self.rows))
        by_kind = [r.kind.name.lower() for r in order.sorted_by(self.rows, 2)]
        self.assertEqual(by_kind, sorted(by_kind))
        self.assertEqual(order.sorted_by(self.rows, 0, reverse=True), tuple(reversed(self.rows)))

    def test_matching_keeps_the_search_the_status_and_the_kind(self) -> None:
        self.assertEqual(order.matching(self.rows, "", None, None), self.rows)
        self.assertEqual([r.asset_id for r in order.matching(self.rows, "  tracker ", None, None)],
                         ["OAHE-TRK-001", "OAHE-TRK-002"])
        self.assertEqual([r.asset_id for r in order.matching(self.rows, "inv-001", None, None)], [INV1, INV2])
        self.assertEqual([r.asset_id for r in order.matching(self.rows, "", AssetStatus.RED, None)], [INV2])
        self.assertEqual([r.asset_id for r in order.matching(self.rows, "inv", None, AssetKind.INVERTER)], [INV1, INV2])
        self.assertEqual(order.matching(self.rows, "nothing like it", None, None), ())


@unittest.skipUnless(display_available(), "no display")
class TheWindow(unittest.TestCase):
    def setUp(self) -> None:
        """The three-colour store's fleet window in a hidden root."""
        self.conn = store()
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = app.FleetWindow(self.root, self.conn)
        self.root.update()

    def shown(self) -> list[str]:
        """The ids the list holds now, in its order."""
        return [row.asset_id for row in self.window.rows]

    def test_the_search_and_the_boxes_narrow_and_esc_clears(self) -> None:
        self.window.search_text.set("tracker")
        self.assertEqual(self.shown(), ["OAHE-TRK-001", "OAHE-TRK-002"])
        self.assertTrue(str(self.window.status_line.cget("text")).endswith("; 2 of 11 shown"))
        self.window.search_text.set("")
        self.window.status_choice.set("yellow")
        self.assertEqual(self.shown(), [SEN])
        self.window.status_choice.set(app.ANY_STATUS)
        self.window.kind_choice.set("inverter")
        self.assertEqual(self.shown(), [INV1, INV2])
        self.window.band_buttons["outages"].invoke()
        self.assertEqual(self.shown(), [INV2])
        self.window.clear_filters()
        self.assertEqual(len(self.shown()), 11)
        self.assertEqual((self.window.kind_choice.get(), self.window.filter_key), (app.ANY_KIND, None))

    def test_a_heading_click_sorts_and_a_second_turns_it_round(self) -> None:
        status_x = self.window.xs[3] + 2
        self.window.on_heading(Click(status_x, 10))
        self.assertEqual(self.shown()[:2], [INV2, SEN])
        heading = self.window.header.itemcget(self.window.header.find_withtag(app.HEADING_TAG)[3], "text")
        self.assertEqual(heading, "Status ▲")
        marked = self.window.header.find_withtag(app.HEADING_TAG)[3]
        self.assertLess(self.window.header.bbox(marked)[2], self.window.xs[4])  # the mark never runs into Cause
        self.window.on_heading(Click(status_x, 10))
        self.assertEqual(self.shown()[-2:], [SEN, INV2])
        self.window.on_heading(Click(self.window.xs[0] + 2, 10))
        self.assertEqual(self.shown(), sorted(self.shown()))

    def test_up_and_down_select_and_enter_opens(self) -> None:
        self.window.open_selected()
        self.assertEqual(self.window.opened, [])
        self.window.move_selection(1)
        self.window.move_selection(1)
        self.window.move_selection(-1)
        self.assertEqual(self.window.selected, INV1)
        self.assertEqual(len(self.window.canvas.find_withtag(app.SELECTED_TAG)), 1)
        self.window.move_selection(-1)
        self.assertEqual(self.window.selected, INV1)
        self.window.open_selected()
        self.assertEqual(self.window.opened, [INV1])

    def test_the_keys_are_bound_on_the_fleets_window(self) -> None:
        for key in ("<Control-f>", "<Escape>", "<F5>", "<Up>", "<Down>", "<Return>"):
            with self.subTest(key=key):
                self.assertTrue(self.root.bind(key))

    def test_f5s_refresh_reads_what_changed(self) -> None:
        project.assign_fault(self.conn, INV1, "INV-001", at(2026, 6, 1, 14), ENGINEER)
        self.window.refresh()
        self.window.status_choice.set("red")
        self.assertEqual(self.shown(), [INV1, INV2])


if __name__ == "__main__":
    unittest.main()
