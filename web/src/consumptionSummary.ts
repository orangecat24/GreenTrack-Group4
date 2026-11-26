import type { ConsumptionResponse } from './api/types'

/** Summarize only observed numeric energy. Null is different from measured zero.
 * Coverage comes from bucket counts AND observed minutes, not first/last dates. */
export function consumptionSummary(data: ConsumptionResponse) {
  const step = data.grain === 'daily' ? 86_400_000 : 3_600_000
  const expected = Math.max(0, Math.ceil(Date.parse(data.requested_end) / step) - Math.ceil(Date.parse(data.requested_start) / step))
  const missing = Math.max(0, expected - data.items.length)
  const numbers = data.items.flatMap(item => item.energy_kwh === null ? [] : [item.energy_kwh])
  const incomplete = data.items.filter(item => item.is_complete === false).length
  const unknown = data.items.filter(item => item.minutes_with_data == null || item.is_complete == null).length
  const nulls = data.items.filter(item => item.energy_kwh === null).length
  return {
    total: numbers.length ? numbers.reduce((a, b) => a + b, 0) : null,
    peak: numbers.length ? Math.max(...numbers) : null,
    missing, incomplete, nulls, unknown,
    minutes: data.items.reduce((sum, item) => sum + (item.minutes_with_data ?? 0), 0),
    expectedMinutes: expected * step / 60_000,
    partial: missing > 0 || incomplete > 0 || nulls > 0 || (data.data_source === 'gold' && unknown > 0),
  }
}
