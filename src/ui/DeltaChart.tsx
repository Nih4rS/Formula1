import { FC, useMemo } from 'react'
import Plot from './Plotly'
import { LapTelemetry } from '../utils/data'

function lapDelta(refDist: number[], refCum: number[], cmpDist: number[], cmpCum: number[]) {
  const x: number[] = []
  const y: number[] = []
  let j = 0
  for (let i = 0; i < refDist.length; i++) {
    const d = refDist[i] ?? 0
    while (j + 1 < cmpDist.length && (cmpDist[j + 1] ?? 0) < d) j++
    x.push(d)
    y.push((refCum[i] ?? 0) - (cmpCum[j] ?? 0))
  }
  return { x, y }
}

type Props = {
  refLap: LapTelemetry | null
  cmpLaps: Record<string, LapTelemetry>
}

const DeltaChart: FC<Props> = ({ refLap, cmpLaps }) => {
  const traces = useMemo(() => {
    const out: any[] = []
    if (!refLap) return out
    Object.values(cmpLaps).forEach((lap) => {
      if (!lap) return
      const { x, y } = lapDelta(refLap.distance_m || [], refLap.cum_lap_time_s || [], lap.distance_m || [], lap.cum_lap_time_s || [])
      out.push({ x, y, mode: 'lines', name: `${lap.driver || 'CMP'}` })
    })
    return out
  }, [refLap, cmpLaps])

  return (
    <Plot
      data={traces}
      layout={{ title: 'Lap Delta (ref - compare)', paper_bgcolor: '#111', plot_bgcolor: '#111', xaxis: { title: 'Distance (m)' }, yaxis: { title: 'Delta (s)' }, height: 280, margin: { l: 50, r: 10, t: 40, b: 40 }, font: { color: '#ddd' }, legend: { orientation: 'h' } }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', height: '100%' }}
    />
  )
}

export default DeltaChart
