import { useState } from 'react'
import { readPath } from '../api/client'
import type { ConsumptionResponse, ForecastResponse, WindowQuery } from '../api/types'
import { formatTime, toWindow, type DateSelection } from '../dates'
import { useApiRead } from '../hooks/useApiRead'
import { Coverage, DateFields, DemoBadge, RequestState } from './Common'
import { EnergyChart, EnergyTable } from './EnergyChart'

export function Forecast({ window }: { window: WindowQuery | null }) {
  // The historical filter supplies observations. Future targets have a separate
  // window because filtering June 1–7 against June 8 forecasts would be empty.
  const [targets, setTargets] = useState<DateSelection>({ from: '2009-06-08', through: '2009-06-08' })
  const targetWindow = toWindow(targets)
  const history = useApiRead<ConsumptionResponse>(window ? readPath('/consumption', window, 'hourly') : null)
  const forecast = useApiRead<ForecastResponse>(targetWindow ? readPath('/forecast', targetWindow) : null)
  const actual = history.data?.items ?? []
  const predicted = forecast.data?.items ?? []
  const unit = forecast.data?.units.energy_kwh ?? history.data?.units.energy_kwh ?? 'kWh'

  return <section aria-labelledby="forecast-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">An illustrative look ahead</p>
        <h2 id="forecast-title">Forecast</h2>
      </div>
      <DemoBadge show={!!(history.data?.is_demo || forecast.data?.is_demo)} />
    </div>

    <div className="panel toolbar">
      <DateFields label="Forecast target dates (UTC)" value={targets} onChange={setTargets} />
      <p>The fixture's next 24 hours are on June 8, 2009.</p>
    </div>

    {!targetWindow && <p className="notice error" role="alert">Choose valid forecast dates with From on or before Through.</p>}
    
    <h3 className="small-heading">Historical observations</h3>

    {window && <RequestState {...history} empty={history.data?.items.length === 0} />}

    <h3 className="small-heading">Forecast target window</h3>

    {targetWindow && <RequestState {...forecast} empty={forecast.data?.items.length === 0} />}

    {forecast.data && <div className="forecast-note">
      <strong>Origin: {formatTime(forecast.data.forecast_origin)} UTC</strong><p>Full target horizon: 
        {formatTime(forecast.data.target_start)} → {formatTime(forecast.data.target_end)} UTC (end exclusive).</p>
        <p>{forecast.data.note}</p></div>}

    {(actual.length > 0 || predicted.length > 0) && <div className="panel">
      <div className="chart-heading">
        <h3>Observed and illustrative energy</h3>
        <span>Hourly · {unit}</span>
      </div>

      <EnergyChart actual={actual} forecast={predicted} unit={unit} />
      <EnergyTable items={actual} unit={unit} label="Actual observations" />
      <EnergyTable items={predicted} unit={unit} label="Illustrative forecast targets" />
    </div>}
    
    {history.data && <div><h3 className="small-heading">Historical coverage</h3><Coverage data={history.data} /></div>}
    {forecast.data && <div><h3 className="small-heading">Forecast target coverage</h3><Coverage data={forecast.data} /></div>}
  </section>
}
