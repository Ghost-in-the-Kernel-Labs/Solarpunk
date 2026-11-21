"""The asset window's words and colours (3.2, 6.4, 7.5, 12.4), with no tkinter so the fast loop tests them: the
asset's field lines and title, its status line and colour, the open faults' rows with who assigned each, the
diagnostics' rows failing first with their tags, the suggestions' rows, the catalogue codes' labels, and a refusal's
words. asset_window.py lays them out over one project.asset_detail call (SP-010: it imports project and the leaf
alone)."""
from solarpunk.ui import cells

from solarpunk import project
from solarpunk.leaf.assets import Asset
from solarpunk.leaf.codes import AssetStatus, FaultCode, lookup

# The words and colours the window shows live here, at module level, where mutmut does not reach (J-008, J-014).
NONE_WORD = "none"
PASS_WORD = "pass"
FAIL_WORD = "FAIL"
NOT_RUN_WORD = "not run"
FAILING_TAG = "failing"
NOT_RUN_TAG = "notrun"
RED_TEXT = "#c0392b"
GREY_TEXT = "#808080"
# The surface's states (project.Diagnostic.state) in the window's words: a failure shouts, the rest do not.
STATE_WORDS = {"fail": FAIL_WORD, "not run": NOT_RUN_WORD, "pass": PASS_WORD}
OPENED_FORMAT = "%Y-%m-%d %H:%M UTC"
COLOURS: dict[AssetStatus, str] = {
    AssetStatus.GREEN: "#2e8b57",
    AssetStatus.YELLOW: "#e0b000",
    AssetStatus.RED: "#c0392b",
}
FAULT_COLUMNS = ("code", "meaning", "opened", "by")
FAULT_HEADINGS = ("Code", "Meaning", "Opened", "Assigned by")
# The open faults' column widths in px: who assigned it, with an operator and cover, is the longest cell (SP-015).
FAULT_WIDTHS = (70, 175, 165, 470)
RESULT_COLUMNS = ("test", "result", "reason")
RESULT_HEADINGS = ("Test", "Result", "Reason")
# The diagnostics' column widths in px: the reason is the column a reader needs whole (6.4).
RESULT_WIDTHS = (190, 70, 480)
OPEN_FAULTS_TITLE = "Open faults"
DIAGNOSTICS_TITLE = "Diagnostics"
ASSIGN_TITLE = "Assign a fault"
ASSIGN_TEXT = "Assign"
ENGINEER_TITLE = "Engineer"
SAVE_TEXT = "Save"
CANCEL_TEXT = "Cancel"
CHOOSE_CODE = "Choose a code to assign."
CHOOSE_ENGINEER = "Choose the engineer who assigned it: only an engineer assigns a fault (SP-015)."
CHOOSE_WORD = "Choose the engineer whose word it is: an operator enters a fault on an engineer's word (SP-015)."
SUGGESTED_TITLE = "Suggested faults (the tests' and the devices', for an engineer to accept or dismiss)"
SUGGESTION_COLUMNS = ("code", "meaning", "source", "reason", "raised")
SUGGESTION_HEADINGS = ("Code", "Meaning", "From", "Why", "Raised")
SUGGESTION_WIDTHS = (70, 190, 110, 255, 165)
ACCEPT_TEXT = "Accept"
DISMISS_TEXT = "Dismiss"
REASON_TITLE = "Reason (to dismiss)"
CHOOSE_SUGGESTION = "Choose a suggested fault first."
GIVE_REASON = "Give the reason it is dismissed: a dismissal is a decision that says why (SP-015)."
ASSIGNED_BY_TITLE = cells.ASSIGNED_BY
ENTERED_BY_TITLE = "Entered by (operator, if called in)"
REFUSALS = (project.LedgerError, project.RegistryError, project.UnknownAsset, project.UnknownEngineer,
            project.SuggestionError, project.NotPermitted, ValueError)


def shown(value: object) -> str:
    """A field's value as the window writes it: shown(None) is "none", shown("Pad A") is "Pad A", shown(5020) "5020"."""
    return NONE_WORD if value is None else str(value)


def endpoint(asset: Asset) -> str:
    """Where the asset's feed is read: "127.0.0.1:5020" for host 127.0.0.1 and port 5020; "none" with no host."""
    return NONE_WORD if asset.host is None else f"{asset.host}:{asset.port}"


def rated(asset: Asset) -> str:
    """The rated power in words: "100.0 kW" for rated_kw 100.0; "none" for an asset that produces nothing."""
    return NONE_WORD if asset.rated_kw is None else f"{asset.rated_kw} kW"


def field_lines(asset: Asset) -> tuple[str, ...]:
    """The fields block, one line per label: for OAHE-INV-001 under OAHE-SIT-001 at Pad A, ("Kind: Inverter",
    "Site: OAHE", "Parent: OAHE-SIT-001", "Rated: 100.0 kW", "Location: Pad A", "Endpoint: 127.0.0.1:5020",
    "Engineer: inverter@oahe.example"); a missing value reads "none"."""
    return (
        f"Kind: {asset.kind.name.capitalize()}",
        f"Site: {asset.site}",
        f"Parent: {shown(asset.parent_id)}",
        f"Rated: {rated(asset)}",
        f"Location: {shown(asset.location)}",
        f"Endpoint: {endpoint(asset)}",
        f"Engineer: {shown(asset.engineer_email)}",
    )


def window_title(asset: Asset) -> str:
    """The window's title: "OAHE-INV-001 — Inverter 1"."""
    return f"{asset.asset_id} — {asset.name}"


def status_line(status: AssetStatus) -> str:
    """The status line's words: status_line(AssetStatus.RED) is "Status: red"."""
    return f"Status: {status.value}"


def colour_of(status: AssetStatus) -> str:
    """The status colour, the glyph's three: colour_of(AssetStatus.RED) is "#c0392b", GREEN "#2e8b57"."""
    return COLOURS[status]


def assigned_text(fault: project.Fault, cover: bool) -> str:
    """Who assigned a fault, as the window writes it (SP-015): "tech@oahe.example"; entered by an operator,
    "tech@oahe.example, entered by ops@oahe.example"; with cover, " (cover)" after; a fault from before, "unrecorded"."""
    entered = "" if fault.recorded_by is None else f", entered by {fault.recorded_by}"
    return f"{fault.assigned_by}{entered}{' (cover)' if cover else ''}"


def fault_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str, str], ...]:
    """The open-faults rows (code, meaning, opened, assigned by): an open INV-001 opened 2026-06-01 10:10 UTC by
    tech@oahe.example gives (("INV-001", "Inverter offline: …", "2026-06-01 10:10 UTC", "tech@oahe.example"),); no open
    fault gives ()."""
    return tuple((fault.code, meaning, fault.opened.strftime(OPENED_FORMAT), assigned_text(fault, cover))
                 for (fault, meaning), cover in zip(detail.open_faults, detail.cover))


def result_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str], ...]:
    """The diagnostics' rows (test, result, reason) in the detail's order (6.4): every remote test of the asset's kind,
    failing first, then never run, then passing: a failed on_grid, five tests never run and a passed reachable give
    ("on_grid", "FAIL", "10:05: off the grid") first and ("reachable", "pass", "3 records") last."""
    return tuple((found.test_name, STATE_WORDS[found.state], found.reason) for found in detail.diagnostics)


def suggestion_lines(detail: project.AssetDetail) -> tuple[tuple[str, str, str, str, str], ...]:
    """The suggested-faults rows (code, meaning, from, why, raised) in the detail's order, a device's first: OAHE-SEN-001's
    gives (("SEN-001", "Irradiance sensor out of range: …", "reachable", "127.0.0.1:9 is unreachable",
    "2026-06-01 13:00 UTC"),); none gives ()."""
    return tuple((found.code, lookup(found.code).meaning, found.source, found.reason,
                  found.raised_at.strftime(OPENED_FORMAT)) for found in detail.suggestions)


def row_tags(line: tuple[str, str, str]) -> tuple[str, ...]:
    """The tags a diagnostics row carries: ("failing",) for a FAIL row, drawn red; ("notrun",) for a test never run,
    drawn grey; () for a pass row."""
    if line[1] == FAIL_WORD:
        return (FAILING_TAG,)
    return (NOT_RUN_TAG,) if line[1] == NOT_RUN_WORD else ()


def code_labels(codes: tuple[FaultCode, ...]) -> tuple[str, ...]:
    """The fault dropdown's entries: INV-004 reads "INV-004 — Firmware update pending"; () gives ()."""
    return tuple(f"{code.code} — {code.meaning}" for code in codes)


def chosen_code(codes: tuple[FaultCode, ...], index: int) -> str | None:
    """The code at the dropdown's index, or None when nothing is chosen (index -1): for the inverter codes,
    chosen_code(codes, 1) is "INV-002" and chosen_code(codes, -1) is None."""
    return codes[index].code if 0 <= index < len(codes) else None


def refusal_text(refusal: Exception) -> str:
    """The message line for a refusal: refusal_text(ValueError("bad address")) is "Refused: bad address"."""
    return f"Refused: {refusal}"
