"""The clock (lane 2.5, SP-006): `jobs` renders one `Job` (name, command, cadence) to a crontab line and to a
`schtasks /Create` command, each against a golden; `install` and `remove` are the only functions that run the
platform's tool, and no test calls them (F-03). Run: python3 -m solarpunk.schedule render solarpunk-kpi."""
