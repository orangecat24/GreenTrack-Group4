import { readPath } from '../api/client'
import type { AnomalyPoint, ReadResponse, WindowQuery } from '../api/types'
import { formatTime } from '../dates'
import { useApiRead } from '../hooks/useApiRead'
import { Coverage, DemoBadge, RequestState } from './Common'

export function Anomalies({ window }: { window: WindowQuery | null }) {
  const result = useApiRead<ReadResponse<AnomalyPoint>>(window ? readPath('/anomalies', window) : null)
  const data = result.data

  return <section aria-labelledby="anomalies-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">Look a little closer</p>
        <h2 id="anomalies-title">Anomalies</h2>
      </div>
      
      <DemoBadge show={data?.is_demo ?? false} />
    </div>

    <p className="section-intro">Review unusual hours alongside their expected consumption. Demo scores are fixture values, not model detections.</p>
    
    {window && <RequestState {...result} empty={data?.items.length === 0} />}
    {data && data.items.length > 0 && <div className="panel table-scroll">
      <table>
        <caption>{data.items.length} synthetic anomaly records · UTC</caption>
        
        <thead>
          <tr>
            <th>Hour starting</th>
            <th>Observed ({data.units.observed_kwh})</th>
            <th>Expected ({data.units.expected_kwh})</th>
            <th>Score ({data.units.score})</th>
            <th>Why it appears</th>
          </tr>
        </thead>

        <tbody>{data.items.map((item) => <tr key={item.timestamp}>
            <td>
              <strong>{formatTime(item.timestamp)}</strong>
              <span className="cell-detail">Ends {formatTime(item.interval_end)}</span>
            </td>

            <td className="anomaly-value">{item.observed_kwh.toFixed(2)}</td>
            <td>{item.expected_kwh.toFixed(2)}</td>
            <td>{item.score.toFixed(2)}</td>
            <td>{item.reason}</td>
          </tr>)}
        </tbody>

      </table>

    </div>}

    {data && <Coverage data={data} />}

  </section>
}
