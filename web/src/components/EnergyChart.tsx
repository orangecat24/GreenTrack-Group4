import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ConsumptionPoint, ForecastPoint } from '../api/types'
import { formatTime } from '../dates'
import { chartRows } from '../chartData'

export function EnergyChart({ actual, forecast = [], unit }: {
  actual: ConsumptionPoint[]; forecast?: ForecastPoint[]; unit: string
}) {
  const rows = chartRows(actual, forecast)
  return <div className="chart" role="img" aria-label={`Energy chart in ${unit}: ${actual.length} actual and ${forecast.length} forecast intervals. Values are available in the data table.`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 700, height: 300 }}>
      <LineChart data={rows} margin={{ top: 15, right: 20, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e0e8e1" />
        <XAxis dataKey="timestamp" type="number" domain={['dataMin', 'dataMax']} scale="time" tickFormatter={(value: number) => formatTime(new Date(value).toISOString())} minTickGap={45} tick={{ fontSize: 11 }} />
        <YAxis unit={` ${unit}`} width={75} tick={{ fontSize: 11 }} />
        <Tooltip labelFormatter={(value) => `${formatTime(new Date(Number(value)).toISOString())} UTC`} formatter={(value, name) => [`${Number(value).toFixed(2)} ${unit}`, name]} />
        <Legend />
        {actual.length > 0 && <Line name="Actual consumption" dataKey="actual" stroke="#27634b" strokeWidth={2.5} dot={rows.length < 15} connectNulls={false} isAnimationActive={false} />}
        {forecast.length > 0 && <Line name="Illustrative forecast" dataKey="forecast" stroke="#bc7737" strokeDasharray="6 4" strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false} />}
      </LineChart>
    </ResponsiveContainer>
  </div>
}

export function EnergyTable({ items, unit, label }: { items: ConsumptionPoint[]; unit: string; label: string }) {
  return <details className="data-details"><summary>{label} · {items.length} intervals</summary>
    <div className="table-scroll"><table><caption>{label} (UTC, interval end exclusive)</caption><thead><tr><th>Interval start</th><th>Interval end</th><th>Energy ({unit})</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.timestamp}><td>{formatTime(item.timestamp)}</td><td>{formatTime(item.interval_end)}</td><td>{item.energy_kwh.toFixed(2)}</td></tr>)}</tbody></table></div>
  </details>
}
