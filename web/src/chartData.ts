import type { ConsumptionPoint, ForecastPoint } from './api/types'

export interface ChartRow { timestamp: number; actual?: number | null; forecast?: number }

/** Convert API records to chart rows; no fixture values or predictions live here. */
export function chartRows(actual: ConsumptionPoint[], forecast: ForecastPoint[] = []): ChartRow[] {
  const rows = new Map<number, ChartRow>()
  for (const point of actual) {
    const timestamp = Date.parse(point.timestamp)
    rows.set(timestamp, { timestamp, actual: point.energy_kwh })
  }
  // A missing API bucket has no row for Recharts to break on. Add a *visual*
  // null marker at the previous interval end, never a fabricated zero reading.
  const ordered = [...actual].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
  for (let i = 1; i < ordered.length; i++) {
    const end = Date.parse(ordered[i - 1].interval_end)
    if (end < Date.parse(ordered[i].timestamp) && !rows.has(end)) rows.set(end, { timestamp: end, actual: null })
  }
  for (const point of forecast) {
    const timestamp = Date.parse(point.timestamp)
    rows.set(timestamp, { ...rows.get(timestamp), timestamp, forecast: point.energy_kwh })
  }
  // Keep gaps between observed and future series. We never fill the future
  // with actual readings or join forecasts to observed measurements.
  return [...rows.values()].sort((a, b) => a.timestamp - b.timestamp)
}
