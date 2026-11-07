import type { WindowQuery } from './api/types'

export interface DateSelection { from: string; through: string }

/** Inputs show inclusive calendar dates; the API wants an exclusive end instant. */
export function toWindow(selection: DateSelection): WindowQuery | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(selection.from) || !/^\d{4}-\d{2}-\d{2}$/.test(selection.through)) return null
  const start = new Date(`${selection.from}T00:00:00Z`)
  const lastDay = new Date(`${selection.through}T00:00:00Z`)
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(lastDay.getTime()) || start > lastDay) return null
  if (start.toISOString().slice(0, 10) !== selection.from || lastDay.toISOString().slice(0, 10) !== selection.through) return null
  const end = new Date(lastDay)
  // UTC arithmetic prevents the browser's timezone or daylight saving from
  // shifting a selected calendar day into an API request for the wrong date.
  end.setUTCDate(end.getUTCDate() + 1)
  return { household_id: 'household-1', start: start.toISOString(), end: end.toISOString() }
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'UTC', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(iso))
}
