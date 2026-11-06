# Person 2: first mock API increment

Decision for our 7–10 day delivery: start with a small FastAPI service and an
explicit provisional contract; build React/TypeScript/Vite against it next.
No frontend, AWS adapter, deployed infrastructure, or AI integration is included yet.
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
  citations, and an explicit Person 3 / Bedrock-disconnected explanation.

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
continuing against these fixtures. Next Person 2 step: simple React views using
this API. No commits or pushes were made by the implementation task.
