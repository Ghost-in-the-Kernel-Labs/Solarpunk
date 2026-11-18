"""pytest's hook for the window tests (J-053): before each test of a file that makes Tk windows, garbage is collected on
the main thread. A window a test leaves in a reference cycle is otherwise freed whenever the collector next runs, and
when that is inside another thread (the demo's simulator thread, as it starts) Tcl deletes its interpreter off the
thread that made it and aborts the whole run ("Fatal Python error: Aborted"). Only pytest runs these files with a
display (the fast loop's python3 has no tkinter), so this file is the one place the rule needs; test_cli_tests.py
collects at its setUp for a cousin of the same reason."""
import gc

import pytest

WINDOW_FILES = ("test_ui", "test_demo", "test_suggestions")


@pytest.fixture(autouse=True)
def collect_on_the_main_thread(request: pytest.FixtureRequest) -> None:
    """Collects garbage before a test of a window file, so no Tk object of an earlier test dies in a worker thread:
    for test_ui_asset.py's tests it runs, for test_kpi.py's it does nothing."""
    if request.path.name.startswith(WINDOW_FILES):
        gc.collect()
