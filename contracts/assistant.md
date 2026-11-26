# P3 01 assistant and weekly-summary contract draft

## Current POST /chat

The [FastAPI models](../api/app/models.py), [service](../api/app/service.py)
and [TypeScript types](../web/src/api/types.ts) describe the running mock
interface. The [chat fixtures](../fixtures/person3/chat_examples.json) have
ordinary chat and weekly-summary request/response pairs.

- Body fields are `household_id`, `start`, `end`, `request_type` and optional
  `message`. The backend ID pattern is `^household-[1-9][0-9]*$`, with a
  maximum length of 64. Extra fields are rejected.
- FastAPI defaults `request_type` to `chat`. The frontend type includes it
  explicitly. `chat` requires a message of 1–2,000 characters after trimming.
  `weekly_summary` permits omission. The backend also accepts explicit null
  for a weekly-summary message. The frontend type uses omission.
- A valid body gets HTTP 200 with `household_id`, `request_type`,
  `requested_start`, `requested_end`, `status: "placeholder"`, `answer`,
  `citations: []`, `assistant_connected: false` and `is_demo: true`.
  Citation entries have `title` and `url`. The placeholder makes no data or
  model queries. Invalid input gets HTTP 422 with a FastAPI `detail` list.

## Window, units and coverage

The current API requires ISO 8601 date-times with `T` and explicit timezone,
normalizes offsets to UTC and requires `end > start`. The proposal selects
gold hourly buckets by start in `[start, end)`; require hour-aligned bounds
for data answers so whole hours agree with the requested duration. A weekly
summary uses exactly seven historical days starting and ending at midnight on
the agreed clock. These alignment and duration rules are proposed validation.
Resolve relative dates against an explicit historical period or ask for dates.

The source clock is recorded as written. The [data contract](data.md) proposes
representing it with UTC labels without shifting source times. Person 1 needs
to confirm Spark and Athena session time zones and day boundaries. Person 2
needs to agree how the API serializes and labels this clock in the UI.

All window totals are observed kWh. The daily peak hour is ranked by observed
kWh, with the earlier hour winning ties. Maximum single-minute power is kW.
Provide expected and measured minutes, and complete, partial, all-null and
absent hour counts. A partial hour contributes observed energy; an all-null or
missing hour contributes no measurement. A measured zero counts toward coverage.
Missing data stays unknown, and partial sums and peaks are labeled as observed.
Sub-meter values describe circuits or groups. Explain when missing sub-meter
readings limit the breakdown.

## Proposed responses for reviewed integration

Keep the request field names, the response envelope and citation shape. Add
`coverage` (the counts above, or null if unavailable) and `provenance`
(source kind and a source/run identifier when available). The fixtures use
`source: "synthetic_fixture"` and a reserved `example.invalid` URL. A deployed
adapter needs source references that are verifiable and suitable for its users.

| Outcome | HTTP | Proposed behavior |
| --- | --- | --- |
| `ok` | 200 | Return an evidence-backed answer. Include coverage for data-backed claims. With incomplete coverage, identify observed totals or omit a metric that cannot be supported. |
| `no_data` | 200 | A completed read found no usable measurements. Explain missing coverage and omit an energy total. |
| `refused` | 200 | A request outside the approved read-only energy scope receives a short refusal, with empty citations and null coverage. |
| Invalid body or unsupported window | 422 | Return the validation `detail` list. |
| `error` | 503 | Give a safe retry message, with empty citations and null coverage when the read fails. |

Fixture envelopes keep `assistant_connected: false` and `is_demo: true`.
Person 2 should review handling of structured non-2xx bodies, citation rendering
and status/provenance changes. For a future live response, set `is_demo` from
the data provenance and agree the exact semantics of `assistant_connected`.

A weekly summary follows the same response rules. With partial data it can
report the observed sum and its coverage and omit unsupported comparisons.
Publish forecast or anomaly claims only when versioned model results apply to
the report window and clearly identify forecast origin and targets. Report
behavior for advisory content, model association and any conversation history
remains pending review.
