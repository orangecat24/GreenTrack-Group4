import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { anomalies, chat, consumption, forecast, jsonResponse } from './test/data'

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  fetchMock.mockImplementation(async (input, options) => {
    const path = String(input)
    if (path.includes('/chat')) {
      const body = JSON.parse(String(options?.body))
      return jsonResponse({ ...chat, request_type: body.request_type })
    }
    if (path.includes('/anomalies')) return jsonResponse(anomalies)
    if (path.includes('/forecast')) return jsonResponse(forecast)
    return jsonResponse(consumption)
  })
  vi.stubGlobal('fetch', fetchMock)
})

describe('dashboard request/render cycle', () => {
  it('renders API totals and demo/UTC labels, then changes aggregation', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText('12.34', { selector: '.primary strong' })).toBeInTheDocument()
    expect(screen.getByText('Demo data')).toBeInTheDocument()
    expect(screen.getByText(/source dataset timezone is unconfirmed/)).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain('end=2009-06-08T00%3A00%3A00.000Z')
    await user.selectOptions(screen.getByLabelText('Consumption interval'), 'hourly')
    await waitFor(() => expect(String(fetchMock.mock.lastCall?.[0])).toContain('grain=hourly'))
  })
  it('navigates all four views without requesting new HTML documents', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Anomalies' }))
    expect(await screen.findByText('Test spike from API')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Forecast' }))
    expect(await screen.findByText('Illustrative values, not a trained model.')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /1 actual and 1 forecast intervals/ })).toBeInTheDocument()
    const forecastCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/forecast'))
    expect(String(forecastCall?.[0])).toContain('start=2009-06-08T00%3A00%3A00.000Z')
    await user.click(screen.getByRole('button', { name: 'Assistant' }))
    await user.type(screen.getByLabelText('Your question'), 'Why the spike?')
    await user.click(screen.getByRole('button', { name: /Send question/ }))
    expect(await screen.findByText(chat.answer)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Request weekly summary' }))
    await waitFor(() => expect(screen.getAllByText(chat.answer)).toHaveLength(2))
    const lastBody = JSON.parse(String(fetchMock.mock.lastCall?.[1]?.body))
    expect(lastBody.request_type).toBe('weekly_summary')
    expect(lastBody.message).toBeUndefined()
    expect(screen.getAllByText('No citations returned.')).toHaveLength(2)
  })
  it('shows loading, empty and recoverable errors while keeping filters and navigation', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...consumption, items: [], covered_start: null, covered_end: null }))
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading API data')
    expect(await screen.findByText(/No records in this window/)).toBeInTheDocument()
    fetchMock.mockRejectedValueOnce(new TypeError('Offline'))
    fireEvent.change(screen.getByLabelText('Consumption interval'), { target: { value: 'hourly' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Start FastAPI on port 8000')
    expect(screen.getByRole('navigation', { name: 'Energy views' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('12.34', { selector: '.primary strong' })).toBeInTheDocument()
  })
  it('aborts changed filters and ignores late responses even if fetch ignores abort', async () => {
    let resolveOld!: (response: Response) => void
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
    render(<App />)
    const oldSignal = fetchMock.mock.calls[0][1]?.signal
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2009-06-02' } })
    expect(await screen.findByText('12.34', { selector: '.primary strong' })).toBeInTheDocument()
    expect(oldSignal?.aborted).toBe(true)
    await act(async () => resolveOld(jsonResponse({ ...consumption, items: [{ ...consumption.items[0], energy_kwh: 999 }] })))
    expect(screen.queryByText('999.00', { selector: '.primary strong' })).not.toBeInTheDocument()
  })
  it('cancels assistant replies when the historical window changes', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Assistant' }))
    let resolveOld!: (response: Response) => void
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
    await user.click(screen.getByRole('button', { name: 'Request weekly summary' }))
    const signal = fetchMock.mock.lastCall?.[1]?.signal
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2009-06-02' } })
    expect(signal?.aborted).toBe(true)
    await act(async () => resolveOld(jsonResponse(chat)))
    expect(screen.queryByText(chat.answer)).not.toBeInTheDocument()
  })
  it('does not fetch with an invalid historical date selection', async () => {
    render(<App />)
    await screen.findByText('12.34', { selector: '.primary strong' })
    const calls = fetchMock.mock.calls.length
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2009-06-10' } })
    expect(screen.getByRole('alert')).toHaveTextContent('Choose valid historical dates')
    expect(fetchMock).toHaveBeenCalledTimes(calls)
    expect(screen.queryByText('12.34', { selector: '.primary strong' })).not.toBeInTheDocument()
  })
  it('uses the response demo flag rather than hard-coding a demo badge', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...consumption, is_demo: false }))
    render(<App />)
    await screen.findByText('12.34', { selector: '.primary strong' })
    expect(screen.queryByText('Demo data')).not.toBeInTheDocument()
  })
  it('keeps earlier assistant messages when a later request fails and can retry', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Assistant' }))
    await user.click(screen.getByRole('button', { name: 'Request weekly summary' }))
    await screen.findByText(chat.answer)
    fetchMock.mockRejectedValueOnce(new TypeError('Offline'))
    await user.click(screen.getByRole('button', { name: 'Request weekly summary' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the API')
    expect(screen.getByText(chat.answer)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry request' }))
    await waitFor(() => expect(screen.getAllByText(chat.answer)).toHaveLength(2))
  })
  it('preserves an unsent question when requesting a weekly summary', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Assistant' }))
    await user.type(screen.getByLabelText('Your question'), 'Why did consumption rise?')
    await user.click(screen.getByRole('button', { name: 'Request weekly summary' }))
    await screen.findByText(chat.answer)
    expect(screen.getByLabelText('Your question')).toHaveValue('Why did consumption rise?')
  })
})
