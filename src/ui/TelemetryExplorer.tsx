import { ChangeEvent, FC, useEffect, useMemo, useState } from 'react'
import TrackMap from './TrackMap'
import SpeedChart from './SpeedChart'
import DeltaChart from './DeltaChart'
import {
  LapTelemetry,
  TrackMapPayload,
  listDrivers,
  listEvents,
  listSessions,
  listYears,
  loadLap,
  loadMapData
} from '../utils/data'

const isAbortError = (error: unknown): boolean =>
  typeof error === 'object' && error !== null && 'name' in error && (error as { name?: unknown }).name === 'AbortError'

const TelemetryExplorer: FC = () => {
  const [years, setYears] = useState<string[]>([])
  const [events, setEvents] = useState<string[]>([])
  const [sessions, setSessions] = useState<string[]>([])
  const [drivers, setDrivers] = useState<string[]>([])

  const [season, setSeason] = useState<string | undefined>()
  const [grandPrix, setGrandPrix] = useState<string | undefined>()
  const [sessionCode, setSessionCode] = useState<string | undefined>()
  const [referenceDriver, setReferenceDriver] = useState<string | undefined>()
  const [comparisonDrivers, setComparisonDrivers] = useState<string[]>([])
  const [selectedTurn, setSelectedTurn] = useState<number | undefined>()

  const [mapData, setMapData] = useState<TrackMapPayload | null>(null)
  const [mapLoading, setMapLoading] = useState<boolean>(false)
  const [mapError, setMapError] = useState<string | null>(null)

  const [referenceLap, setReferenceLap] = useState<LapTelemetry | null>(null)
  const [comparisonLaps, setComparisonLaps] = useState<Record<string, LapTelemetry>>({})
  const [referenceLapLoading, setReferenceLapLoading] = useState<boolean>(false)
  const [comparisonLapLoading, setComparisonLapLoading] = useState<boolean>(false)
  const [referenceLapError, setReferenceLapError] = useState<string | null>(null)
  const [comparisonLapWarning, setComparisonLapWarning] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listYears(controller.signal)
      .then((data) => setYears(data))
      .catch((error) => {
        if (!isAbortError(error)) setYears([])
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!years.length) return
    setSeason((prev) => prev && years.includes(prev) ? prev : years[years.length - 1])
  }, [years])

  useEffect(() => {
    setGrandPrix(undefined)
    setSessionCode(undefined)
    setReferenceDriver(undefined)
    setComparisonDrivers([])
    setSelectedTurn(undefined)
  }, [season])

  useEffect(() => {
    setSessionCode(undefined)
    setReferenceDriver(undefined)
    setComparisonDrivers([])
    setSelectedTurn(undefined)
  }, [grandPrix])

  useEffect(() => {
    setReferenceDriver(undefined)
    setComparisonDrivers([])
  }, [sessionCode])

  useEffect(() => {
    if (!season) {
      setEvents([])
      return
    }
    const controller = new AbortController()
    setEvents([])
    listEvents(season, controller.signal)
      .then((data) => setEvents(data))
      .catch((error) => {
        if (!isAbortError(error)) setEvents([])
      })
    return () => controller.abort()
  }, [season])

  useEffect(() => {
    if (!season || !grandPrix) {
      setSessions([])
      return
    }
    const controller = new AbortController()
    setSessions([])
    listSessions(season, grandPrix, controller.signal)
      .then((data) => setSessions(data))
      .catch((error) => {
        if (!isAbortError(error)) setSessions([])
      })
    return () => controller.abort()
  }, [season, grandPrix])

  useEffect(() => {
    if (!season || !grandPrix || !sessionCode) {
      setDrivers([])
      return
    }
    const controller = new AbortController()
    setDrivers([])
    listDrivers(season, grandPrix, sessionCode, controller.signal)
      .then((data) => setDrivers(data))
      .catch((error) => {
        if (!isAbortError(error)) setDrivers([])
      })
    return () => controller.abort()
  }, [season, grandPrix, sessionCode])

  useEffect(() => {
    if (!drivers.length) {
      setReferenceDriver(undefined)
      return
    }
    setReferenceDriver((prev) => (prev && drivers.includes(prev) ? prev : drivers[0]))
  }, [drivers])

  useEffect(() => {
    if (!referenceDriver) return
    setComparisonDrivers((prev) => prev.filter((driver) => driver !== referenceDriver))
  }, [referenceDriver])

  useEffect(() => {
    setComparisonDrivers((prev) => prev.filter((driver) => drivers.includes(driver)))
  }, [drivers])

  useEffect(() => {
    if (!season || !grandPrix) {
      setMapData(null)
      setMapError(null)
      return
    }
    const controller = new AbortController()
    setMapLoading(true)
    setMapError(null)
    setMapData(null)
    loadMapData(season, grandPrix, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        setMapData(data)
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setMapData(null)
        setMapError('Unable to load circuit map for the selected round.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setMapLoading(false)
      })
    return () => controller.abort()
  }, [season, grandPrix])

  useEffect(() => {
    if (!season || !grandPrix || !sessionCode || !referenceDriver) {
      setReferenceLap(null)
      setReferenceLapError(null)
      setReferenceLapLoading(false)
      return
    }
    const controller = new AbortController()
    setReferenceLap(null)
    setReferenceLapError(null)
    setReferenceLapLoading(true)
    loadLap(season, grandPrix, sessionCode, referenceDriver, controller.signal)
      .then((lap) => {
        if (controller.signal.aborted) return
        setReferenceLap(lap)
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setReferenceLap(null)
        setReferenceLapError('Reference lap telemetry is unavailable for the selected driver.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setReferenceLapLoading(false)
      })
    return () => controller.abort()
  }, [season, grandPrix, sessionCode, referenceDriver])

  useEffect(() => {
    if (!season || !grandPrix || !sessionCode || comparisonDrivers.length === 0) {
      setComparisonLaps({})
      setComparisonLapWarning(null)
      setComparisonLapLoading(false)
      return
    }
    const controller = new AbortController()
    setComparisonLapWarning(null)
    setComparisonLapLoading(true)
    const requests = comparisonDrivers.map(async (driver) => {
      try {
        const lap = await loadLap(season, grandPrix, sessionCode, driver, controller.signal)
        return { driver, lap }
      } catch (error) {
        throw { driver, error }
      }
    })
    Promise.allSettled(requests)
      .then((results) => {
        if (controller.signal.aborted) return
        const next: Record<string, LapTelemetry> = {}
        const missing: string[] = []
        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            const { driver, lap } = result.value
            if (driver !== referenceDriver) next[driver] = lap
          } else {
            const failure = result.reason as { driver?: string; error?: unknown }
            if (!isAbortError(failure?.error)) {
              missing.push(failure?.driver ?? 'Unknown')
            }
          }
        })
        setComparisonLaps(next)
        setComparisonLapWarning(missing.length ? `Missing telemetry for: ${missing.join(', ')}` : null)
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setComparisonLaps({})
        setComparisonLapWarning('Unable to load comparison telemetry.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setComparisonLapLoading(false)
      })
    return () => controller.abort()
  }, [season, grandPrix, sessionCode, comparisonDrivers, referenceDriver])

  const comparisonOptions = useMemo(
    () => drivers.filter((driver) => driver !== referenceDriver),
    [drivers, referenceDriver]
  )

  const comparisonSize = useMemo(
    () => Math.min(6, Math.max(2, comparisonOptions.length || 2)),
    [comparisonOptions.length]
  )

  const eventTitle = useMemo(() => {
    if (!grandPrix) return undefined
    const spaced = grandPrix.replace(/-/g, ' ')
    return spaced.replace(/\b\w/g, (char) => char.toUpperCase())
  }, [grandPrix])

  const handleSeasonChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSeason(event.target.value || undefined)
  }

  const handleEventChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setGrandPrix(event.target.value || undefined)
  }

  const handleSessionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSessionCode(event.target.value || undefined)
  }

  const handleReferenceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setReferenceDriver(event.target.value || undefined)
  }

  const handleComparisonChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const unique = Array.from(new Set(Array.from(event.target.selectedOptions).map((option) => option.value)))
    setComparisonDrivers(unique.filter((driver) => driver && driver !== referenceDriver))
  }

  return (
    <div className="telemetry-shell">
      <div className="telemetry-header">
        <h2>Lap Telemetry Explorer</h2>
        <p>Compare best laps, inspect circuit traces, and drill into speed profiles across seasons.</p>
      </div>

      <div className="telemetry-controls">
        <label>
          Season
          <select value={season || ''} onChange={handleSeasonChange} disabled={!years.length}>
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>

        <label>
          Grand Prix
          <select value={grandPrix || ''} onChange={handleEventChange} disabled={!events.length}>
            <option value=""></option>
            {events.map((eventSlug) => (
              <option key={eventSlug} value={eventSlug}>{eventSlug.replace(/-/g, ' ')}</option>
            ))}
          </select>
        </label>

        <label>
          Session
          <select value={sessionCode || ''} onChange={handleSessionChange} disabled={!sessions.length}>
            <option value=""></option>
            {sessions.map((code) => (
              <option key={code} value={code}>{code}</option>
            ))}
          </select>
        </label>

        <label>
          Reference Driver
          <select value={referenceDriver || ''} onChange={handleReferenceChange} disabled={!drivers.length}>
            <option value=""></option>
            {drivers.map((driver) => (
              <option key={driver} value={driver}>{driver}</option>
            ))}
          </select>
        </label>

        <label>
          Compare Drivers
          <select
            multiple
            size={comparisonSize}
            value={comparisonDrivers}
            onChange={handleComparisonChange}
            disabled={!comparisonOptions.length}
          >
            {comparisonOptions.map((driver) => (
              <option key={driver} value={driver}>{driver}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="telemetry-grid">
        <div className="telemetry-map">
          {mapLoading ? (
            <div className="telemetry-placeholder">
              <div className="loading-spinner" aria-hidden />
              <p>Loading circuit data...</p>
            </div>
          ) : (
            <TrackMap
              year={season}
              event={grandPrix}
              mapData={mapData}
              selectedTurn={selectedTurn}
              onSelectTurn={setSelectedTurn}
              title={eventTitle}
            />
          )}
          {mapError ? <div className="telemetry-alert telemetry-alert--warning">{mapError}</div> : null}
        </div>
        <div className="telemetry-charts">
          {referenceLapError ? <div className="telemetry-alert telemetry-alert--warning">{referenceLapError}</div> : null}
          {comparisonLapWarning ? <div className="telemetry-alert telemetry-alert--info">{comparisonLapWarning}</div> : null}

          {referenceLapLoading ? (
            <div className="telemetry-placeholder">
              <div className="loading-spinner" aria-hidden />
              <p>Loading reference telemetry...</p>
            </div>
          ) : referenceLap ? (
            <>
              <SpeedChart refLap={referenceLap} cmpLaps={comparisonLaps} />
              {comparisonLapLoading ? (
                <div className="telemetry-placeholder">
                  <div className="loading-spinner" aria-hidden />
                  <p>Loading comparison telemetry...</p>
                </div>
              ) : (
                <DeltaChart refLap={referenceLap} cmpLaps={comparisonLaps} />
              )}
            </>
          ) : (
            <div className="telemetry-placeholder">
              <p>Select a session and reference driver to display telemetry.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TelemetryExplorer
