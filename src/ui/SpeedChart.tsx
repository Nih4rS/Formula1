import { FC, useMemo } from 'react'
import Plot from './Plotly'
import { LapTelemetry } from '../utils/data'

type Props = {
  refLap: LapTelemetry | null
  cmpLaps: Record<string, LapTelemetry>
}

const SpeedChart: FC<Props> = ({ refLap, cmpLaps }) => {
  const traces = useMemo(() => {
    const out: any[] = []
    if (refLap) out.push({ x: refLap.distance_m, y: refLap.speed_kph, mode: 'lines', name: `${refLap.driver || 'REF'}`, line: { width: 2 } })
    Object.values(cmpLaps).forEach((lap) => {
      if (lap) out.push({ x: lap.distance_m, y: lap.speed_kph, mode: 'lines', name: `${lap.driver || 'CMP'}`, line: { width: 1.5, dash: 'dot' } })
    })
    return out
  }, [refLap, cmpLaps])

  return (
    <Plot
      data={traces}
      layout={{ title: 'Speed vs Distance', paper_bgcolor: '#111', plot_bgcolor: '#111', xaxis: { title: 'Distance (m)' }, yaxis: { title: 'Speed (kph)' }, height: 280, margin: { l: 50, r: 10, t: 40, b: 40 }, font: { color: '#ddd' }, legend: { orientation: 'h' } }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', height: '100%' }}
    />
  )
}

export default SpeedChart
