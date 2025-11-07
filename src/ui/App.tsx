import React, { useEffect, useMemo, useState } from 'react'
import { listYears, listEvents, listSessions, listDrivers, loadLap, loadMapData } from '../utils/data'
import TrackMap from './TrackMap'
import SpeedChart from './SpeedChart'
import DeltaChart from './DeltaChart'

type Selection = {
  year?: string
  event?: string
  session?: string
  ref?: string
  compares: string[]
  selectedTurn?: number
}

const App: React.FC = () => {
  const [years, setYears] = useState<string[]>([])
  const [events, setEvents] = useState<string[]>([])
  const [sessions, setSessions] = useState<string[]>([])
  const [drivers, setDrivers] = useState<string[]>([])
  const [sel, setSel] = useState<Selection>({ compares: [] })

  // Load cascading lists
  useEffect(() => { listYears().then(setYears).catch(() => setYears([])) }, [])
  useEffect(() => {
    if (!sel.year) return
    listEvents(sel.year).then(setEvents).catch(() => setEvents([]))
  }, [sel.year])
  useEffect(() => {
    if (!sel.year || !sel.event) return
    listSessions(sel.year, sel.event).then(setSessions).catch(() => setSessions([]))
  }, [sel.year, sel.event])
  useEffect(() => {
    if (!sel.year || !sel.event || !sel.session) return
    listDrivers(sel.year, sel.event, sel.session).then(setDrivers).catch(() => setDrivers([]))
  }, [sel.year, sel.event, sel.session])

  // Default to latest year
  useEffect(() => {
    if (!sel.year && years.length) setSel(s => ({ ...s, year: years[years.length - 1] }))
  }, [years])

  const [mapData, setMapData] = useState<any | null>(null)
  useEffect(() => {
    if (sel.year && sel.event) {
      loadMapData(sel.year, sel.event).then(setMapData).catch(() => setMapData(null))
    } else {
      setMapData(null)
    }
  }, [sel.year, sel.event])

  const [refLap, setRefLap] = useState<any | null>(null)
  const [cmpLaps, setCmpLaps] = useState<Record<string, any>>({})

  useEffect(() => {
    setRefLap(null); setCmpLaps({})
    if (sel.year && sel.event && sel.session && sel.ref) {
      loadLap(sel.year, sel.event, sel.session, sel.ref).then(setRefLap).catch(() => setRefLap(null))
    }
  }, [sel.year, sel.event, sel.session, sel.ref])

  useEffect(() => {
    if (!sel.year || !sel.event || !sel.session) return
    const next: Record<string, any> = {}
    Promise.all(sel.compares.map(d => loadLap(sel.year!, sel.event!, sel.session!, d).then(v => (next[d] = v)).catch(() => {})))
      .then(() => setCmpLaps(next))
  }, [sel.year, sel.event, sel.session, sel.compares.join('|')])

  const eventTitle = useMemo(() => sel.event ? sel.event.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '', [sel.event])

  return (
    <div style={{ padding: 16, color: '#eee', background: '#111', minHeight: '100vh' }}>
      <h1 style={{ marginTop: 0 }}>F1 Lap Explorer</h1>
      <p style={{ marginTop: -10, opacity: 0.8 }}>Static viewer for best-lap telemetry and circuit turn map. Data auto-refreshes weekly via GitHub Actions.</p>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
        <div>
          <label>Year<br/>
            <select value={sel.year || ''} onChange={e => setSel(s => ({ ...s, year: e.target.value, event: undefined, session: undefined, ref: undefined, compares: [] }))}>
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Grand Prix<br/>
            <select value={sel.event || ''} onChange={e => setSel(s => ({ ...s, event: e.target.value, session: undefined, ref: undefined, compares: [] }))}>
              <option value=""></option>
              {events.map(ev => <option key={ev} value={ev}>{ev.replace(/-/g,' ')}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Session<br/>
            <select value={sel.session || ''} onChange={e => setSel(s => ({ ...s, session: e.target.value, ref: undefined, compares: [] }))}>
              <option value=""></option>
              {sessions.map(ss => <option key={ss} value={ss}>{ss}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Reference Driver<br/>
            <select value={sel.ref || ''} onChange={e => setSel(s => ({ ...s, ref: e.target.value }))}>
              <option value=""></option>
              {drivers.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Compare Drivers<br/>
            <select multiple size={Math.min(6, Math.max(2, drivers.length))}
                    value={sel.compares}
                    onChange={e => {
                      const opts = Array.from(e.target.selectedOptions).map(o => o.value)
                      setSel(s => ({ ...s, compares: opts.filter(d => d !== s.ref) }))
                    }}>
              {drivers.filter(d => d !== sel.ref).map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 16, marginTop: 16 }}>
        <div>
          <TrackMap year={sel.year} event={sel.event} mapData={mapData} selectedTurn={sel.selectedTurn}
                    onSelectTurn={(t) => setSel(s => ({ ...s, selectedTurn: t }))}
                    title={eventTitle} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <SpeedChart refLap={refLap} cmpLaps={cmpLaps} />
          <DeltaChart refLap={refLap} cmpLaps={cmpLaps} />
        </div>
      </div>
    </div>
  )
}

export default App

