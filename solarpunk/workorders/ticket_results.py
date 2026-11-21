"""The failed results a ticket holds (7.9, SP-046): the ticket_results table, one row per failed result linked to a
ticket, a ticket holding a streak of them (one ticket, many failed results). A result belongs to at most one ticket
(result_id is unique); rows are only added, never updated or deleted. It imports nothing of ours (MOD-05): project
decides which results belong together (project/result_tickets.py)."""
import sqlite3

# The SQL lives here, at module level, where mutmut does not reach (docs/MUTATION.md, J-008).
SCHEMA = ("CREATE TABLE ticket_results (wo_id INTEGER NOT NULL, result_id INTEGER NOT NULL UNIQUE)",)
INSERT = "INSERT INTO ticket_results (wo_id, result_id) VALUES (?, ?)"
TICKET_OF = "SELECT wo_id FROM ticket_results WHERE result_id = ?"
RESULTS_OF = "SELECT result_id FROM ticket_results WHERE wo_id = ? ORDER BY result_id"


def schema() -> tuple[str, ...]:
    """The statements that make the ticket_results table: schema()[0] starts with "CREATE TABLE ticket_results"."""
    return SCHEMA


def link(conn: sqlite3.Connection, wo_id: int, result_id: int) -> None:
    """Links a failed result to a ticket and commits: link(conn, 1, 7) then ticket_of(conn, 7) is 1; a result already
    linked, to any ticket, raises sqlite3.IntegrityError and changes nothing."""
    conn.execute(INSERT, (wo_id, result_id))
    conn.commit()


def ticket_of(conn: sqlite3.Connection, result_id: int) -> int | None:
    """The ticket a result is linked to, or None: after link(conn, 1, 7), ticket_of(conn, 7) is 1 and of 8 is None."""
    row = conn.execute(TICKET_OF, (result_id,)).fetchone()
    return None if row is None else row[0]


def results_of(conn: sqlite3.Connection, wo_id: int) -> tuple[int, ...]:
    """The ids of the results a ticket holds, oldest first: a ticket linked to results 7 and 8 gives (7, 8)."""
    return tuple(row[0] for row in conn.execute(RESULTS_OF, (wo_id,)))
