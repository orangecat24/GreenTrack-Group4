import { expect, it } from 'vitest'
import { chartRows } from './chartData'
import { forecast, reading } from './test/data'

it('keeps actual and forecast as separate keys, including overlapping targets', () => {
  const predicted = forecast.items[0]
  const rows = chartRows([reading, { ...reading, timestamp: predicted.timestamp }], [predicted])
  expect(rows).toHaveLength(3)
  expect(rows[1].actual).toBeNull() // The absent observation periods form a visual gap.
  expect(rows[0].actual).toBe(reading.energy_kwh)
  expect(rows[0].forecast).toBeUndefined()
  expect(rows[2]).toEqual({ timestamp: Date.parse(predicted.timestamp), actual: reading.energy_kwh, forecast: predicted.energy_kwh })
  expect(chartRows([], [predicted])[0].actual).toBeUndefined()
})
