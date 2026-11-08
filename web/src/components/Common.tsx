import type { DateSelection } from '../dates'
import { formatTime } from '../dates'
import type { ReadResponse } from '../api/types'

export function DemoBadge({ show }: { show: boolean }) {
  return show ? <span className="badge"><span aria-hidden="true">●</span> Demo data</span> : null
}

/** Props are inputs from the parent, similar to a typed Razor partial model. */
export function DateFields({ value, onChange, label }: {
  value: DateSelection; onChange: (value: DateSelection) => void; label: string
}) {
  return <fieldset className="date-fields">
    <legend>{label}</legend>
    <label>From<input type="date" required value={value.from} onChange={(event) => onChange({ ...value, from: event.target.value })} /></label>
    <span className="date-arrow" aria-hidden="true">→</span>
    <label>Through <small>(inclusive)</small><input type="date" required value={value.through} onChange={(event) => onChange({ ...value, through: event.target.value })} /></label>
  </fieldset>
}

export function RequestState({ loading, error, empty, retry }: {
  loading: boolean; error: string | null; empty: boolean; retry: () => void
}) {
  if (loading) return <div className="notice" role="status"><span className="spinner" /> Loading API data…</div>
  if (error) return <div className="notice error" role="alert"><div><strong>We couldn’t load this view.</strong><p>{error}</p></div><button onClick={retry}>Try again</button></div>
  if (empty) return <div className="notice" role="status">No records in this window. Try June 1–7, 2009 for history or June 8 for forecast targets.</div>
  return null
}

export function Coverage({ data }: { data: ReadResponse<unknown> }) {
  return <div className="coverage">
    <p><strong>Requested:</strong> {formatTime(data.requested_start)} → {formatTime(data.requested_end)} UTC <span>(end exclusive)</span></p>
    <p><strong>Covered:</strong> {data.covered_start && data.covered_end ? `${formatTime(data.covered_start)} → ${formatTime(data.covered_end)} UTC` : 'No returned buckets'}</p>
    <p>{data.timezone_note}</p>
  </div>
}
