import type { ConsumptionPoint, ForecastPoint } from './api/types'

export interface ChartRow { timestamp: number; actual?: number; forecast?: number }

/** Convert API records to chart rows; no fixture values or predictions live here. */
export function chartRows(actual: ConsumptionPoint[], forecast: ForecastPoint[] = []): ChartRow[] {
  const rows = new Map<number, ChartRow>()
  for (const point of actual) {
    const timestamp = Date.parse(point.timestamp)
    rows.set(timestamp, { timestamp, actual: point.energy_kwh })
  }
  for (const point of forecast) {
    const timestamp = Date.parse(point.timestamp)
    rows.set(timestamp, { ...rows.get(timestamp), timestamp, forecast: point.energy_kwh })
  }
  // Keep gaps between observed and future series. We never fill the future
  // with actual readings or join forecasts to observed measurements.
  return [...rows.values()].sort((a, b) => a.timestamp - b.timestamp)
}
