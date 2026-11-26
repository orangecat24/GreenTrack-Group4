# Person 3 P3 01 fixture and review handoff

The drafts and offline verification are complete. Teammate review is pending.
Every value, model result and citation here is synthetic. The dates use the
proposed historical clock for easy comparison with existing interfaces. The
examples have their own readings and provenance. [Data contract](../../contracts/data.md)

| File | What it shows |
| --- | --- |
| [gold_hourly.json](gold_hourly.json) | Gold hourly rows for one synthetic household and day |
| [gold_daily_expected.json](gold_daily_expected.json) | Expected gold daily and peak rows, with separate window coverage metadata |
| [model_payloads.json](model_payloads.json) | Forecast input lags and features, forecast and RCF endpoint examples, and the combined Lambda request and response |
| [chat_examples.json](chat_examples.json) | Mock placeholder responses, a validation error, and proposed assistant outcomes with synthetic citations |

The gold-shaped objects use the fields produced by the Glue job. The surrounding
JSON carries fixture metadata. The proposed assistant uses the gold data to
explain the observed total and coverage. The proposed model caller turns
complete gold hours into input rows, then pairs the endpoint results with the
corresponding hours. The model example supplies separate synthetic previous-week
lag values because the gold fixture is one day long.
[Gold job](../../data/glue/gold_job.py) · [Model draft](../../contracts/models.md)
· [Assistant draft](../../contracts/assistant.md)

## Minute recipe and expected values

All times are on 1 June 2009. Each of the first three sub-meter columns
specifies Wh for each minute in the row.

| Hour starts | Minute rows | Active power (kW) | Kitchen (Wh) | Laundry (Wh) | Heater/AC (Wh) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 00:00 normal | 60 | 1.5 | 10 | 5 | 5 |
| 01:00 partial | 30 | 1.5 | 5 | 5 | 5 |
| 01:00 partial | 30 | null | null | null | null |
| 02:00 all-null | 60 | null | null | null | null |
| 03:00 absent | 0 | | | | |
| 04:00 measured zero | 60 | 0 | 0 | 0 | 0 |
| 05:00 spike | 30 | 12 | 20 | 10 | 30 |
| 05:00 spike | 30 | 3 | 20 | 10 | 30 |
| 06:00 through 23:00 absent | 0 each | | | | |

Add the minute power values divided by 60 to get kWh. Add each sub-meter's
minute values divided by 1,000 to get that circuit's kWh. Subtract the three
sub-meter totals from total energy to get the residual `other_kwh`. The
synthetic day has **9.75 observed kWh** and **210 of 1,440 measured minutes**.
It contains three complete, one partial, one all-null, and 19 absent hours.
The observed peak hour starts at **05:00** with **7.5 kWh**. The highest minute
power is **12 kW**. Coverage includes the complete hour with measured zero.

For a duplicate example, imagine the normal 00:00 minute arrived first as
2 kW and then arrived again as 1.5 kW with a newer load timestamp. Bronze
retains both original rows. Silver keeps the newer reading for that household
and minute, so exactly one 1.5 kW reading goes into gold. Within an input batch
the job orders matching timestamps by load timestamp and then source file.
Across batches the merge updates a matching household/minute when the
incoming load timestamp is newer or equal. This fixture recipe starts at the
deduplicated boundary. [Silver job](../../data/glue/silver_job.py)

## Reproduce the offline checks

From the repository root using the project's Node 24 toolchain, run:

```powershell
node fixtures/person3/check.mjs
git diff --check
```

The checker uses built-in Node modules. It parses all four JSON files,
recalculates the gold rows and coverage from the synthetic minute recipe,
and checks all 24 forecast feature rows and target intervals plus the mapping
of the three RCF scores to eligible hours. It checks all eight chat examples
for envelope shape and consistency with the gold fixture. The current examples
were compared with the FastAPI models, service, route and TypeScript types by
source inspection. The checker exercises fixture data. Runtime FastAPI tests
were outside this verification because a runnable Python environment was
unavailable in the checkout.
[Python models](../../api/app/models.py) · [TypeScript types](../../web/src/api/types.ts)

## Pending teammate review

| Reviewer | Review and decisions |
| --- | --- |
| Person 1 | Confirm the deployed gold column types, nullability, clock and day boundaries, residual cases with mismatched nulls, and run/snapshot identity. The draft data contract says `int` for `minutes_with_data`; Spark's `count` produces a long. Review complete-hour inputs, the 24-hour target, exact lags and feature order, and whether corrections or publication delay affect what is available by the origin. Confirm Region, model/container access and wire format, and the gold read path for later live verification. |
| Person 2 | Review the JSON examples, combined request validation and component error handling, and mapping of gold nulls and coverage into API/storage. Agree how to store raw RCF scores and flags, choose an active forecast run, and carry model versions. For chat, review new statuses, coverage and provenance, weekly-summary window rules, citation rendering and the 503 UI behavior. |

Person 1's handoffs report successful AWS runs of the separate pipeline
fixture and matching Athena summaries. The checks above independently verify
only the local Person 3 examples. Deployment, assistant runtime grants,
Athena consumer-role queries, endpoint access and live results remain pending
for Person 3. [Gold AWS results](../../docs/data-lake-gold.md#verified-results-2026-11-15-applied-and-run-in-aws)
· [Upload workflow handoff](../../docs/data-lake-orchestration.md)
