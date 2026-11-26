import { useState } from 'react'
import { readPath } from '../api/client'
import type { ConsumptionResponse, Grain, WindowQuery } from '../api/types'
import { useApiRead } from '../hooks/useApiRead'
import { Coverage, Provenance, RequestState } from './Common'
import { consumptionSummary } from '../consumptionSummary'
import { EnergyChart, EnergyTable } from './EnergyChart'

export function Consumption({ window }: { window: WindowQuery | null }) {
  // This local state changes only aggregation, not navigation or other tabs.
  const [grain, setGrain] = useState<Grain>('daily')
  const result = useApiRead<ConsumptionResponse>(window ? readPath('/consumption', window, grain) : null)
  const data = result.data
  const summary = data ? consumptionSummary(data) : null
  const unit = data?.units.energy_kwh ?? 'kWh'

  return <section aria-labelledby="consumption-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">Understand your usage</p>
        <h2 id="consumption-title">Consumption</h2>
      </div>
      <Provenance data={data} />
    </div>

    <div className="panel toolbar">
      <p>Energy across the selected historical period.</p>
      <label>Interval
        <select aria-label="Consumption interval" value={grain} onChange={(event) => setGrain(event.target.value as Grain)}>
          <option value="daily">Daily</option>
          <option value="hourly">Hourly</option>
        </select>
      </label>
    </div>

    {window && <RequestState {...result} empty={data?.items.length === 0} />}

    {data && data.items.length > 0 && <>

      <div className="stats-grid">

        <article className="stat-card primary">
          <span>{summary?.partial ? 'Observed energy' : 'Total consumption'}</span>
          <strong>{summary?.total == null ? 'No measured energy' : summary.total.toFixed(2)} <small>{summary?.total != null && unit}</small></strong>
          <p>{summary?.partial ? 'Partial coverage; this is not a complete-period total.' : 'Sum of returned intervals'}</p>
        </article>

        <article className="stat-card">
          <span>Highest {data.grain === 'daily' ? 'day' : 'hour'}</span>
          <strong>{summary?.peak == null ? 'Unavailable' : summary.peak.toFixed(2)} <small>{summary?.peak != null && unit}</small></strong>
          <p>Within this selection</p>
        </article>

        <article className="stat-card">
          <span>Intervals returned</span><strong>{data.items.length}</strong>
          <p>{data.grain === 'daily' ? 'Calendar-day buckets' : 'Hourly energy buckets'}</p>
        </article>

      </div>

      <div className="panel">
        <div className="chart-heading">
          <h3>Consumption over time</h3><span>{data.grain} · {unit}</span>
        </div>

        <EnergyChart actual={data.items} unit={unit} />
        <EnergyTable items={data.items} unit={unit} label={data.is_demo ? 'Synthetic consumption data' : 'Historical consumption data'} />

      </div>

    </>}

    {data && summary && <div className="notice" role="note">
      <p>{summary.missing} missing periods; {summary.incomplete} incomplete intervals; {summary.nulls} null energy values.</p>
      {data.data_source === 'gold' ? <p>{summary.minutes} / {summary.expectedMinutes} observed minutes. {summary.unknown > 0 && `${summary.unknown} intervals have unknown quality.`}</p>
        : <p>Observed-minute quality is not applicable to synthetic fixtures.</p>}
    </div>}
    {data && <Coverage data={data} />}
    
  </section>
}
