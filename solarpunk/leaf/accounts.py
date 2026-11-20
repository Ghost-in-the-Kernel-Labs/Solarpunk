"""Who may act and where (SOL-16, SP-028): the four roles, an account as the leaf's frozen type, and the site an asset's
id names, so project can hold an account's scope against any record without reading another module. It imports the
leaf alone, so every module may read it."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from solarpunk.leaf.assets import ASSET_ID_SHAPE

ALL_SITES = "*"
MIN_PASSWORD = 12


class Role(Enum):
    """An account's one role: Role.VIEWER.value is "viewer"."""

    ENGINEER = "engineer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Account:
    """One account, never its password: Account("site@oahe.example", "Site engineer", Role.ENGINEER, True, created,
    ("OAHE",)); sites is ("*",) for all, and an admin's always is."""

    email: str
    name: str
    role: Role
    active: bool
    created: datetime
    sites: tuple[str, ...]

    def sees(self, site: str) -> bool:
        """Whether the account's scope holds a site: an account of ("*",) sees every site."""
        return ALL_SITES in self.sites or site in self.sites


def site_of(asset_id: str) -> str:
    """The site an asset's id names (SOL-05): site_of("OAHE-INV-002") is "OAHE"; an id of another shape raises
    ValueError."""
    found = ASSET_ID_SHAPE.match(asset_id)
    if found is None:
        raise ValueError(f"{asset_id} is not an asset id")
    return found.group("site")
