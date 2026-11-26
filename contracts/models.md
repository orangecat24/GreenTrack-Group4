# P3 01 model and inference contract draft

Person 3 owns this proposal. The [synthetic payloads](../fixtures/person3/model_payloads.json)
exercise the shapes offline. Person 1 and Person 2 review them before implementation.

## Forecast target and seasonal baseline

The hour-aligned `forecast_origin` is a historical information cutoff. The first
target starts exactly at that cutoff. For steps 1 through 24, target start is
origin plus step minus one hours, and target end is one hour later. The run covers
`[origin, origin + 24 hours)`. Each target is the kWh measured over one full hour
for `household-1`. Use [gold hourly consumption](data.md) as the input and label
interface. The `Z` examples follow the provisional source-clock convention in the
[assistant draft](assistant.md#window-units-and-coverage).

The seasonal prediction for a target is the observed kWh of the hour starting
168 hours before that target. Compare model and baseline on the same chronological
held-out origins, targets and eligible labels. Define the split dates and
near-zero MAPE rule during P3 05 and report RMSE on the shared eligible set.

## Candidate feature order

Use a direct forecast. One candidate XGBoost model predicts one kWh value per
row, with a horizon feature identifying the target. Each row has these five
numbers in order.

| Position | Feature | Value |
| --- | --- | --- |
| 1 | `horizon_step` | 1 through 24 |
| 2 | `target_hour` | 0 through 23 on the agreed historical clock |
| 3 | `target_weekday` | Monday = 0 through Sunday = 6 |
| 4 | `origin_lag_1_kwh` | kWh of the hour ending at the origin, shared by all 24 rows |
| 5 | `target_lag_168_kwh` | kWh of the target's same hour in the previous week |

Calendar features are known in advance. Every observed input must be complete,
finite, available by the cutoff, and have an interval end at or before it.
Historical evaluation should use versioned input evidence and account for
late arrivals and corrections before claiming point-in-time availability.
Require the exact two lag sources for each target (one origin lag and 24
seasonal hours across the run). A measured zero is valid. An absent, null, or
partial lag makes the run `insufficient_history` for this draft. There is no
imputation in the starter design. Use the same feature builder at training,
evaluation and serving, and use future observations only as eligible labels.

## Separate model endpoints

| Endpoint | Proposed request | Proposed response |
| --- | --- | --- |
| Forecast adapter | `application/json`, `{"instances":[[...], ...]}` with 24 five-number rows in target order | `application/json`, `{"predictions":[...]}` with 24 finite nonnegative kWh values in the same order |
| Built-in Random Cut Forest (RCF) | Candidate `text/csv`, one complete hour per line with one feature, `energy_kwh`, and no header or metadata columns | Candidate `application/json`, `{"scores":[{"score":0.42}, ...]}` in matching row order |

The forecast envelope describes the proposed serving adapter. Confirm the RCF
wire format and row ordering against the selected container before integration.
The caller retains the ordered timestamps and joins predictions or scores back
to them. A wrong response count, malformed row or invalid number fails that
component rather than assigning results to the wrong hour.

RCF scores are unitless model-specific measures of unusualness. Larger scores
mean more unusual relative to the fitted model. For this draft use
`is_anomaly = raw_score >= threshold`; choose the threshold using training or
validation evidence and version it with the model. The fixture uses a made-up
threshold and scores. An RCF score can exceed 1, and a flag alone gives no cause,
probability, or counterfactual expected usage. Skip incomplete hours and keep
coverage counts so callers can distinguish skipped hours from scored negatives.

## Combined window Lambda proposal for Person 2

The Lambda accepts `household_id`, `reference_start`, `reference_end`,
`forecast_origin`, and `horizon_hours` (24). The aligned historical reference
window is half-open and ends at or before the origin. It selects anomaly hours
by their starts. The forecast builder may read the required lag buckets outside
that window. The forecast target window is derived separately from the origin.

The example response echoes the request fields and adds provenance and two
components. `forecast` carries target bounds, model version, status, and hourly
`items`. `anomalies` carries its own model version, threshold, status,
`expected_hours`, `scored_hours`, and scored `items`. Each item names the hour
with `timestamp` and `interval_end`. Anomaly items also carry `observed_kwh`,
`raw_score` and `is_anomaly`. Sort both lists by hour. Draft component statuses
are `ok`, `insufficient_history` (forecast), `no_data` (no eligible anomaly
hours), and `error` (failed component). A failed or unavailable component has
empty items. If its model metadata is unavailable use null, and use null
`scored_hours` on error when scoring did not finish. A valid request can retain
the successful component when its peer fails. Reject invalid input before
calling either endpoint. The exact validation/error transport and window limit
are pending Person 2 review.

The live mapping needs review before any storage or API changes. Current
`ForecastPoint.method` is `illustrative_previous_day`; current anomaly
`score` is limited to 0–1 and `expected_kwh` is required. Raw RCF output cannot
populate those fields directly. Discuss run/version keys, forecast origin
selection, null/coverage mapping from gold and model provenance with Person 2.
[Current Python models](../api/app/models.py) · [Person 2 storage handoff](../docs/person2-handoff.md)
