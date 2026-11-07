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
No deployment or cloud configuration is created by this increment.

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

Validated with Node 24.22.2 / npm 11.19.1: **19 frontend tests passed**, production
TypeScript/Vite build passed, and lint passed with zero warnings. A real Chrome
smoke check verified the Vite proxy, 111.80 kWh total, three anomalies, 168 actual
and 24 forecast intervals, weekly-summary response, and mobile layout without
browser exceptions. Temporary QA-owned servers/browser were stopped.

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
