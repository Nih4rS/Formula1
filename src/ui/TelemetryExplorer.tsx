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

const sessionLabels: Record<string, string> = {
  FP1: 'Free Practice 1',
  FP2: 'Free Practice 2',
  FP3: 'Free Practice 3',
  SQ: 'Sprint Qualifying',
  SS: 'Sprint',
  Q: 'Qualifying',
  R: 'Race'
}

type SessionLeaderboardRow = {
  driver: string
  lapTimeSeconds: number
  lapNumber?: number
  topSpeedKph?: number
}

const formatLapTime = (seconds?: number): string => {
  if (seconds === undefined || !Number.isFinite(seconds)) return '--'
  const total = seconds
  const minutes = Math.floor(total / 60)
  const remainder = total - minutes * 60
  const remainderText = remainder.toFixed(3).padStart(6, '0')
  return `${minutes}:${remainderText}`
}

const formatGap = (gapSeconds?: number): string => {
  if (gapSeconds === undefined || !Number.isFinite(gapSeconds) || gapSeconds <= 0.0005) return 'Leader'
  return `+${gapSeconds.toFixed(3)}s`
}

const formatSpeed = (speed?: number): string => {
  if (speed === undefined || !Number.isFinite(speed)) return '--'
  return `${Math.round(speed)} kph`
}

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

  const [leaderboard, setLeaderboard] = useState<SessionLeaderboardRow[]>([])
  const [leaderboardLoading, setLeaderboardLoading] = useState<boolean>(false)
  const [leaderboardError, setLeaderboardError] = useState<string | null>(null)
  const [leaderboardWarning, setLeaderboardWarning] = useState<string | null>(null)

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
    if (!season || !grandPrix || !sessionCode) {
      setLeaderboard([])
      setLeaderboardLoading(false)
      setLeaderboardError(null)
      setLeaderboardWarning(null)
      return
    }
    if (!drivers.length) {
      setLeaderboard([])
      setLeaderboardLoading(false)
      setLeaderboardError(null)
      setLeaderboardWarning(null)
      return
    }
    const controller = new AbortController()
    setLeaderboardLoading(true)
    setLeaderboardError(null)
    setLeaderboardWarning(null)
    const requests = drivers.map(async (driver) => {
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
        const rows: SessionLeaderboardRow[] = []
        const missing: string[] = []
        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            const { driver, lap } = result.value
            const lapTimes = Array.isArray(lap.cum_lap_time_s) ? lap.cum_lap_time_s : []
            const lapTime = lapTimes.length ? lapTimes[lapTimes.length - 1] : undefined
            if (typeof lapTime !== 'number' || !Number.isFinite(lapTime)) {
              missing.push(driver)
              return
            }
            const speeds = Array.isArray(lap.speed_kph) ? lap.speed_kph : []
            let topSpeed = 0
            for (const value of speeds) {
              if (typeof value === 'number' && value > topSpeed) topSpeed = value
            }
            const lapNumberValue = (lap as { lapNumber?: unknown }).lapNumber
            const lapNumber = typeof lapNumberValue === 'number' ? lapNumberValue : undefined
            rows.push({
              driver,
              lapTimeSeconds: lapTime as number,
              lapNumber,
              topSpeedKph: topSpeed > 0 ? topSpeed : undefined
            })
          } else {
            const failure = result.reason as { driver?: string; error?: unknown }
            if (failure?.driver && !isAbortError(failure.error)) missing.push(failure.driver)
          }
        })
        rows.sort((a, b) => a.lapTimeSeconds - b.lapTimeSeconds)
        setLeaderboard(rows)
        if (!rows.length) {
          setLeaderboardError('No lap telemetry is available for this session.')
        } else {
          setLeaderboardError(null)
        }
        const uniqueMissing = missing.length ? Array.from(new Set(missing)) : []
        setLeaderboardWarning(uniqueMissing.length ? `Missing telemetry for: ${uniqueMissing.join(', ')}` : null)
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setLeaderboard([])
        setLeaderboardError('Unable to load the session leaderboard.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLeaderboardLoading(false)
      })
    return () => controller.abort()
  }, [season, grandPrix, sessionCode, drivers])

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

  const sessionName = useMemo(() => {
    if (!sessionCode) return undefined
    return sessionLabels[sessionCode] ?? sessionCode
  }, [sessionCode])

  const leaderboardRows = useMemo(() => {
    if (!leaderboard.length) return []
    const best = leaderboard[0].lapTimeSeconds
    return leaderboard.map((row, index) => ({
      ...row,
      position: index + 1,
      gapSeconds: row.lapTimeSeconds - best
    }))
  }, [leaderboard])

  const lapCountLabel = leaderboardLoading ? 'Loading...' : String(leaderboard.length)

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
            <option value="">Select season</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>

        <label>
          Grand Prix
          <select value={grandPrix || ''} onChange={handleEventChange} disabled={!season || !events.length}>
            <option value="">Select round</option>
            {events.map((eventSlug) => (
              <option key={eventSlug} value={eventSlug}>{eventSlug.replace(/-/g, ' ')}</option>
            ))}
          </select>
        </label>

        <label>
          Session
          <select value={sessionCode || ''} onChange={handleSessionChange} disabled={!grandPrix || !sessions.length}>
            <option value="">Select session</option>
            {sessions.map((code) => (
              <option key={code} value={code}>{sessionLabels[code] ?? code}</option>
            ))}
          </select>
        </label>

        <label>
          Reference Driver
          <select value={referenceDriver || ''} onChange={handleReferenceChange} disabled={!drivers.length}>
            <option value="">Select driver</option>
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

      <div className="telemetry-summary">
        <span className="telemetry-pill">Season <strong>{season ?? '--'}</strong></span>
        <span className="telemetry-pill">Event <strong>{eventTitle ?? '--'}</strong></span>
        <span className="telemetry-pill">Session <strong>{sessionName ?? '--'}</strong></span>
        <span className="telemetry-pill">Drivers <strong>{drivers.length}</strong></span>
        <span className="telemetry-pill">Lap files <strong>{lapCountLabel}</strong></span>
      </div>

      <div className="telemetry-grid">
        <div className="telemetry-primary">
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

          <div className="telemetry-leaderboard">
            <div className="telemetry-leaderboard__header">
              <h3>{sessionName ? `${sessionName} Leaderboard` : 'Session Leaderboard'}</h3>
              {leaderboardLoading ? <span className="telemetry-tag">Loading...</span> : null}
              {!leaderboardLoading && leaderboard.length ? (
                <span className="telemetry-tag">{leaderboard.length} drivers</span>
              ) : null}
            </div>
            {leaderboardError ? <div className="telemetry-alert telemetry-alert--warning">{leaderboardError}</div> : null}
            {leaderboardWarning ? <div className="telemetry-alert telemetry-alert--info">{leaderboardWarning}</div> : null}
            {leaderboardLoading ? (
              <div className="telemetry-placeholder">
                <div className="loading-spinner" aria-hidden />
                <p>Loading session leaderboard...</p>
              </div>
            ) : leaderboardRows.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Pos</th>
                    <th>Driver</th>
                    <th>Lap</th>
                    <th>Lap Time</th>
                    <th>Gap</th>
                    <th>Top Speed</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboardRows.map((row) => (
                    <tr key={row.driver}>
                      <td>{row.position}</td>
                      <td>{row.driver}</td>
                      <td>{row.lapNumber ? `#${row.lapNumber}` : '--'}</td>
                      <td><strong>{formatLapTime(row.lapTimeSeconds)}</strong></td>
                      <td>{formatGap(row.gapSeconds)}</td>
                      <td>{formatSpeed(row.topSpeedKph)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="telemetry-placeholder">
                <p>Select a session to view lap rankings.</p>
              </div>
            )}
          </div>
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
