@echo off
rem Solarpunk on Windows, one word: "solarpunk" opens the fleet window on solarpunk.db in the current folder,
rem "solarpunk --demo" the demo, "solarpunk --db fleet.db" another store (python -m solarpunk.ui, every argument as
rem typed). A first word that is one of the command line's own (test, fleet, fault, ticket, account, telemetry, kpi, report, clauses, help) goes to
rem python -m solarpunk.cli instead: "solarpunk test run", "solarpunk test list", "solarpunk test add <name>".
rem "solarpunk --shortcut" puts a desktop shortcut to this file, with Solarpunk's icon, starting in the current folder.
rem "solarpunk --help" (or -h, or help) lists every command: python -m solarpunk.cli help.
rem It runs from any folder once this folder is on PATH: the store stays in the folder you typed it in.
rem test/test_launcher.py holds the command words to the command line's own.
setlocal
if defined PYTHONPATH (set "PYTHONPATH=%~dp0;%PYTHONPATH%") else (set "PYTHONPATH=%~dp0")
set "SOLARPUNK_MODULE=solarpunk.ui"
for %%c in (test fleet fault ticket account telemetry kpi report clauses help) do if "%~1"=="%%c" set "SOLARPUNK_MODULE=solarpunk.cli"
set "SOLARPUNK_HELP="
for %%h in (--help -h) do if "%~1"=="%%h" set "SOLARPUNK_HELP=yes"
if defined SOLARPUNK_HELP (py -m solarpunk.cli help) else (py -m %SOLARPUNK_MODULE% %*)
exit /b %ERRORLEVEL%
