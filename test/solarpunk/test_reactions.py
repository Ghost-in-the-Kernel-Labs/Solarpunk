"""Reactions (13.4, SP-020, SP-049): what a failing test does is declared from a closed set, checked at load, carried out by
the scheduled run and recorded. One test per action, each over a store of one inverter whose `reachable` result was stored
by hand, the held test a hand-made RemoteTest, and any suite a file in a scratch folder the registry is pointed at."""
import dataclasses
import gc
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from solarpunk import project
from solarpunk.faults import ledger
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.clock import at
from solarpunk.leaf.codes import AssetKind
from solarpunk.mailer import mail as mailer
from solarpunk.mailer.transport import MailError, Settings
from solarpunk.project import orchestrator
from solarpunk.project import reactions as carrying
from solarpunk.remote import reactions, registry, results, suite_registry
from solarpunk.remote.reactions import Fault, Mail, OpenPreventive, RunSuite
from solarpunk.remote.registry import BadRemoteTest, RemoteTest
from solarpunk.workorders import ledger as work_ledger

RUN_AT = at(2026, 6, 1, 12)
SITE = Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, engineer_email="site@oahe.example")
INVERTER = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0)
SETTINGS = Settings("127.0.0.1", 1, "ops@oahe.example", False, None, None)
SUITE = 'from solarpunk.leaf.codes import AssetKind\n\nTESTS = ("reachable",)\nKINDS = ()\nSITES = ()\nCADENCE = "hourly"\n'


def held(declared: tuple, name: str = "reachable") -> dict[str, RemoteTest]:
    """The held tests: a hand-made `reachable` whose INVERTER reactions are those declared."""
    real = registry.discover()[name]
    return {name: dataclasses.replace(real, reactions={AssetKind.INVERTER: declared})}


class Store(unittest.TestCase):
    """A store of the site and one inverter with a scratch suites folder; failing(at) stores a failed reachable."""

    def setUp(self) -> None:
        """self.conn holds the fleet and no result; self.folder is the empty suites folder the registry reads."""
        gc.collect()
        self.conn = project.open_store()
        self.addCleanup(self.conn.close)
        project.register_asset(self.conn, SITE)
        project.register_asset(self.conn, INVERTER)
        self.folder = Path(tempfile.mkdtemp(prefix="suites-"))
        for patched in (mock.patch.object(suite_registry, "folder", return_value=self.folder),
                        mock.patch.object(registry, "suites_folder", return_value=self.folder)):
            patched.start()
            self.addCleanup(patched.stop)

    def failing(self, run_at: datetime = RUN_AT, test: str = "reachable") -> None:
        """Stores one failed result of the test on the inverter at the instant."""
        results.record(self.conn, test, INVERTER.asset_id, run_at, results.Result(False, "no records"))

    def carry(self, tests: dict, run_at: datetime = RUN_AT, settings: Settings | None = None) -> int:
        """Carries out the reactions of the run at the instant over the inverter; returns the mails sent."""
        return carrying.carry_out(self.conn, (INVERTER,), {}, run_at, settings, None, tests)

    def rows(self) -> list[tuple[str, str]]:
        """The reactions table as (action, detail), oldest first."""
        return [(row.action, row.detail) for row in reactions.all_rows(self.conn)]


class TheSet(unittest.TestCase):
    def test_the_set_holds_four_names_and_none_commands_equipment(self) -> None:
        self.assertEqual([member.__name__ for member in reactions.REACTIONS_SET],
                         ["Fault", "Mail", "RunSuite", "OpenPreventive"])
        self.assertEqual(reactions.MAX_CHAIN, 3)

    def test_the_tests_in_the_folder_declare_their_faults_as_they_suggested_them(self) -> None:
        found = registry.discover()
        self.assertEqual(found["reachable"].fault_code(AssetKind.METER), "MTR-001")
        self.assertEqual(found["reachable"].fault_code(AssetKind.INVERTER), "SIT-004")
        self.assertEqual(found["irradiance_in_range"].fault_code(AssetKind.SENSOR), "SEN-001")
        self.assertEqual(found["on_grid"].reactions_for(AssetKind.INVERTER), (Fault("SIT-004"),))

    def test_text_is_the_name_and_its_arguments(self) -> None:
        self.assertEqual([reactions.text(item) for item in (Fault("SIT-004"), Mail(), RunSuite("deep"), OpenPreventive("x"))],
                         ["Fault(SIT-004)", "Mail()", "RunSuite(deep)", "OpenPreventive(x)"])


class TheLoadRefuses(unittest.TestCase):
    def module(self, declared: object) -> types.ModuleType:
        """A test module for INVERTER with the REACTIONS declared."""
        module = types.ModuleType("solarpunk.remote.tests.fake")
        module.KINDS, module.CLAUSES, module.REACTIONS = (AssetKind.INVERTER,), ("9001-9.1.1",), declared
        module.run = lambda asset, given: None
        return module

    def refused(self, declared: object, words: str) -> None:
        """Whether loading a module with these REACTIONS raises BadRemoteTest saying words."""
        with self.assertRaisesRegex(BadRemoteTest, words):
            registry.from_module("fake", self.module(declared))

    def test_an_action_outside_the_set(self) -> None:
        for item in ("Mail", 5, object()):
            self.refused({AssetKind.INVERTER: (item,)}, "none of Fault, Mail, RunSuite, OpenPreventive")
        self.refused({AssetKind.INVERTER: "Mail"}, "is not a tuple")

    def test_a_fault_the_catalogue_lacks_or_of_another_kind(self) -> None:
        self.refused({AssetKind.INVERTER: (Fault("ZZZ-999"),)}, "ZZZ-999, which is no INVERTER code")
        self.refused({AssetKind.INVERTER: (Fault("SEN-001"),)}, "SEN-001, which is no INVERTER code")
        registry.from_module("fake", self.module({AssetKind.INVERTER: (Fault("SIT-004"),)}))  # the generic is for any kind

    def test_more_than_one_fault_for_a_kind(self) -> None:
        self.refused({AssetKind.INVERTER: (Fault("INV-001"), Fault("SIT-004"))}, "more than one Fault for INVERTER")

    def test_a_kind_the_test_does_not_run_on(self) -> None:
        self.refused({AssetKind.METER: ()}, "keyed by kinds of its KINDS")

    def test_a_suite_the_folder_lacks(self) -> None:
        self.refused({AssetKind.INVERTER: (RunSuite("nowhere"),)}, "runs suite nowhere, which the folder does not hold")
        registry.from_module("fake", self.module({AssetKind.INVERTER: (RunSuite("all"),)}))  # `all` is always held

    def test_a_preventive_with_no_note(self) -> None:
        self.refused({AssetKind.INVERTER: (OpenPreventive(" "),)}, "needs a note")

    def test_a_chain_that_starts_itself_or_runs_too_deep(self) -> None:
        self.assertIsNone(reactions.chain_problem({"a": ("s",)}, {"s": ("b",)}))
        self.assertEqual(reactions.chain_problem({"a": ("s",)}, {"s": ("a",)}), "suite s starts itself (s -> s)")
        looped = reactions.chain_problem({"a": ("s",), "b": ("t",)}, {"s": ("b",), "t": ("a",)})
        self.assertIn("starts itself (s -> t -> s)", looped)
        deep = reactions.chain_problem({"a": ("s",), "b": ("t",), "c": ("u",), "d": ("v",)},
                                       {"s": ("b",), "t": ("c",), "u": ("d",), "v": ("e",)})
        self.assertEqual(deep, "a failure starts 4 suites in a row (s -> t -> u -> v), more than 3")
        three = reactions.chain_problem({"a": ("s",), "b": ("t",), "c": ("u",)}, {"s": ("b",), "t": ("c",), "u": ("d",)})
        self.assertIsNone(three)


class TheLoadChecksTheChain(Store):
    def test_a_suite_holding_the_test_that_starts_it_is_refused_in_the_folder(self) -> None:
        (self.folder / "probe.py").write_text(SUITE, encoding="utf-8")
        found = registry.discover()
        starting = dataclasses.replace(found["reachable"], reactions={AssetKind.INVERTER: (RunSuite("probe"),)})
        with self.assertRaisesRegex(BadRemoteTest, "suite probe starts itself"):
            registry.checked_chains({**found, "reachable": starting})
        registry.checked_chains(found)


class TheFaultReaction(Store):
    def test_a_failure_raises_its_fault_and_is_recorded(self) -> None:
        self.failing()
        self.carry(held((Fault("INV-001"),)))
        self.assertEqual(self.rows(), [("Fault", "INV-001 raised")])
        self.assertEqual([fault.code for fault in ledger.by_asset(self.conn, INVERTER.asset_id)], ["INV-001"])

    def test_a_kind_naming_none_raises_the_generic_one_and_no_data_and_a_pass_react_not_at_all(self) -> None:
        self.failing(test="reachable")
        results.record(self.conn, "on_grid", INVERTER.asset_id, RUN_AT, results.no_data("no records"))
        results.record(self.conn, "power_under_rated", INVERTER.asset_id, RUN_AT, results.Result(True, "fine"))
        self.carry(registry.discover())
        self.assertEqual(self.rows(), [("Fault", "SIT-004 raised")])


class TheMailReaction(Store):
    def test_the_first_failure_of_a_streak_mails_the_engineers_and_a_second_does_not(self) -> None:
        with mock.patch.object(carrying.transport, "send") as sent:
            self.failing()
            self.assertEqual(self.carry(held((Mail(),)), settings=SETTINGS), 1)
            later = RUN_AT + timedelta(hours=1)
            self.failing(later)
            self.assertEqual(self.carry(held((Mail(),)), later, SETTINGS), 0)
        self.assertEqual(sent.call_count, 1)
        mail = sent.call_args.args[0]
        self.assertEqual(mail.to, ("site@oahe.example",))
        self.assertIn("reachable", mail.subject)
        self.assertIn("no records", mail.body)
        self.assertEqual(len(mailer.sent_for(self.conn, INVERTER.asset_id)), 1)
        self.assertEqual([detail for action, detail in self.rows() if action == "Mail"],
                         ["mailed site@oahe.example", "skipped: the streak was mailed at its first failure"])

    def test_a_recovery_ends_the_streak_so_the_next_failure_mails_again(self) -> None:
        with mock.patch.object(carrying.transport, "send") as sent:
            self.failing()
            results.record(self.conn, "reachable", INVERTER.asset_id, RUN_AT + timedelta(hours=1), results.Result(True, "ok"))
            later = RUN_AT + timedelta(hours=2)
            self.failing(later)
            self.carry(held((Mail(),)), RUN_AT, SETTINGS)
            self.carry(held((Mail(),)), later, SETTINGS)
        self.assertEqual(sent.call_count, 2)

    def test_no_settings_or_a_mail_that_cannot_go_is_a_skipped_row_not_a_stop(self) -> None:
        self.failing()
        self.carry(held((Mail(),)))
        with mock.patch.object(carrying.transport, "send", side_effect=MailError("down")):
            self.carry(held((Mail(),)), settings=SETTINGS)
        self.assertEqual([detail for action, detail in self.rows() if action == "Mail"],
                         ["skipped: no mail settings", "skipped: down"])


class TheRunSuiteReaction(Store):
    def test_the_suite_runs_on_the_asset_at_once_with_its_results_under_its_name(self) -> None:
        (self.folder / "probe.py").write_text(SUITE, encoding="utf-8")
        self.failing(test="power_under_rated")  # the suite's own test, reachable, has no RunSuite here
        self.carry(held((RunSuite("probe"),), "power_under_rated"))
        stored = [found for found in results.results_of(self.conn, INVERTER.asset_id) if found.suite == "probe"]
        self.assertEqual([(found.test_name, found.failed) for found in stored], [("reachable", True)])
        self.assertIn(("RunSuite", "ran probe: 1 results"), self.rows())

    def test_its_own_failures_react_in_turn_down_to_the_chain_limit(self) -> None:
        (self.folder / "probe.py").write_text(SUITE, encoding="utf-8")
        self.failing()
        self.carry(held((RunSuite("probe"),)))  # probe's reachable failure starts probe again: held() bypasses the load check
        ran = [detail for action, detail in self.rows() if action == "RunSuite"]
        # The deepest reaction is recorded first, the one that started the chain last.
        self.assertEqual(ran, ["skipped: the chain is 3 suites deep"] + ["ran probe: 1 results"] * reactions.MAX_CHAIN)

    def test_a_suite_gone_since_the_load_is_a_skipped_row(self) -> None:
        self.failing()
        self.carry(held((RunSuite("gone"),)))
        self.assertIn(("RunSuite", "skipped: no suite gone"), self.rows())


class TheOpenPreventiveReaction(Store):
    def test_it_opens_one_preventive_order_and_not_a_second_while_it_is_open(self) -> None:
        self.failing()
        self.carry(held((OpenPreventive("grease the bearing"),)))
        later = RUN_AT + timedelta(hours=1)
        self.failing(later)
        self.carry(held((OpenPreventive("grease the bearing"),)), later)
        orders = [order for order in work_ledger.by_asset(self.conn, INVERTER.asset_id) if order.kind == "preventive"]
        self.assertEqual([(order.note, order.fault_id) for order in orders], [("grease the bearing", None)])
        self.assertEqual([detail for action, detail in self.rows() if action == "OpenPreventive"],
                         ["opened work order 1", "skipped: an open preventive order with this note is already on it"])

    def test_a_closed_order_does_not_hold_the_note(self) -> None:
        self.failing()
        self.carry(held((OpenPreventive("grease"),)))
        work_ledger.close(self.conn, 1, RUN_AT + timedelta(minutes=30))
        later = RUN_AT + timedelta(hours=1)
        self.failing(later)
        self.carry(held((OpenPreventive("grease"),)), later)
        self.assertEqual(len([o for o in work_ledger.by_asset(self.conn, INVERTER.asset_id)]), 2)


class TheTable(Store):
    def test_an_old_store_gains_the_reactions_table_and_a_reaction_is_never_changed(self) -> None:
        self.failing()
        self.carry(held((Fault("INV-001"),)))
        row = reactions.of_result(self.conn, 1)[0]
        self.assertEqual((row.result_id, row.action, row.at), (1, "Fault", RUN_AT.isoformat()))
        self.assertEqual(reactions.all_rows(self.conn), (row,))
        self.assertIn(("reactions", reactions.schema()), orchestrator.LATER_TABLES)


if __name__ == "__main__":
    unittest.main()
