import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { consumptionSummary } from './consumptionSummary'
import { chartRows } from './chartData'
import { consumption, forecast, jsonResponse, reading } from './test/data'

// Invented unit-test values only. Live smoke expectations come from the reviewed
// export files, not these test doubles or a second fixture array in production.
const gold = { ...consumption, data_source: 'gold' as const, is_demo: false,
  requested_end: '2009-06-03T00:00:00Z', items: [
    { ...reading, energy_kwh: null, minutes_with_data: 0, is_complete: false },
    { ...reading, timestamp: '2009-06-02T00:00:00Z', interval_end: '2009-06-03T00:00:00Z', energy_kwh: 2, minutes_with_data: 720, is_complete: false },
  ] }

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async input => {
    const path = String(input)
    if (path.includes('/forecast')) return jsonResponse({ ...forecast, status: 'unavailable', data_source: 'unavailable',
      forecast_origin: null, target_start: null, target_end: null, items: [], note: 'Forecast model is not integrated.' })
    if (path.includes('/anomalies')) return jsonResponse({ ...gold, status: 'unavailable', data_source: 'unavailable',
      items: [], is_demo: true, note: 'Anomaly detection is not integrated.' })
    return jsonResponse(gold)
  }))
})

it('shows real provenance, observed totals and partial minute coverage', async () => {
  render(<App />)
  expect(await screen.findByText('Historical source data')).toBeInTheDocument()
  expect(screen.queryByText('Demo data')).not.toBeInTheDocument()
  expect(screen.queryByText(/Synthetic energy demo/)).not.toBeInTheDocument()
  expect(screen.getByText('Observed energy')).toBeInTheDocument()
  expect(screen.getByText('2.00', { selector: '.primary strong' })).toBeInTheDocument()
  expect(screen.getByText(/720 \/ 2880 observed minutes/)).toBeInTheDocument()
  expect(screen.getByText(/not a complete-period total/)).toBeInTheDocument()
  expect(screen.getByText('Unavailable', { selector: 'td' })).toBeInTheDocument()
})

it('distinguishes all-null energy from a measured numeric zero', () => {
  const empty = consumptionSummary({ ...gold, items: [gold.items[0]] })
  expect(empty.total).toBeNull()
  expect(consumptionSummary({ ...gold, items: [{ ...gold.items[0], energy_kwh: 0, minutes_with_data: 60 }] }).total).toBe(0)
})

it('renders no measured energy instead of a false 0 kWh total', async () => {
  vi.mocked(fetch).mockResolvedValue(jsonResponse({ ...gold, items: [gold.items[0]] }))
  render(<App />)
  expect(await screen.findByText('No measured energy')).toBeInTheDocument()
  expect(screen.queryByText('0.00', { selector: '.primary strong' })).not.toBeInTheDocument()
})

it('keeps gold provenance on a successful empty window', async () => {
  vi.mocked(fetch).mockResolvedValue(jsonResponse({ ...gold, items: [], covered_start: null, covered_end: null }))
  render(<App />)
  expect(await screen.findByText(/No records in this window/)).toBeInTheDocument()
  expect(screen.getByText('Historical source data')).toBeInTheDocument()
  expect(screen.queryByText('Demo data')).not.toBeInTheDocument()
})

it('shows unavailable features separately from empty data and invents no model dates', async () => {
  render(<App />)
  await screen.findByText('Historical source data')
  fireEvent.click(screen.getByRole('button', { name: 'Anomalies' }))
  expect(await screen.findByText('Anomaly detection is not integrated.')).toBeInTheDocument()
  expect(screen.queryByText(/No records in this window/)).not.toBeInTheDocument()
  expect(screen.queryByText('Demo data')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Forecast' }))
  expect(await screen.findByText('Forecast model is not integrated.')).toBeInTheDocument()
  expect(screen.queryByText(/Origin:/)).not.toBeInTheDocument()
  expect(screen.queryByText('Demo data')).not.toBeInTheDocument()
  expect(screen.getByRole('img', { name: /2 actual and 0 forecast/ })).toBeInTheDocument()
})

it('detects omitted periods and creates visual null gaps without changing source rows', () => {
  const first = { ...reading, energy_kwh: 1 }
  const third = { ...first, timestamp: '2009-06-03T00:00:00Z', interval_end: '2009-06-04T00:00:00Z' }
  const data = { ...gold, requested_end: third.interval_end, items: [first, third] }
  expect(consumptionSummary(data).missing).toBe(1)
  const rows = chartRows(data.items)
  expect(rows).toHaveLength(3)
  expect(rows[1].actual).toBeNull()
  expect(data.items).toHaveLength(2)
})
