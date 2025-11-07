import React from 'react'
import Plot from './Plotly'

type Props = {
  year?: string
  event?: string
  mapData: any | null
  selectedTurn?: number
  onSelectTurn?: (t: number) => void
  title?: string
}

const TrackMap: React.FC<Props> = ({ mapData, selectedTurn, onSelectTurn, title }) => {
  const traces: any[] = []
  if (mapData?.track_map) {
    traces.push({
      x: mapData.track_map.X,
      y: mapData.track_map.Y,
      mode: 'lines',
      line: { color: 'white', width: 2 },
      name: 'Track',
      hoverinfo: 'skip'
    })
  }
  if (Array.isArray(mapData?.sectors)) {
    const colors = ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db']
    mapData.sectors.forEach((s: any, i: number) => {
      if (s?.X && s?.Y) traces.push({ x: s.X, y: s.Y, mode: 'lines', line: { color: colors[i % colors.length], width: 4 }, opacity: 0.35, name: `Sector ${i+1}`, hoverinfo: 'skip', showlegend: false })
    })
  }
  if (Array.isArray(mapData?.corners)) {
    const xs = mapData.corners.map((t: any) => t.X)
    const ys = mapData.corners.map((t: any) => t.Y)
    const labels = mapData.corners.map((t: any) => `T${t.Number}`)
    const nums = mapData.corners.map((t: any) => t.Number)
    traces.push({
      x: xs, y: ys, mode: 'markers+text', text: labels, textposition: 'top center',
      marker: { color: 'rgba(255,80,80,0.8)', size: 8 },
      name: 'Turns', customdata: nums
    })
    if (selectedTurn != null) {
      const i = nums.indexOf(selectedTurn)
      if (i >= 0) traces.push({ x: [xs[i]], y: [ys[i]], mode: 'markers+text', text: [labels[i]], textposition: 'top center', marker: { color: 'rgb(0,200,255)', size: 14, line: { color: 'white', width: 1.5 } }, name: `Selected T${selectedTurn}`, hoverinfo: 'text' })
    }
  }

  return (
    <Plot
      data={traces}
      onClick={(e) => {
        const p = e.points?.[0]
        const cd = p?.data?.customdata
        if (Array.isArray(cd)) {
          // pick nearest turn by index
          const idx = p.pointIndex ?? 0
          const t = cd[idx]
          if (typeof t === 'number') onSelectTurn?.(t)
        }
      }}
      layout={{
        title: `${title || 'Circuit'} Layout`,
        paper_bgcolor: '#111', plot_bgcolor: '#111',
        xaxis: { visible: false }, yaxis: { visible: false, scaleanchor: 'x', scaleratio: 1 },
        height: 600, margin: { l: 10, r: 10, t: 60, b: 10 }, legend: { orientation: 'h', y: -0.08, font: { color: '#ddd' } }, font: { color: '#ddd' }
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', height: '100%' }}
    />
  )
}

export default TrackMap
