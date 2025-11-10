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

const TelemetryExplorer: React.FC = () => {
  const [years, setYears] = useState<string[]>([])
  const [events, setEvents] = useState<string[]>([])
  const [sessions, setSessions] = useState<string[]>([])
  const [drivers, setDrivers] = useState<string[]>([])
  const [sel, setSel] = useState<Selection>({ compares: [] })

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

  useEffect(() => {
    if (!sel.year && years.length) setSel((s: Selection) => ({ ...s, year: years[years.length - 1] }))
  }, [years, sel.year])

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
    Promise.all(sel.compares.map((d: string) => loadLap(sel.year!, sel.event!, sel.session!, d).then(v => (next[d] = v)).catch(() => {})))
      .then(() => setCmpLaps(next))
  }, [sel.year, sel.event, sel.session, sel.compares.join('|')])

  const eventTitle = useMemo(() => sel.event ? sel.event.replace(/-/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) : '', [sel.event])

  return (
    <div className="telemetry-shell">
      <div className="telemetry-header">
        <h2>Lap Telemetry Explorer</h2>
        <p>Compare best laps and dive into circuit traces with historic telemetry pulled from the repository dataset.</p>
      </div>

      <div className="telemetry-controls">
        <div>
          <label>Season
            <select value={sel.year || ''} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSel((s: Selection) => ({ ...s, year: e.target.value, event: undefined, session: undefined, ref: undefined, compares: [] }))}>
              {years.map((y: string) => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Grand Prix
            <select value={sel.event || ''} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSel((s: Selection) => ({ ...s, event: e.target.value, session: undefined, ref: undefined, compares: [] }))}>
              <option value=""></option>
              {events.map((ev: string) => <option key={ev} value={ev}>{ev.replace(/-/g, ' ')}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Session
            <select value={sel.session || ''} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSel((s: Selection) => ({ ...s, session: e.target.value, ref: undefined, compares: [] }))}>
              <option value=""></option>
              {sessions.map((ss: string) => <option key={ss} value={ss}>{ss}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Reference Driver
            <select value={sel.ref || ''} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSel((s: Selection) => ({ ...s, ref: e.target.value }))}>
              <option value=""></option>
              {drivers.map((d: string) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        </div>
        <div>
          <label>Compare Drivers
            <select multiple size={Math.min(6, Math.max(2, drivers.length))}
                    value={sel.compares}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                      const opts = Array.from(e.target.selectedOptions).map(o => o.value)
                      setSel((s: Selection) => ({ ...s, compares: opts.filter(d => d !== s.ref) }))
                    }}>
              {drivers.filter((d: string) => d !== sel.ref).map((d: string) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="telemetry-grid">
        <div className="telemetry-map">
          <TrackMap year={sel.year} event={sel.event} mapData={mapData} selectedTurn={sel.selectedTurn}
                    onSelectTurn={(t) => setSel(s => ({ ...s, selectedTurn: t }))}
                    title={eventTitle} />
        </div>
        <div className="telemetry-charts">
          <SpeedChart refLap={refLap} cmpLaps={cmpLaps} />
          <DeltaChart refLap={refLap} cmpLaps={cmpLaps} />
        </div>
      </div>
    </div>
  )
}

export default TelemetryExplorer
