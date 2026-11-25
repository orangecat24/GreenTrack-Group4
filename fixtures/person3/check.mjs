// Offline fixture verifier. Run from the repository root with Node.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

function readFixture(name) {
  const data = JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'))
  assert.equal(data.is_synthetic, true, name)
  return data
}

const hourly = readFixture('gold_hourly.json')
const daily = readFixture('gold_daily_expected.json')
const models = readFixture('model_payloads.json')
const chat = readFixture('chat_examples.json')
const hourMs = 60 * 60 * 1000
const day = '2009-06-01'
const household = { household_id: 'household-1' }
const partition = { year: 2009, month: 6 }
const iso = (time) => new Date(time).toISOString().replace('.000Z', 'Z')
const nextHour = (time) => iso(Date.parse(time) + hourMs)
const at = (hour) => iso(Date.parse(day) + hour * hourMs)
const round = (number) => Number(number.toFixed(9))

// Bands stand for minutes with identical readings. Use W for active power and
// Wh for sub-meters to keep the arithmetic in integers until the final division.
// A null band contains existing rows with all measurements missing.
const bands = [
  [0, 60, 1500, 10, 5, 5],
  [1, 30, 1500, 5, 5, 5],
  [1, 30, null, null, null, null],
  [2, 60, null, null, null, null],
  [4, 60, 0, 0, 0, 0],
  [5, 30, 12000, 20, 10, 30],
  [5, 30, 3000, 20, 10, 30],
]

function goldConsumption(period_start, readings, minutesRequired) {
  const measured = readings.filter(([power]) => power !== null)
  const sum = (column) => readings.reduce(
    (total, row) => total + (row[column] ?? 0), 0,
  )
  const energy_kwh = sum(0) / 60000
  const [kitchen_kwh, laundry_kwh, heater_ac_kwh] = [1, 2, 3].map(
    (column) => sum(column) / 1000,
  )
  return {
    ...household,
    period_start,
    energy_kwh: measured.length ? energy_kwh : null,
    kitchen_kwh: measured.length ? kitchen_kwh : null,
    laundry_kwh: measured.length ? laundry_kwh : null,
    heater_ac_kwh: measured.length ? heater_ac_kwh : null,
    other_kwh: measured.length
      ? round(energy_kwh - kitchen_kwh - laundry_kwh - heater_ac_kwh)
      : null,
    minutes_with_data: measured.length,
    is_complete: measured.length === minutesRequired,
    ...partition,
  }
}

const minuteBuckets = Map.groupBy(bands, ([hour]) => hour)
const minuteRows = (bandsForPeriod) => bandsForPeriod.flatMap(
  ([, count, ...readings]) => Array.from({ length: count }, () => readings),
)
const expectedHourly = [...minuteBuckets].map(([hour, entries]) =>
  goldConsumption(at(hour), minuteRows(entries), 60),
)
assert.deepEqual(hourly.window, { start: at(0), end: at(24) })
assert.deepEqual(hourly.hourly_consumption, expectedHourly)
assert.deepEqual(daily.window, hourly.window)
assert.deepEqual(daily.daily_consumption, [
  goldConsumption(at(0), minuteRows(bands), 1440),
])

const peak = expectedHourly
  .filter((row) => row.energy_kwh !== null)
  .sort((a, b) => b.energy_kwh - a.energy_kwh || a.period_start.localeCompare(b.period_start))[0]
assert.deepEqual(daily.daily_peak, [{
  ...household,
  day,
  peak_hour_start: peak.period_start,
  peak_hour_kwh: peak.energy_kwh,
  max_minute_power_kw: Math.max(...minuteRows(bands).map(([power]) => power ?? -Infinity)) / 1000,
  ...partition,
}])

function coverageFor(start, end) {
  const rows = expectedHourly.filter(({ period_start }) => period_start >= start && period_start < end)
  const hours = (Date.parse(end) - Date.parse(start)) / hourMs
  return {
    expected_minutes: hours * 60,
    measured_minutes: rows.reduce((total, row) => total + row.minutes_with_data, 0),
    complete_hours: rows.filter((row) => row.is_complete).length,
    partial_hours: rows.filter((row) => row.minutes_with_data > 0 && !row.is_complete).length,
    all_null_hours: rows.filter((row) => row.minutes_with_data === 0).length,
    absent_hours: hours - rows.length,
  }
}
assert.deepEqual(daily.coverage, coverageFor(daily.window.start, daily.window.end))

const { request, response } = models.combined_window_lambda
const { forecast, anomalies, provenance, ...echo } = response
assert.deepEqual(request, {
  ...household,
  reference_start: at(0),
  reference_end: at(6),
  forecast_origin: at(6),
  horizon_hours: 24,
})
assert.deepEqual(echo, request)
assert.deepEqual(provenance, { source: 'synthetic_fixture', source_id: 'person3-starter' })
assert.equal(forecast.target_start, request.forecast_origin)
assert.equal(forecast.target_end, at(30))
assert.equal(forecast.status, 'ok')
assert.equal(anomalies.status, 'ok')

const forecastEndpoint = models.forecast_endpoint
const rcfEndpoint = models.rcf_endpoint
assert.equal(forecastEndpoint.content_type, 'application/json')
assert.equal(rcfEndpoint.content_type, 'text/csv')
assert.equal(forecastEndpoint.accept, 'application/json')
assert.equal(rcfEndpoint.accept, 'application/json')
const { instances } = forecastEndpoint.request_body
const { predictions } = forecastEndpoint.response_body
const { origin_lag_1: recent, previous_week_hours: baseline } = models.feature_sources
const { period_start, energy_kwh, minutes_with_data, is_complete } = peak
assert.deepEqual(recent, { period_start, energy_kwh, minutes_with_data, is_complete })
assert.equal(nextHour(recent.period_start), request.forecast_origin)
for (const list of [instances, predictions, baseline, forecast.items]) {
  assert.equal(list.length, request.horizon_hours)
}
for (const [index, seasonal] of baseline.entries()) {
  const target = new Date(Date.parse(request.forecast_origin) + index * hourMs)
  assert.equal(seasonal.period_start, iso(target.getTime() - 168 * hourMs))
  assert.ok(nextHour(seasonal.period_start) <= request.forecast_origin)
  assert.equal(seasonal.minutes_with_data, 60)
  assert.equal(seasonal.is_complete, true)
  assert.ok(Number.isFinite(seasonal.energy_kwh) && seasonal.energy_kwh >= 0)
  assert.deepEqual(instances[index], [
    index + 1, target.getUTCHours(), (target.getUTCDay() + 6) % 7,
    recent.energy_kwh, seasonal.energy_kwh,
  ])
  assert.ok(Number.isFinite(predictions[index]) && predictions[index] >= 0)
  assert.deepEqual(forecast.items[index], {
    timestamp: iso(target),
    interval_end: nextHour(iso(target)),
    energy_kwh: predictions[index],
  })
}

const scored = expectedHourly.filter((row) =>
  row.is_complete && row.period_start >= request.reference_start && row.period_start < request.reference_end,
)
assert.equal(rcfEndpoint.request_body, scored.map((row) => row.energy_kwh).join('\n') + '\n')
const { scores } = rcfEndpoint.response_body
assert.equal(scores.length, scored.length)
assert.equal(anomalies.scored_hours, scored.length)
assert.equal(anomalies.expected_hours, (Date.parse(request.reference_end) - Date.parse(request.reference_start)) / hourMs)
assert.ok(Number.isFinite(anomalies.threshold) && anomalies.threshold > 0)
assert.deepEqual(anomalies.items, scored.map((row, index) => {
  const { score } = scores[index]
  assert.ok(Number.isFinite(score) && score >= 0)
  return {
    timestamp: row.period_start,
    interval_end: nextHour(row.period_start),
    observed_kwh: row.energy_kwh,
    raw_score: score,
    is_anomaly: score >= anomalies.threshold,
  }
}))
assert.deepEqual(anomalies.items.filter((row) => row.is_anomaly).map((row) => row.timestamp), [peak.period_start])

const baseFields = [
  'answer', 'assistant_connected', 'citations', 'household_id', 'is_demo',
  'request_type', 'requested_end', 'requested_start', 'status',
]
for (const example of [...chat.current, ...chat.proposed]) {
  const { request: body, response: result } = example
  if (example.http_status === 422) {
    assert.equal(Object.hasOwn(body, 'household_id'), false)
    assert.deepEqual(result.detail, [{
      type: 'missing', loc: ['body', 'household_id'], msg: 'Field required', input: body,
    }])
    continue
  }
  const hasMessage = Object.hasOwn(body, 'message')
  const expectedKeys = ['household_id', 'start', 'end', 'request_type']
  if (hasMessage) expectedKeys.push('message')
  assert.deepEqual(Object.keys(body).sort(), expectedKeys.sort(), example.name)
  assert.equal(body.household_id, household.household_id)
  assert.equal(body.start, iso(Date.parse(body.start)))
  assert.equal(body.end, iso(Date.parse(body.end)))
  assert.ok(body.start < body.end)
  assert.ok(['chat', 'weekly_summary'].includes(body.request_type))
  if (hasMessage || body.request_type === 'chat') {
    assert.equal(typeof body.message, 'string')
    assert.ok(body.message.trim().length >= 1 && body.message.trim().length <= 2000)
  }
  const proposed = chat.proposed.includes(example)
  const responseFields = proposed ? [...baseFields, 'coverage', 'provenance'] : baseFields
  assert.deepEqual(Object.keys(result).sort(), responseFields.sort(), example.name)
  assert.equal(result.household_id, body.household_id)
  assert.equal(result.request_type, body.request_type)
  assert.equal(result.requested_start, body.start)
  assert.equal(result.requested_end, body.end)
  assert.ok(typeof result.answer === 'string' && result.answer.length > 0)
  assert.equal(result.is_demo, true)
  assert.equal(result.assistant_connected, false)
  assert.ok(Array.isArray(result.citations))
  if (!proposed) {
    const feature = body.request_type === 'chat' ? 'chat' : 'weekly summary'
    assert.equal(result.status, 'placeholder')
    assert.equal(result.answer, `Placeholder: ${feature} is not implemented. Bedrock is not connected.`)
    assert.deepEqual(result.citations, [])
    continue
  }
  assert.ok(['ok', 'no_data', 'refused', 'error'].includes(result.status))
  assert.equal(example.http_status, result.status === 'error' ? 503 : 200)
  assert.equal(Date.parse(body.start) % hourMs, 0)
  assert.equal(Date.parse(body.end) % hourMs, 0)
  if (body.request_type === 'weekly_summary') {
    assert.equal(Date.parse(body.start) % (24 * hourMs), 0)
    assert.equal(Date.parse(body.end) - Date.parse(body.start), 168 * hourMs)
  }
  const coversData = result.status === 'ok' || result.status === 'no_data'
  assert.deepEqual(result.coverage, coversData ? coverageFor(body.start, body.end) : null)
  assert.deepEqual(result.provenance, {
    source: 'synthetic_fixture', source_id: coversData ? 'person3-starter' : null,
  })
  if (result.status === 'ok') {
    assert.ok(result.citations.length > 0)
    assert.ok(result.answer.includes(`${daily.daily_consumption[0].energy_kwh} kWh`))
  } else {
    assert.deepEqual(result.citations, [])
  }
  for (const citation of result.citations) {
    assert.deepEqual(Object.keys(citation).sort(), ['title', 'url'])
    assert.match(citation.title, /synthetic/i)
    assert.equal(new URL(citation.url).hostname, 'example.invalid')
  }
}

console.log('P3 01 verified: 4 JSON fixtures, 5 gold hours, daily totals/coverage/peak, 24 forecast features/targets, 3 RCF scores, and 8 chat examples.')
