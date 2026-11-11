# GreenTrack SPA

React + TypeScript + Vite, plain CSS, and Recharts. Requires **Node 24**.
All consumption, anomaly, forecast, and assistant responses come from FastAPI;
the browser contains no copy of its fixture arrays. Small synthetic objects in
`src/test/` are test doubles only.

## Windows PowerShell

Start FastAPI from the repository root in terminal 1:

```powershell
$env:APP_DATA_MODE = 'mock'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir api --reload
```

In terminal 2, from the repository root:

```powershell
cd web
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. Both servers need to remain running; Ctrl+C stops each.
Use `npm.cmd` in PowerShell because this computer blocks the `npm.ps1` wrapper.
Dependencies are already installed; `npm.cmd ci` reproduces `package-lock.json`
after cloning or changing branches. No activation script or global setting is needed.

```powershell
# Run from web/ (the watch-mode test command is npm.cmd test).
npm.cmd run test:run
npm.cmd run build
npm.cmd run lint
```

## Real browser smoke flow (local and CI)

Prerequisites: Node 24, the repository-root Python 3.14 `.venv`, and dependencies
installed from `api/requirements-dev.txt` and `web/package-lock.json`.
On Windows PowerShell, from the repository root:

```powershell
# Only create .venv if it is absent; keep your existing local environment.
# py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements-dev.txt
cd web
npm.cmd ci
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

The browser install downloads Playwright's matching Chromium to its local cache;
repeat it after changing the Playwright version. It is separate from `npm ci`.
No browser extension, personal Chrome profile, AWS credentials, or prestarted
servers are needed. The test is headless by default; use
`npm.cmd run test:e2e -- --headed` to watch it.

`playwright.config.ts` starts fresh FastAPI and Vite processes on **18000** and
**15173**, waits for readiness through `/api/health`, and tears down its processes
after the test. The API launcher explicitly selects mock mode and removes inherited
AWS settings. The web server sets `VITE_API_BASE_URL=/api` and the server-only
`API_PROXY_TARGET=http://127.0.0.1:18000`, overriding deployment settings for this
test. Normal development remains on 8000/5173 and is left alone. If the test ports
are already occupied, stop the previous test process or let it finish; the smoke
flow deliberately refuses to reuse an unidentified server.

The single flow visits Consumption, Anomalies, Forecast, and Assistant; narrows
the history to June 1 and verifies its 13.46 kWh total; restores the week; checks
actual/illustrative forecast labels; sends a chat question; and requests a weekly
summary while checking that an unsent draft survives. It uses real API responses
and blocks unexpected external browser requests. Vitest only collects `src/`
unit/component tests, keeping the browser flow separate.

On Linux/CI, use `python3.14 -m venv .venv`, then
`.venv/bin/python -m pip install -r api/requirements-dev.txt` from the root.
From `web/`, run `npm ci`, `npx playwright install --with-deps chromium`, and
`npm run test:e2e`. The `--with-deps` option installs Linux browser libraries too;
it may need administrator privileges on a local Linux machine.
This follows [Playwright's browser installation guidance](https://playwright.dev/docs/browsers).

`.github/workflows/demo-checks.yml` performs the API tests, frontend tests, build,
lint, and smoke flow on a pull request or manual workflow run, using Python 3.14
and Node 24. See [the PR check guide](../docs/pr-checks.md) for local commands,
failed-step logs, cancellation, and conditional Terraform checks. It does not deploy anything. CI executes the same
[Playwright webServer setup](https://playwright.dev/docs/test-webserver) as local
testing, with the executable path selected for Windows or Linux by
`scripts/start-mock-api.mjs`.

Failures leave an ignored HTML report in `web/playwright-report/` and a screenshot
and trace in `web/test-results/`. Run `npx.cmd playwright show-report` to view the
report. Browser artifacts and `node_modules` must not be committed.

## Deployed browser smoke

`npm.cmd run test:deployed` uses `playwright.deployed.config.ts` and starts no
local servers. Set `DEPLOYED_WEBSITE_URL` and `DEPLOYED_API_BASE_URL` to the real
authorized Terraform application outputs. It runs the same four-tab/date/chat
journey as the local flow, plus health and explicit CORS preflight checks. It
also verifies the browser actually requests the deployed API origin, catching
frontend builds that accidentally retained `/api`. There are two retries, no
deployed screenshots/traces, and no fallback URL. This command sends real HTTPS
requests; collection with `--list` does not execute them.

See [deployment-pipeline.md](../docs/deployment-pipeline.md) for exact activation
variables, commands and recovery. The existing ordinary checks remain offline;
the separate main deployment pipeline reuses them and is disabled until a
maintainer explicitly activates it. No cloud deployment has been run here.

The build produces ignored `web/dist/`. `npm.cmd run preview` serves those static
files for inspection; it does **not** provide the development API proxy.

## API base URL: exact convention

`VITE_API_BASE_URL` is the **complete prefix before an endpoint**. The client
appends `/consumption`, `/anomalies`, `/forecast`, or `/chat` directly to it,
removing any trailing slash first. It does not add another `/api` automatically.

| Setting | Browser request for consumption | Required server behavior |
| --- | --- | --- |
| unset, empty, or `/api` | `/api/consumption?...` | During development, Vite strips `/api` and proxies to `http://127.0.0.1:8000/consumption?...` |
| `/api` in a production build | `/api/consumption?...` | Production hosting must route `/api/*` to the API and strip `/api` |
| `https://api.example.com` | `https://api.example.com/consumption?...` | Direct API deployment at the domain root |
| `https://api.example.com/stage` | `https://api.example.com/stage/consumption?...` | API deployed under `/stage` |
| `/` | `/consumption?...` | API routes at the same origin's root |

For deployment, set the value **before** `npm.cmd run build`, e.g.:

```powershell
$env:VITE_API_BASE_URL = 'https://api.example.com/stage'
npm.cmd run build
Remove-Item Env:\VITE_API_BASE_URL
```

Alternatively copy `.env.example` to `.env.local` and edit the public value.
Restart Vite after changing environment files. Vite embeds `VITE_*` variables
in browser JavaScript at build time: never put credentials or secrets in them.
Changing a server environment variable after uploading `dist/` does not change
the compiled base URL. These behaviors follow [Vite's environment contract](https://vite.dev/guide/env-and-mode).

The `/api` proxy is [development-server configuration](https://vite.dev/config/server-options.html#server-proxy),
not something included in static output. A cross-origin deployment also needs
HTTPS and explicit CORS permission for the frontend's origin on the API/gateway.
The current mock API has no CORS middleware; use the development proxy locally.
Prepared deployment configuration now lives in `infra/challenge1`, called from
the existing dev Terraform root. Its HTTP API owns CORS for the CloudFront
origin and the two local port-5173 origins; FastAPI still has no CORS middleware.
The default deployment uses the API Gateway HTTPS endpoint with no `/api` or
named-stage suffix. Use the `application.api_base_url` Terraform output as
`VITE_API_BASE_URL` before building. No infrastructure or uploads were executed.
See [the deployment/build guide](../docs/application-infrastructure.md) for exact
PowerShell/Linux commands, upload order, cache headers and verification limits.

## Behavior and file tour

- History defaults to June 1–7, 2009, for `household-1`. **Through** is inclusive;
  `dates.ts` converts it to next-day UTC midnight for the API's exclusive end.
- Forecast targets default to June 8 and have their own selector. The historical
  selector controls its separate actual series. Origin, target horizon, coverage,
  units, and the backend's illustrative-forecast note remain visible.
- Each response's `is_demo` controls its Demo data badge. UTC is a demo convention,
  not a claim about the source dataset timezone. Empty results are not failures.
- `App.tsx`: shared history filters and four tabs held in simple React state.
- `components/`: one view per tab, shared state/coverage widgets, chart and table.
- `api/types.ts` mirrors Pydantic JSON; `api/client.ts` joins URLs, encodes queries,
  posts chat requests, and translates FastAPI errors into readable messages.
- `hooks/useApiRead.ts`: fetch on URL changes, cancellation, stale-response guard,
  loading/error state and retry. The surrounding shell stays visible on failure.
- `chartData.ts`: map returned records to distinct actual/forecast chart keys.
- `styles.css`: responsive layout, focus indicators, and reduced-motion support.
- `*.test.ts(x)` and `test/`: transport, date, mapping, UI, and cancellation checks.

The Assistant submits real HTTP requests to the mock `/chat` route, including
`request_type=weekly_summary`. It displays the returned placeholder messages,
disconnected status and empty-citation notice without claiming an AI integration.
Changing history resets its conversation and aborts an outstanding request;
failed subsequent requests leave earlier messages visible.

## Validation and dependency notes

Latest review, November 8, 2026, with Node 24.22.2 / npm 11.19.1 and Python
3.14.10: **57 API tests, 20 frontend tests, and one Playwright Chromium flow
passed**. The production TypeScript/Vite build passed and lint passed with zero
warnings. The API suite retains one upstream Starlette/HTTPX deprecation warning.
The GitHub-hosted Linux workflow is configured but has not been executed from
this local session; its result is not claimed as tested here.

One user-facing bug was reproduced before fixing it: a successful weekly-summary
request erased an unsent question from the textarea. The assistant now clears
that field only after successfully sending a chat question. A Testing Library
regression test and the browser flow both cover this behavior. No API behavior
needed changing. Existing tests already cover validation, inclusive/exclusive
date boundaries, hourly/daily totals, empty results, and offline mock startup;
they were retained instead of duplicating them.

Forecasts remain a separate dashed illustrative series with an explicit origin
and target horizon, distinct from observed consumption. The chart mapping test
checks overlapping timestamps without blending the values; the browser flow
checks the visible labels and non-model disclaimer. Chat/summary responses remain
placeholders, show the disconnected state, and provide no fabricated citations.

`package-lock.json` records exact resolved versions. The `minimatch` override
selects the patched 11.x line for development tools while upstream ranges still
select an affected 10.x line ([advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249)).
The installed dependency audit reports **zero vulnerabilities**; lint, build and
tests were rerun with the override. No global npm configuration was changed.

## SPA versus C# Razor Pages

A traditional Razor request runs server handlers, builds HTML from a page model,
and sends a new document to the browser. Here the first request downloads an HTML
shell and React code. A tab or filter changes `useState`; a `useEffect` fetches
JSON from FastAPI; React re-renders the affected components in the same document.
Props are like inputs to Razor partials, but state and rendering live in the
browser. FastAPI owns validation and data rules, and React owns presentation.
See [React's effect lifecycle](https://react.dev/reference/react/useEffect) for
why cleanup cancels old requests when dependencies change.
