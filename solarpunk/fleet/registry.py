"""The asset registry: the assets table holding every field of the leaf's Asset, the refusals at its door (Invariant:
SOL-05) and the lists by site, kind and parent, each in id order. Rows come back as leaf Assets, never as rows."""
import dataclasses
import sqlite3

from solarpunk.leaf.assets import Asset, parse_asset_id, site_id
from solarpunk.leaf import versions
from solarpunk.leaf.codes import AssetKind

# The SQL lives here, at module level, where mutmut does not reach: SQLite reads keywords and names in any case, so a
# mutant that only changes their case could not be told apart from the original (docs/MUTATION.md).
COLUMNS = "asset_id, kind, site, parent_id, name, rated_kw, host, port, location, engineer_email"
SCHEMA = (
    "CREATE TABLE assets ("
    " asset_id TEXT PRIMARY KEY,"
    " kind TEXT NOT NULL,"
    " site TEXT NOT NULL,"
    " parent_id TEXT REFERENCES assets(asset_id),"
    " name TEXT NOT NULL,"
    " rated_kw REAL,"
    " host TEXT,"
    " port INTEGER,"
    " location TEXT,"
    " engineer_email TEXT,"
    f" {versions.COLUMN_SQL})",
)
SELECT = f"SELECT {COLUMNS}, {versions.COLUMN} FROM assets WHERE {{column}} = ? ORDER BY asset_id"
BY_ID = SELECT.format(column="asset_id")
BY_SITE = SELECT.format(column="site")
BY_KIND = SELECT.format(column="kind")
BY_PARENT = SELECT.format(column="parent_id")
INSERT = f"INSERT INTO assets ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
SET_ENGINEER = f"UPDATE assets SET engineer_email = ?, {versions.BUMP} WHERE asset_id = ?"


class RegistryError(ValueError):
    """Raised for an asset the registry refuses: RegistryError("OAHE-INV-001 is already registered")."""


def schema() -> tuple[str, ...]:
    """The registry's tables as schema statements: store.apply(connect(), schema()) leaves an empty table assets."""
    return SCHEMA


def to_asset(row: sqlite3.Row) -> Asset:
    """A row read back as a leaf Asset: the row ("OAHE-SEN-001", "SEN", "OAHE", None, "Sensor", None, …, 1) gives
    Asset("OAHE-SEN-001", AssetKind.SENSOR, "OAHE", None, "Sensor", None), at version 1."""
    asset_id, kind, site, parent_id, name, rated_kw, host, port, location, engineer_email, version = row
    return Asset(asset_id, AssetKind(kind), site, parent_id, name, rated_kw, host, port, location, engineer_email,
                 version)


def select(conn: sqlite3.Connection, query: str, value: str) -> tuple[Asset, ...]:
    """The assets one of the queries above finds for a value, in id order: select(conn, BY_SITE, "OAHE") gives OAHE's
    assets, OAHE-INV-001 before OAHE-INV-002."""
    rows = conn.execute(query, (value,))
    return tuple(to_asset(row) for row in rows)


def get(conn: sqlite3.Connection, asset_id: str) -> Asset | None:
    """The asset of one id, or None: get(conn, "OAHE-INV-001") is the inverter, get(conn, "OAHE-INV-999") is None."""
    found = select(conn, BY_ID, asset_id)
    return found[0] if found else None


def by_site(conn: sqlite3.Connection, site: str) -> tuple[Asset, ...]:
    """A site's assets in id order, its own site asset among them: by_site(conn, "OAHE") has ten in the example fleet."""
    return select(conn, BY_SITE, site)


def by_kind(conn: sqlite3.Connection, kind: AssetKind) -> tuple[Asset, ...]:
    """The assets of one kind in id order: by_kind(conn, AssetKind.TRACKER) is (OAHE-TRK-001, OAHE-TRK-002)."""
    return select(conn, BY_KIND, kind.value)


def children(conn: sqlite3.Connection, parent_id: str) -> tuple[Asset, ...]:
    """The assets whose parent is one id, in id order: children(conn, "OAHE-INV-001") is (OAHE-STR-001, OAHE-STR-002)."""
    return select(conn, BY_PARENT, parent_id)


def refusal(conn: sqlite3.Connection, asset: Asset) -> str | None:
    """Why the registry refuses an asset, or None: an Asset("OAHE-INV-001", AssetKind.STRING, …) gives
    "OAHE-INV-001: kind STR disagrees with the id's INV". A malformed id raises the leaf's MalformedAssetId."""
    # Invariant: SOL-05 (a malformed id is refused where it enters, never stored)
    site, kind, _ = parse_asset_id(asset.asset_id)
    if kind is not asset.kind:
        return f"{asset.asset_id}: kind {asset.kind.value} disagrees with the id's {kind.value}"
    if site != asset.site:
        return f"{asset.asset_id}: site {asset.site} disagrees with the id's {site}"
    if get(conn, asset.asset_id) is not None:
        return f"{asset.asset_id} is already registered"
    if asset.parent_id is None:
        return None
    parent = get(conn, asset.parent_id)
    if parent is None:
        return f"{asset.asset_id}: parent {asset.parent_id} is not registered"
    if parent.site != asset.site:
        return f"{asset.asset_id}: parent {asset.parent_id} is at site {parent.site}, not {asset.site}"
    return None


def register(conn: sqlite3.Connection, asset: Asset) -> None:
    """Stores one asset, or refuses it with RegistryError (MalformedAssetId for a malformed id) and stores nothing:
    register(conn, Asset("OAHE-SIT-001", AssetKind.SITE, "OAHE", None, "Oahe", None)) makes get(conn, "OAHE-SIT-001")
    that asset; registering it again raises RegistryError("OAHE-SIT-001 is already registered")."""
    # Invariant: SOL-05
    reason = refusal(conn, asset)
    if reason is not None:
        raise RegistryError(reason)
    values = (
        asset.asset_id, asset.kind.value, asset.site, asset.parent_id, asset.name, asset.rated_kw,
        asset.host, asset.port, asset.location, asset.engineer_email,
    )
    conn.execute(INSERT, values)
    conn.commit()


def load_fleet(conn: sqlite3.Connection, assets: tuple[Asset, ...]) -> None:
    """Registers each asset in order, a parent before its children; the first refusal raises and stops the load, the
    assets before it staying stored: load_fleet(conn, (site, inverter)) stores both."""
    for asset in assets:
        register(conn, asset)


def known(conn: sqlite3.Connection, asset_id: str) -> Asset:
    """The registered asset of one id, or RegistryError: known(conn, "OAHE-INV-999") raises
    RegistryError("OAHE-INV-999 is not registered")."""
    asset = get(conn, asset_id)
    if asset is None:
        raise RegistryError(f"{asset_id} is not registered")
    return asset


def upgrade(conn: sqlite3.Connection) -> None:
    """Gives an assets table made before 12.2 its version column, every asset at version 1."""
    versions.add_column(conn, "assets")


def assign_engineer(conn: sqlite3.Connection, asset_id: str, email: str, read_at: int | None = None) -> None:
    """Sets the engineer who services one asset and raises its version; the leaf's Asset refuses a malformed address
    with ValueError, and an asset read at an older version StaleWrite (12.2), each writing nothing:
    assign_engineer(conn, "OAHE-INV-002", "b@x.org") makes get(conn, "OAHE-INV-002").engineer_email "b@x.org"."""
    current = known(conn, asset_id)
    versions.check(f"asset {asset_id}", current.version, read_at)
    checked = dataclasses.replace(current, engineer_email=email)
    conn.execute(SET_ENGINEER, (checked.engineer_email, asset_id))
    conn.commit()


def engineers_for(conn: sqlite3.Connection, asset_id: str) -> tuple[str, ...]:
    """Whom to write to about an asset: its engineer, then its parent's, then its site's, distinct and skipping None;
    in the example fleet engineers_for(conn, "OAHE-STR-001") is ("inverter@oahe.example", "site@oahe.example")."""
    asset = known(conn, asset_id)
    chain = [asset]
    if asset.parent_id is not None:
        chain.append(known(conn, asset.parent_id))
    site = get(conn, site_id(asset.site))
    if site is not None:
        chain.append(site)
    emails: list[str] = []
    for link in chain:
        if link.engineer_email is not None and link.engineer_email not in emails:
            emails.append(link.engineer_email)
    return tuple(emails)
