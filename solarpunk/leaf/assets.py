"""An asset is one thing in the fleet with an id of one shape (Invariant: SOL-05): a site, an inverter, a string, a
tracker, a meter or a sensor, each under a site and optionally under a parent asset."""
import re
from dataclasses import dataclass

from solarpunk.leaf.codes import AssetKind

ASSET_ID_SHAPE = re.compile(r"^(?P<site>[A-Z0-9]{2,6})-(?P<kind>[A-Z]{3})-(?P<number>\d{3})$")
KIND_BY_PREFIX: dict[str, AssetKind] = {kind.value: kind for kind in AssetKind}
EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class MalformedAssetId(ValueError):
    """Raised for an asset id not of the shape SITE-KIND-nnn, or whose kind prefix is not an AssetKind: MalformedAssetId("x")."""


@dataclass(frozen=True)
class Asset:
    """One asset: Asset("OAHE-INV-003", AssetKind.INVERTER, "OAHE", None, "Inverter 3", 100.0, "10.0.0.3", 5020).
    rated_kw is None for an asset that produces nothing (a sensor, a meter, a tracker, a site); host and port are the
    endpoint its data feed is read from (Phase 2), None for an asset with no feed (a site, a string); location is where
    the asset physically is, in words; engineer_email is who services it and whom the mailer writes to (Phase 2); version
is the stored record's (12.2)."""

    asset_id: str
    kind: AssetKind
    site: str
    parent_id: str | None
    name: str
    rated_kw: float | None
    host: str | None = None
    port: int | None = None
    location: str | None = None
    engineer_email: str | None = None
    version: int = 1  # 12.2: raised by one with every change the registry stores

    def __post_init__(self) -> None:
        """A port is 1 to 65535 and comes with a host: Asset(…, host="10.0.0.3", port=0) raises ValueError."""
        if (self.host is None) != (self.port is None):
            raise ValueError(f"{self.asset_id}: host and port come together")
        if self.port is not None and not 1 <= self.port <= 65535:
            raise ValueError(f"{self.asset_id}: port {self.port} is not 1 to 65535")
        if self.engineer_email is not None and not EMAIL_SHAPE.match(self.engineer_email):
            raise ValueError(f"{self.asset_id}: {self.engineer_email!r} is not an email address")


def parse_asset_id(asset_id: str) -> tuple[str, AssetKind, int]:
    """The site, kind and number of a well-formed id: parse_asset_id("OAHE-INV-003") is ("OAHE", AssetKind.INVERTER, 3);
    parse_asset_id("OAHE-INV-3") and parse_asset_id("OAHE-XYZ-003") raise MalformedAssetId."""
    match = ASSET_ID_SHAPE.match(asset_id)
    if match is None:
        raise MalformedAssetId(f"{asset_id!r} is not of the shape SITE-KIND-nnn")
    prefix = match.group("kind")
    if prefix not in KIND_BY_PREFIX:
        raise MalformedAssetId(f"{asset_id!r}: {prefix} is not an asset kind")
    return match.group("site"), KIND_BY_PREFIX[prefix], int(match.group("number"))


def site_id(site: str) -> str:
    """A site's own asset id: site_id("OAHE") is "OAHE-SIT-001"."""
    return f"{site}-SIT-001"
