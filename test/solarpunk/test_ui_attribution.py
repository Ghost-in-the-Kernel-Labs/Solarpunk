"""The asset window signed in (12.4, SP-015): an engineer sees no engineer picker and assigns as themself, an operator
picks the engineer "On the word of" from the site's engineer accounts and the fault records both, and the ticket panel
has no "By" box, its comment the account's own. Over test_attribution's store with accounts; skips "no tkinter" or
"no display" as test_ui.py does."""
import unittest

from solarpunk import project
from test.solarpunk.test_attribution import ENGINEER, OPERATOR, OPS, SITE, stored
from test.solarpunk.test_ui_suggestions import HAS_TKINTER, display_available

if HAS_TKINTER:
    import tkinter

    from solarpunk.ui import asset_window

ASSET = "OAHE-INV-001"


@unittest.skipUnless(display_available(), "no display")
class SignedIn(unittest.TestCase):
    def setUp(self) -> None:
        """The store with accounts in memory and a hidden root."""
        self.conn = stored(project.open_store())
        self.addCleanup(self.conn.close)
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def window(self, account: project.Account) -> "asset_window.AssetWindow":
        """OAHE-INV-001's window as the account, the first code chosen."""
        window = asset_window.AssetWindow(self.root, self.conn, ASSET, account=account)
        self.root.update()
        window.code_box.current(0)
        return window

    def test_an_engineer_sees_no_picker_and_assigns_as_themself(self) -> None:
        window = self.window(ENGINEER)
        self.assertIsNone(window.assigned_by_box)
        self.assertIsNone(window.ticket_panel.by_box)
        window.assign_button.invoke()
        fault = project.faults_listing(self.conn, False)[0]
        self.assertEqual((fault.assigned_by, fault.recorded_by, str(window.message.cget("text"))), (SITE, None, ""))

    def test_an_operator_names_the_engineer_on_whose_word_it_is(self) -> None:
        window = self.window(OPERATOR)
        window.assign_button.invoke()
        self.assertEqual(str(window.message.cget("text")), asset_window.CHOOSE_WORD)
        self.assertEqual(tuple(window.assigned_by_box.cget("values")), (SITE,))
        self.assertIsNone(window.entered_by_box)
        window.assigned_by_box.set(SITE)
        window.assign_button.invoke()
        fault = project.faults_listing(self.conn, False)[0]
        self.assertEqual((fault.assigned_by, fault.recorded_by), (SITE, OPS))
        window.ticket_panel.comment_box.insert(0, "on my way")
        window.ticket_panel.comment_button.invoke()
        self.assertEqual(project.ticket_comments(self.conn, 1)[0].author, OPS)
