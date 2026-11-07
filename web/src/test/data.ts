import type { AnomalyPoint, ChatResponse, ConsumptionPoint, ConsumptionResponse, ForecastResponse, ReadResponse } from '../api/types'

// Small test doubles only: production screens always fetch their values. These
// deliberately do not duplicate the backend's 168-point fixture or its totals.
export const reading: ConsumptionPoint = {
  household_id: 'household-1', timestamp: '2009-06-01T00:00:00Z',
  interval_end: '2009-06-02T00:00:00Z', energy_kwh: 12.34,
}
export const consumption: ConsumptionResponse = {
  household_id: 'household-1', items: [reading], units: { energy_kwh: 'kWh' },
  requested_start: '2009-06-01T00:00:00Z', requested_end: '2009-06-08T00:00:00Z',
  covered_start: reading.timestamp, covered_end: reading.interval_end,
  next_cursor: null, is_demo: true, grain: 'daily',
  timezone_note: 'UTC is a demo convention only; the source dataset timezone is unconfirmed.',
}
export const anomalies: ReadResponse<AnomalyPoint> = {
  ...consumption, units: { observed_kwh: 'kWh', expected_kwh: 'kWh', score: 'unitless' },
  items: [{ household_id: 'household-1', timestamp: reading.timestamp, interval_end: reading.interval_end,
    observed_kwh: 3.6, expected_kwh: 1.1, score: 0.95, reason: 'Test spike from API' }],
}
export const forecast: ForecastResponse = {
  ...consumption, forecast_origin: '2009-06-08T00:00:00Z',
  target_start: '2009-06-08T00:00:00Z', target_end: '2009-06-09T00:00:00Z',
  covered_start: '2009-06-08T00:00:00Z', covered_end: '2009-06-08T01:00:00Z',
  note: 'Illustrative values, not a trained model.',
  items: [{ ...reading, timestamp: '2009-06-08T00:00:00Z', interval_end: '2009-06-08T01:00:00Z',
    forecast_origin: '2009-06-08T00:00:00Z', method: 'illustrative_previous_day', energy_kwh: 0.77 }],
}
export const chat: ChatResponse = {
  household_id: 'household-1', request_type: 'chat', requested_start: consumption.requested_start,
  requested_end: consumption.requested_end, status: 'placeholder',
  answer: 'Person 3 placeholder: Bedrock is not connected.', citations: [], assistant_connected: false, is_demo: true,
}

export function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}
