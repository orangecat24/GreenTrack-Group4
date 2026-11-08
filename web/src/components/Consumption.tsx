import { useState } from 'react'
import { readPath } from '../api/client'
import type { ConsumptionResponse, Grain, WindowQuery } from '../api/types'
import { useApiRead } from '../hooks/useApiRead'
import { Coverage, DemoBadge, RequestState } from './Common'
import { EnergyChart, EnergyTable } from './EnergyChart'

export function Consumption({ window }: { window: WindowQuery | null }) {
  // This local state changes only aggregation, not navigation or other tabs.
  const [grain, setGrain] = useState<Grain>('daily')
  const result = useApiRead<ConsumptionResponse>(window ? readPath('/consumption', window, grain) : null)
  const data = result.data
  const total = data?.items.reduce((sum, item) => sum + item.energy_kwh, 0) ?? 0
  const peak = data?.items.reduce((max, item) => Math.max(max, item.energy_kwh), 0) ?? 0
  const unit = data?.units.energy_kwh ?? 'kWh'

  return <section aria-labelledby="consumption-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">Understand your usage</p>
        <h2 id="consumption-title">Consumption</h2>
      </div>
      <DemoBadge show={data?.is_demo ?? false} />
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
          <span>Total consumption</span>
          <strong>{total.toFixed(2)} <small>{unit}</small></strong>
          <p>Sum of returned intervals</p>
        </article>

        <article className="stat-card">
          <span>Highest {data.grain === 'daily' ? 'day' : 'hour'}</span>
          <strong>{peak.toFixed(2)} <small>{unit}</small></strong>
          <p>Within this selection</p>
        </article>

        <article className="stat-card">
          <span>Intervals returned</span><strong>{data.items.length}</strong>
          <p>{data.grain === 'daily' ? 'Complete UTC days' : 'Hourly energy readings'}</p>
        </article>

      </div>

      <div className="panel">
        <div className="chart-heading">
          <h3>Consumption over time</h3><span>{data.grain} · {unit}</span>
        </div>

        <EnergyChart actual={data.items} unit={unit} />
        <EnergyTable items={data.items} unit={unit} label="Actual consumption data" />

      </div>

    </>}

    {data && <Coverage data={data} />}
    
  </section>
}
