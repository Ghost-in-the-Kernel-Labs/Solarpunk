"""The asset registry holds its door (SOL-05): every leaf Asset field round-trips, lists come back in id order, and a
malformed id, a kind or site disagreeing with the id, a missing or foreign-site parent and a duplicate are refused."""
import sqlite3
import unittest

from solarpunk.fleet import registry
from solarpunk.fleet.registry import RegistryError
from solarpunk.leaf import store
from solarpunk.leaf.assets import Asset, MalformedAssetId
from solarpunk.leaf.codes import AssetKind

SITE_EMAIL = "site@oahe.example"
INVERTER_EMAIL = "inverter@oahe.example"

# The OAHE example fleet (ROADMAP 1.1): the site and the ten assets at it, eleven rows; other lanes' tests may copy it,
# never import it (MOD-05).
OAHE: tuple[Asset, ...] = (
    Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None, location="Pierre, SD",
          engineer_email=SITE_EMAIL),
    Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 1", 100.0, "10.0.0.1", 5020,
          "Pad A", INVERTER_EMAIL),
    Asset("OAHE-INV-002", AssetKind.INVERTER, "OAHE", "OAHE-SIT-001", "Inverter 2", 100.0, "10.0.0.2", 5020, "Pad B"),
    Asset("OAHE-STR-001", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 1", 50.0),
    Asset("OAHE-STR-002", AssetKind.STRING, "OAHE", "OAHE-INV-001", "String 2", 50.0),
    Asset("OAHE-STR-003", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 3", 50.0),
    Asset("OAHE-STR-004", AssetKind.STRING, "OAHE", "OAHE-INV-002", "String 4", 50.0),
    Asset("OAHE-TRK-001", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 1", None, "10.0.0.11", 502),
    Asset("OAHE-TRK-002", AssetKind.TRACKER, "OAHE", "OAHE-SIT-001", "Tracker 2", None, "10.0.0.12", 502),
    Asset("OAHE-MTR-001", AssetKind.METER, "OAHE", "OAHE-SIT-001", "Revenue meter", None, "10.0.0.21", 1),
    Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Irradiance sensor", None, "10.0.0.31", 65535),
)


def count(conn: sqlite3.Connection) -> int:
    """The number of stored assets: count of the loaded OAHE store is 11."""
    return conn.execute("SELECT count(*) FROM assets").fetchone()[0]


def ids(assets: tuple[Asset, ...]) -> list[str]:
    """The ids of some assets, in their order: ids(OAHE[:1]) is ["OAHE-SIT-001"]."""
    return [asset.asset_id for asset in assets]


class Registry(unittest.TestCase):
    """A test case whose stores close when it ends."""

    def empty(self) -> sqlite3.Connection:
        """An in-memory store holding the empty registry: self.empty().execute("SELECT count(*) FROM assets") gives 0."""
        conn = store.connect()
        self.addCleanup(conn.close)
        store.apply(conn, registry.schema())
        return conn

    def loaded(self) -> sqlite3.Connection:
        """An in-memory store holding the OAHE fleet: registry.get(self.loaded(), "OAHE-MTR-001") is the meter."""
        conn = self.empty()
        registry.load_fleet(conn, OAHE)
        return conn


class TheFixture(unittest.TestCase):
    def test_it_is_one_site_and_ten_assets_at_it(self) -> None:
        self.assertEqual(len(OAHE), 11)
        self.assertEqual(len(set(ids(OAHE))), 11)
        self.assertEqual(len([a for a in OAHE if a.kind is not AssetKind.SITE]), 10)
        self.assertEqual({asset.site for asset in OAHE}, {"OAHE"})


class TheTable(Registry):
    def test_the_schema_is_one_table_with_every_field_of_the_asset(self) -> None:
        conn = self.empty()
        names = [row[1] for row in conn.execute("PRAGMA table_info(assets)")]
        self.assertEqual(names, ["asset_id", "kind", "site", "parent_id", "name", "rated_kw", "host", "port",
                                 "location", "engineer_email"])
        self.assertEqual(count(conn), 0)

    def test_the_parent_references_assets(self) -> None:
        conn = self.empty()
        keys = [tuple(row)[2:5] for row in conn.execute("PRAGMA foreign_key_list(assets)")]
        self.assertEqual(keys, [("assets", "parent_id", "asset_id")])
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO assets (asset_id, kind, site, parent_id, name) VALUES ('A', 'SIT', 'S', 'B', 'n')")

    def test_every_asset_round_trips_as_the_leaf_asset(self) -> None:
        conn = self.loaded()
        self.assertEqual(count(conn), 11)
        for asset in OAHE:
            self.assertEqual(registry.get(conn, asset.asset_id), asset)

    def test_the_store_hands_back_rows_by_name_too(self) -> None:
        row = self.loaded().execute("SELECT asset_id, rated_kw FROM assets WHERE kind = 'INV' ORDER BY asset_id").fetchone()
        self.assertEqual((row["asset_id"], row["rated_kw"]), ("OAHE-INV-001", 100.0))

    def test_get_of_an_unregistered_id_is_none(self) -> None:
        self.assertIsNone(registry.get(self.loaded(), "OAHE-INV-999"))


class TheLists(Registry):
    def setUp(self) -> None:
        """The OAHE fleet registered out of id order (OAHE-INV-002 before OAHE-INV-001), so the lists' order is
        theirs, not the insertion's: by_kind(self.conn, AssetKind.INVERTER) still starts with OAHE-INV-001."""
        self.conn = self.empty()
        order = (0, 2, 1, 6, 5, 4, 3, 8, 7, 10, 9)
        registry.load_fleet(self.conn, tuple(OAHE[i] for i in order))

    def test_by_site_is_the_whole_site_in_id_order(self) -> None:
        self.assertEqual(ids(registry.by_site(self.conn, "OAHE")), sorted(ids(OAHE)))
        self.assertEqual(registry.by_site(self.conn, "BIGS"), ())

    def test_by_kind_is_one_kind_in_id_order(self) -> None:
        self.assertEqual(ids(registry.by_kind(self.conn, AssetKind.STRING)),
                         ["OAHE-STR-001", "OAHE-STR-002", "OAHE-STR-003", "OAHE-STR-004"])
        self.assertEqual(ids(registry.by_kind(self.conn, AssetKind.TRACKER)), ["OAHE-TRK-001", "OAHE-TRK-002"])
        self.assertEqual(registry.by_kind(self.conn, AssetKind.SITE), (OAHE[0],))

    def test_children_are_the_direct_children_in_id_order(self) -> None:
        self.assertEqual(ids(registry.children(self.conn, "OAHE-INV-002")), ["OAHE-STR-003", "OAHE-STR-004"])
        self.assertEqual(ids(registry.children(self.conn, "OAHE-SIT-001")),
                         ["OAHE-INV-001", "OAHE-INV-002", "OAHE-MTR-001", "OAHE-TRK-001", "OAHE-TRK-002"])
        self.assertEqual(registry.children(self.conn, "OAHE-STR-001"), ())


class TheRefusals(Registry):
    def refused(self, conn: sqlite3.Connection, asset: Asset, message: str) -> None:
        """Asserts register refuses the asset with this message and stores nothing: refused(c, dup, "… registered")."""
        before = count(conn)
        with self.assertRaises(RegistryError) as raised:
            registry.register(conn, asset)
        self.assertEqual(str(raised.exception), message)
        self.assertEqual(count(conn), before)

    def test_a_malformed_id_is_refused_by_the_leaf_and_never_stored(self) -> None:
        conn = self.loaded()
        for bad in ("OAHE-INV-3", "oahe-INV-003", "OAHE-XYZ-003", "OAHE-INV-0003", ""):
            with self.assertRaises(MalformedAssetId, msg=bad):
                registry.register(conn, Asset(bad, AssetKind.INVERTER, "OAHE", None, "bad", None))
        self.assertEqual(count(conn), 11)

    def test_a_kind_disagreeing_with_the_id_is_refused(self) -> None:
        asset = Asset("OAHE-INV-003", AssetKind.STRING, "OAHE", None, "Inverter 3", 100.0)
        self.refused(self.loaded(), asset, "OAHE-INV-003: kind STR disagrees with the id's INV")

    def test_a_site_disagreeing_with_the_id_is_refused(self) -> None:
        asset = Asset("OAHE-INV-003", AssetKind.INVERTER, "BIGS", None, "Inverter 3", 100.0)
        self.refused(self.loaded(), asset, "OAHE-INV-003: site BIGS disagrees with the id's OAHE")

    def test_a_missing_parent_is_refused(self) -> None:
        asset = Asset("OAHE-STR-005", AssetKind.STRING, "OAHE", "OAHE-INV-003", "String 5", 50.0)
        self.refused(self.loaded(), asset, "OAHE-STR-005: parent OAHE-INV-003 is not registered")

    def test_a_parent_at_another_site_is_refused(self) -> None:
        conn = self.loaded()
        registry.register(conn, Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", None, "Big Stone 1", 100.0))
        asset = Asset("OAHE-STR-005", AssetKind.STRING, "OAHE", "BIGS-INV-001", "String 5", 50.0)
        self.refused(conn, asset, "OAHE-STR-005: parent BIGS-INV-001 is at site BIGS, not OAHE")

    def test_a_duplicate_is_refused_and_the_first_kept(self) -> None:
        conn = self.loaded()
        twin = Asset("OAHE-INV-001", AssetKind.INVERTER, "OAHE", None, "Twin", 1.0)
        self.refused(conn, twin, "OAHE-INV-001 is already registered")
        self.assertEqual(registry.get(conn, "OAHE-INV-001"), OAHE[1])

    def test_load_fleet_stops_at_the_first_refusal_keeping_those_before(self) -> None:
        conn = self.empty()
        orphan = Asset("OAHE-STR-009", AssetKind.STRING, "OAHE", "OAHE-INV-009", "Orphan", 1.0)
        with self.assertRaises(RegistryError):
            registry.load_fleet(conn, OAHE[:2] + (orphan,) + OAHE[2:])
        self.assertEqual(ids(registry.by_site(conn, "OAHE")), ["OAHE-INV-001", "OAHE-SIT-001"])

    def test_a_child_before_its_parent_is_refused(self) -> None:
        with self.assertRaises(RegistryError):
            registry.load_fleet(self.empty(), (OAHE[3], OAHE[1], OAHE[0]))


class TheEngineers(Registry):
    def test_the_chain_is_asset_then_parent_then_site_skipping_none(self) -> None:
        conn = self.loaded()
        self.assertEqual(registry.engineers_for(conn, "OAHE-STR-001"), (INVERTER_EMAIL, SITE_EMAIL))
        self.assertEqual(registry.engineers_for(conn, "OAHE-INV-001"), (INVERTER_EMAIL, SITE_EMAIL))
        self.assertEqual(registry.engineers_for(conn, "OAHE-STR-003"), (SITE_EMAIL,))
        self.assertEqual(registry.engineers_for(conn, "OAHE-SEN-001"), (SITE_EMAIL,))
        self.assertEqual(registry.engineers_for(conn, "OAHE-SIT-001"), (SITE_EMAIL,))

    def test_an_email_appears_once_at_its_first_place(self) -> None:
        conn = self.loaded()
        registry.assign_engineer(conn, "OAHE-STR-002", SITE_EMAIL)
        self.assertEqual(registry.engineers_for(conn, "OAHE-STR-002"), (SITE_EMAIL, INVERTER_EMAIL))

    def test_an_unregistered_site_or_no_engineer_gives_what_there_is(self) -> None:
        conn = self.empty()
        registry.register(conn, Asset("BIGS-INV-001", AssetKind.INVERTER, "BIGS", None, "Big Stone 1", 100.0))
        self.assertEqual(registry.engineers_for(conn, "BIGS-INV-001"), ())
        registry.assign_engineer(conn, "BIGS-INV-001", "b@bigs.example")
        self.assertEqual(registry.engineers_for(conn, "BIGS-INV-001"), ("b@bigs.example",))

    def test_assign_engineer_sets_one_asset_only(self) -> None:
        conn = self.loaded()
        registry.assign_engineer(conn, "OAHE-INV-002", "b@oahe.example")
        self.assertEqual(registry.get(conn, "OAHE-INV-002").engineer_email, "b@oahe.example")
        self.assertEqual(registry.engineers_for(conn, "OAHE-STR-004"), ("b@oahe.example", SITE_EMAIL))
        self.assertEqual(registry.get(conn, "OAHE-INV-001").engineer_email, INVERTER_EMAIL)
        self.assertEqual(conn.execute("SELECT count(*) FROM assets WHERE engineer_email IS NULL").fetchone()[0], 8)

    def test_assign_engineer_refuses_a_bad_address_and_an_unknown_asset(self) -> None:
        conn = self.loaded()
        with self.assertRaises(ValueError) as bad:
            registry.assign_engineer(conn, "OAHE-INV-002", "not an address")
        self.assertEqual(str(bad.exception), "OAHE-INV-002: 'not an address' is not an email address")
        self.assertIsNone(registry.get(conn, "OAHE-INV-002").engineer_email)
        with self.assertRaises(RegistryError) as raised:
            registry.assign_engineer(conn, "OAHE-INV-999", "b@oahe.example")
        self.assertEqual(str(raised.exception), "OAHE-INV-999 is not registered")
        with self.assertRaises(RegistryError):
            registry.engineers_for(conn, "OAHE-INV-999")


class TheLeafAtTheDoor(Registry):
    """The leaf's own refusals the registry relies on, said exactly, so a reader of a refusal knows what was wrong."""

    def test_a_malformed_id_says_which_rule_it_broke(self) -> None:
        conn = self.empty()
        cases = (("OAHE-INV-3", "'OAHE-INV-3' is not of the shape SITE-KIND-nnn"),
                 ("OAHE-XYZ-003", "'OAHE-XYZ-003': XYZ is not an asset kind"))
        for bad, message in cases:
            with self.assertRaises(MalformedAssetId, msg=bad) as raised:
                registry.register(conn, Asset(bad, AssetKind.INVERTER, "OAHE", None, "bad", None))
            self.assertEqual(str(raised.exception), message)

    def test_an_asset_with_a_bad_endpoint_never_reaches_the_registry(self) -> None:
        cases = (("10.0.0.3", None, "OAHE-INV-003: host and port come together"),
                 ("10.0.0.3", 0, "OAHE-INV-003: port 0 is not 1 to 65535"),
                 ("10.0.0.3", 65536, "OAHE-INV-003: port 65536 is not 1 to 65535"))
        for host, port, message in cases:
            with self.assertRaises(ValueError, msg=message) as raised:
                Asset("OAHE-INV-003", AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0, host, port)
            self.assertEqual(str(raised.exception), message)
