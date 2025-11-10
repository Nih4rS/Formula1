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
  const [eventOptions, setEventOptions] = useState<string[]>([])
  const [sessionOptions, setSessionOptions] = useState<string[]>([])
  const [driverOptions, setDriverOptions] = useState<string[]>([])

  const [formSeason, setFormSeason] = useState<string>('')
  const [formGrandPrix, setFormGrandPrix] = useState<string>('')
  const [formSession, setFormSession] = useState<string>('')
  const [formReference, setFormReference] = useState<string>('')
  const [formComparisons, setFormComparisons] = useState<string[]>([])

  const [season, setSeason] = useState<string | undefined>()
  const [grandPrix, setGrandPrix] = useState<string | undefined>()
  const [sessionCode, setSessionCode] = useState<string | undefined>()
  const [referenceDriver, setReferenceDriver] = useState<string | undefined>()
  const [comparisonDrivers, setComparisonDrivers] = useState<string[]>([])
  const [appliedDrivers, setAppliedDrivers] = useState<string[]>([])
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

  // ----- Form-driven option fetching (no defaults preselected)
  useEffect(() => {
    // when formSeason changes, fetch events list for the season
    if (!formSeason) {
      setEventOptions([])
      setSessionOptions([])
      setDriverOptions([])
      setFormGrandPrix('')
      setFormSession('')
      setFormReference('')
      setFormComparisons([])
      return
    }
    const controller = new AbortController()
    setEventOptions([])
    setSessionOptions([])
    setDriverOptions([])
    listEvents(formSeason, controller.signal)
      .then((data) => setEventOptions(data))
      .catch((error) => {
        if (!isAbortError(error)) setEventOptions([])
      })
    return () => controller.abort()
  }, [formSeason])

  useEffect(() => {
    // when formGrandPrix changes, fetch sessions for that round
    if (!formSeason || !formGrandPrix) {
      setSessionOptions([])
      setDriverOptions([])
      setFormSession('')
      setFormReference('')
      setFormComparisons([])
      return
    }
    const controller = new AbortController()
    setSessionOptions([])
    setDriverOptions([])
    listSessions(formSeason, formGrandPrix, controller.signal)
      .then((data) => setSessionOptions(data))
      .catch((error) => {
        if (!isAbortError(error)) setSessionOptions([])
      })
    return () => controller.abort()
  }, [formSeason, formGrandPrix])

  useEffect(() => {
    // when formSession changes, fetch drivers for that session
    if (!formSeason || !formGrandPrix || !formSession) {
      setDriverOptions([])
      setFormReference('')
      setFormComparisons([])
      return
    }
    const controller = new AbortController()
    setDriverOptions([])
    listDrivers(formSeason, formGrandPrix, formSession, controller.signal)
      .then((data) => setDriverOptions(data))
      .catch((error) => {
        if (!isAbortError(error)) setDriverOptions([])
      })
    return () => controller.abort()
  }, [formSeason, formGrandPrix, formSession])

  // When filters are applied (season, grandPrix, sessionCode), fetch drivers for the applied selection
  useEffect(() => {
    if (!season || !grandPrix || !sessionCode) {
      setAppliedDrivers([])
      return
    }
    const controller = new AbortController()
    setAppliedDrivers([])
    listDrivers(season, grandPrix, sessionCode, controller.signal)
      .then((data) => setAppliedDrivers(data))
      .catch((error) => {
        if (!isAbortError(error)) setAppliedDrivers([])
      })
    return () => controller.abort()
  }, [season, grandPrix, sessionCode])

  // ----- End form option fetching

  // (Replaced by applied-drivers effect above)

  // Do not auto-select any driver by default; when the reference driver changes, drop it from comparisons

  useEffect(() => {
    if (!referenceDriver) return
    setComparisonDrivers((prev) => prev.filter((driver) => driver !== referenceDriver))
  }, [referenceDriver])

  useEffect(() => {
    // keep applied comparison list consistent with available applied drivers
    setComparisonDrivers((prev) => prev.filter((driver) => appliedDrivers.includes(driver)))
  }, [appliedDrivers])

  useEffect(() => {
    if (!season || !grandPrix || !sessionCode) {
      setLeaderboard([])
      setLeaderboardLoading(false)
      setLeaderboardError(null)
      setLeaderboardWarning(null)
      return
    }
    if (!appliedDrivers.length) {
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
    const requests = appliedDrivers.map(async (driver) => {
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
  }, [season, grandPrix, sessionCode, appliedDrivers])

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

  // Form comparison options depend on form selections
  const formComparisonOptions = useMemo(
    () => driverOptions.filter((driver) => driver !== formReference),
    [driverOptions, formReference]
  )

  const comparisonSize = useMemo(
    () => Math.min(6, Math.max(2, formComparisonOptions.length || 2)),
    [formComparisonOptions.length]
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
    setFormSeason(event.target.value)
  }

  const handleEventChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setFormGrandPrix(event.target.value)
  }

  const handleSessionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setFormSession(event.target.value)
  }

  const handleReferenceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setFormReference(event.target.value)
  }

  const handleComparisonChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const unique = Array.from(new Set(Array.from(event.target.selectedOptions).map((option) => option.value)))
    setFormComparisons(unique.filter((driver) => driver && driver !== formReference))
  }

  const applyFilters = () => {
    setSeason(formSeason || undefined)
    setGrandPrix(formGrandPrix || undefined)
    setSessionCode(formSession || undefined)
    setReferenceDriver(formReference || undefined)
    setComparisonDrivers(formComparisons.filter((d) => d && d !== formReference))
    setSelectedTurn(undefined)
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
          <select value={formSeason} onChange={handleSeasonChange} disabled={!years.length}>
            <option value="">Select season</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>

        <label>
          Grand Prix
          <select value={formGrandPrix} onChange={handleEventChange} disabled={!formSeason || !eventOptions.length}>
            <option value="">Select round</option>
            {eventOptions.map((eventSlug) => (
              <option key={eventSlug} value={eventSlug}>{eventSlug.replace(/-/g, ' ')}</option>
            ))}
          </select>
        </label>

        <label>
          Session
          <select value={formSession} onChange={handleSessionChange} disabled={!formGrandPrix || !sessionOptions.length}>
            <option value="">Select session</option>
            {sessionOptions.map((code) => (
              <option key={code} value={code}>{sessionLabels[code] ?? code}</option>
            ))}
          </select>
        </label>

        <label>
          Reference Driver
          <select value={formReference} onChange={handleReferenceChange} disabled={!driverOptions.length}>
            <option value="">Select driver</option>
            {driverOptions.map((driver) => (
              <option key={driver} value={driver}>{driver}</option>
            ))}
          </select>
        </label>

        <label>
          Compare Drivers
          <select
            multiple
            size={comparisonSize}
            value={formComparisons}
            onChange={handleComparisonChange}
            disabled={!formComparisonOptions.length}
          >
            {formComparisonOptions.map((driver) => (
              <option key={driver} value={driver}>{driver}</option>
            ))}
          </select>
        </label>

        <div>
          <span className="sr-only">Apply</span>
          <button type="button" className="nav-tab" onClick={applyFilters} disabled={!formSeason || !formGrandPrix || !formSession}>
            Apply
          </button>
        </div>
      </div>

      <div className="telemetry-summary">
        <span className="telemetry-pill">Season <strong>{season ?? '--'}</strong></span>
        <span className="telemetry-pill">Event <strong>{eventTitle ?? '--'}</strong></span>
        <span className="telemetry-pill">Session <strong>{sessionName ?? '--'}</strong></span>
  <span className="telemetry-pill">Drivers <strong>{appliedDrivers.length}</strong></span>
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
