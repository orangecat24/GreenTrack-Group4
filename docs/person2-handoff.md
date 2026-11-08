# Person 2: first mock API increment

Decision for our 7–10 day delivery: start with a small FastAPI service and an
explicit provisional contract. A React/TypeScript/Vite SPA now consumes it in `web/`.
No AWS adapter, deployed infrastructure, or AI integration is included yet.
Python 3.14.10 was used; Node 24 LTS is the frontend target. Persistent teaching
and stack instructions are in `AGENTS.md`.

## Run on Windows PowerShell

Run from the repository root. The project `.venv` already exists; on another
machine create it once with `py -3.14 -m venv .venv`. Use its executable directly
so PowerShell activation policy and the system's older `python` do not interfere.

```powershell
# Reproduce the pinned development environment when needed (downloads packages).
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt

# Start locally; stop with Ctrl+C. Mock is also the default when this is unset.
$env:APP_DATA_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
```

Open http://127.0.0.1:8000/docs to try the typed requests interactively.
The bare http://127.0.0.1:8000/ now redirects there. Previously `/` had no route
and returned `{"detail":"Not Found"}` even while the API was healthy.
Use http://127.0.0.1:8000/health for the JSON health check, and port 5173 for the React app.
In a second terminal, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -c api\pytest.ini api\tests -q
.\.venv\Scripts\python.exe -m pip check
Invoke-RestMethod 'http://127.0.0.1:8000/consumption?household_id=household-1&start=2009-06-01T00:00:00Z&end=2009-06-02T00:00:00Z&grain=daily'
```

`api/requirements.txt` pins runtime dependencies including transitive packages;
`requirements-dev.txt` includes those pins plus test dependencies. `.env.example`
is safe documentation; the API does not automatically load `.env` files. No AWS
settings are needed. Unsupported `APP_DATA_MODE` values deliberately fail startup.

## Provisional contract and fixture decisions

- `GET /health` reports mock process health. `GET /consumption`, `/anomalies`, and
  `/forecast` require `household_id`, `start`, `end`. Use ISO datetimes with `T`
  and explicit offsets; they are normalized to UTC. Start is inclusive and end
  exclusive, selecting buckets by their **start timestamp**.
- Consumption accepts `grain=hourly` (default) or `daily`. Daily boundaries must
  be UTC midnight; reject partial-day requests rather than label partial sums
  as full daily totals. `energy_kwh` is energy per interval, not kW power.
- `household-1` has 168 continuous synthetic hours in
  `[2009-06-01T00:00:00Z, 2009-06-08T00:00:00Z)`. Seven daily totals are calculated
  from those readings, totaling 111.80 kWh. Three anomalies reference the same
  hourly values: June 2 at 18:00, June 4 at 19:00, June 6 at 12:00.
- The illustrative forecast origin is June 8 at 00:00 UTC. Its 24 hourly targets
  cover `[June 8 00:00, June 9 00:00)` by repeating June 7's observations.
  Queries filter **target** timestamps. This is not a trained/validated model.
- UTC is **only a demo convention**. The source dataset's timezone is unconfirmed;
  none of these synthetic readings are represented as source dataset records.
- Read envelopes include typed `items`, `units`, `requested_start/end`,
  `covered_start/end`, `next_cursor=null`, and `is_demo=true`. Coverage is the
  boundaries of returned whole buckets; hourly coverage can extend beyond an
  unaligned requested end. Empty results have null coverage. Results are ordered,
  deterministic, and bounded at 168/7/3/24 items (hourly/daily/anomalies/forecast),
  so this increment needs no pagination. Add stable query-bound cursors before
  introducing an unbounded real repository.
- Household IDs follow `household-<positive integer>`. Well-formed unknown IDs
  and valid windows without data return `200` with empty items. Invalid inputs,
  missing fields, unsupported grain, and extra parameters return FastAPI's `422`
  `detail` error list. Equal or reversed dates are invalid.
- `POST /chat` accepts the same household/window plus `request_type=chat` and
  `message`; or `request_type=weekly_summary` without a message. Both return
  `status=placeholder`, `assistant_connected=false`, `is_demo=true`, empty
  citations, and an explicit placeholder / Bedrock-disconnected explanation.

Example weekly-summary JSON for `/docs`:

```json
{"household_id":"household-1","start":"2009-06-01T00:00:00Z","end":"2009-06-08T00:00:00Z","request_type":"weekly_summary"}
```

## File tour, checks, and handoffs

`api/app/main.py` owns routes and startup; `models.py` defines Pydantic contracts;
`service.py` filters windows and computes daily totals; `repository.py` owns the
fixtures and a small storage protocol. `api/tests/` exercises actual routes and
startup in memory, removes common AWS credential settings, and blocks application
network connections (allowing only Windows' internal event-loop socketpair).

Validation on Windows/Python 3.14.10: **56 tests passed**, `pip check` passed,
and a real local Uvicorn smoke check passed for `/health`, `/docs`, and the
13.46 kWh daily response; the temporary server was stopped. The test dependency
currently emits one upstream Starlette warning about future migration from
HTTPX to HTTPX2. There are no failing tests. No live AWS/AI checks apply here.

For example, the daily consumption request above enters the **route**, which
validates its query. The **service** asks the **repository** for hourly observations,
selects June 1's 24 buckets, and sums them. Pydantic/FastAPI returns **JSON** with
one daily item (`energy_kwh=13.46`), units and covered dates. Routes handle HTTP;
services handle rules; repositories supply data. Changing storage should not
require rewriting the HTTP routes.

Person 1 can implement the repository contract once gold/DynamoDB access patterns
are ready; Person 3 can replace the assistant placeholder and supply model outputs.
Confirm source timezone and agree any contract changes through review, while
continuing against these fixtures. The four React views now use this API; next
integration work is replacing the mock repository and assistant through reviewed
contracts. No commits or pushes were made by the implementation tasks.

## React SPA increment

See [web/README.md](../web/README.md) for exact PowerShell start/check commands,
the file tour, deployment base-URL examples, and the SPA/Razor comparison.
Start FastAPI on port 8000, then run `npm.cmd run dev` from `web/` and visit
http://127.0.0.1:5173. The default `/api` prefix is stripped by Vite's development
proxy. Production must provide that route or set `VITE_API_BASE_URL` to the actual
API prefix **before building**; no endpoint suffix or credentials belong in it.

History uses inclusive calendar dates (converted to the API's exclusive end).
Forecast has its own June 8 target window and separate actual/forecast series.
All displayed records come from the API; demo flags, units, UTC caveats and
placeholder assistant behavior remain visible. Requests are cancelled/ignored
when filters change. Validation: 19 frontend tests, production build, lint, and
a real desktop/mobile Chrome smoke check passed. npm reports zero vulnerabilities.

Review update (November 8): 57 API tests, 20 frontend tests, build, lint, and a
committed Playwright Chromium smoke flow passed locally. Run `npm.cmd run test:e2e`
from `web/`; first install its browser with `npx.cmd playwright install chromium`.
The test starts/stops its own mock servers on 18000/15173. The new demo-checks
workflow runs the same checks in CI; the remote workflow has not been run here.
Fixed weekly-summary requests deleting an unsent chat draft. See `web/README.md`
for setup, browser installation, reporting, and the remaining upstream API warning.
