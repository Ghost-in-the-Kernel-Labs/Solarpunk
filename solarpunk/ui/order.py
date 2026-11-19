"""The fleet list's order and filter (9.4, SP-023), pure so the fast loop tests them: worst first (red, then yellow,
then green, ties by id), a column's sort, and the rows a search, a status and a kind keep. Three red assets among three
hundred are found without scrolling."""
from solarpunk.leaf.codes import AssetKind, AssetStatus
from solarpunk.project.surface import AssetRow
from solarpunk.ui.cells import row_text

SEVERITY = {AssetStatus.RED: 0, AssetStatus.YELLOW: 1, AssetStatus.GREEN: 2}
STATUS_COLUMN = 3


def worst_first(rows: tuple[AssetRow, ...]) -> tuple[AssetRow, ...]:
    """Red rows, then yellow, then green, each colour by id: (green INV-001, red INV-002, yellow SEN-001) gives
    (INV-002, SEN-001, INV-001)."""
    return tuple(sorted(rows, key=lambda row: (SEVERITY[row.status], row.asset_id)))


def sorted_by(rows: tuple[AssetRow, ...], column: int, reverse: bool = False) -> tuple[AssetRow, ...]:
    """The rows sorted by one column of their words, ties by id, the status column worst first rather than by its
    word: sorted_by(rows, 0) is id order; sorted_by(rows, 3) is worst_first(rows); reverse turns the order round."""
    if column == STATUS_COLUMN:
        ordered = worst_first(rows)
    else:
        ordered = tuple(sorted(rows, key=lambda row: (row_text(row)[column].casefold(), row.asset_id)))
    return tuple(reversed(ordered)) if reverse else ordered


def matching(rows: tuple[AssetRow, ...], text: str, status: AssetStatus | None,
             kind: AssetKind | None) -> tuple[AssetRow, ...]:
    """The rows whose words hold the text (any case, any column) and whose status and kind are the ones given (None
    keeps any), in their order: matching(rows, "inv-00", AssetStatus.RED, None) keeps the red inverters alone;
    matching(rows, "", None, None) keeps every row."""
    needle = text.strip().casefold()
    return tuple(row for row in rows
                 if (not needle or any(needle in word.casefold() for word in row_text(row)))
                 and (status is None or row.status is status)
                 and (kind is None or row.kind is kind))
