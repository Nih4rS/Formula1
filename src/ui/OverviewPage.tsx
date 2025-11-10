import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ConstructorStanding,
  DriverStanding,
  RaceResult,
  RaceSummary,
  fetchConstructorStandings,
  fetchDriverStandings,
  fetchLastRaceResults,
  fetchNextRace,
  fetchSeasonSchedule
} from '../utils/api'

type OverviewData = {
  schedule: RaceSummary[]
  nextRace: RaceSummary | null
  lastRace: RaceResult | null
  driverStandings: DriverStanding[]
  constructorStandings: ConstructorStanding[]
}

const DEFAULT_OVERVIEW: OverviewData = {
  schedule: [],
  nextRace: null,
  lastRace: null,
  driverStandings: [],
  constructorStandings: []
}

const formatDateTime = (value: Date | null, options?: Intl.DateTimeFormatOptions): string => {
  if (!value) return 'TBC'
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    ...options
  }).format(value)
}

const formatDate = (value: Date | null): string => {
  if (!value) return 'TBC'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric'
  }).format(value)
}

const formatTime = (value: Date | null): string => {
  if (!value) return 'TBC'
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit'
  }).format(value)
}

const formatCountdown = (start: Date | null, now: Date): string | null => {
  if (!start) return null
  const diff = start.getTime() - now.getTime()
  if (diff <= 0) return 'Lights out!'
  const minutes = Math.floor(diff / 60000)
  const days = Math.floor(minutes / (60 * 24))
  const hours = Math.floor((minutes % (60 * 24)) / 60)
  const remainingMinutes = minutes % 60
  const parts: string[] = []
  if (days) parts.push(`${days}d`)
  if (days || hours) parts.push(`${hours}h`)
  parts.push(`${remainingMinutes}m`)
  return parts.join(' ')
}

const isAbortError = (error: unknown): boolean =>
  typeof error === 'object' && error !== null && 'name' in error && (error as { name?: unknown }).name === 'AbortError'

const OverviewPage: FC = () => {
  const [data, setData] = useState<OverviewData>(DEFAULT_OVERVIEW)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [now, setNow] = useState<Date>(() => new Date())
  const isMounted = useRef(true)

  useEffect(() => () => {
    isMounted.current = false
  }, [])

  const load = useCallback(async (signal?: AbortSignal) => {
    if (isMounted.current && !signal?.aborted) {
      setLoading(true)
      setError(null)
    }
    try {
      const [schedule, nextRace, lastRace, driverStandings, constructorStandings] = await Promise.all([
        fetchSeasonSchedule('current', signal),
        fetchNextRace('current', signal),
        fetchLastRaceResults('current', signal),
        fetchDriverStandings('current', signal),
        fetchConstructorStandings('current', signal)
      ])
      if (signal?.aborted || !isMounted.current) return
      setData({ schedule, nextRace, lastRace, driverStandings, constructorStandings })
    } catch (err) {
      if (signal?.aborted || !isMounted.current || isAbortError(err)) return
      setError('Unable to load live championship data. Please try again in a moment.')
    } finally {
      if (!signal?.aborted && isMounted.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(id)
  }, [])

  const upcomingRaces = useMemo(() => {
    const nowMs = now.getTime()
    return data.schedule
      .filter((race: RaceSummary) => !race.start || race.start.getTime() >= nowMs - 3_600_000)
      .slice(0, 6)
  }, [data.schedule, now])

  const resultsToShow = useMemo(() => data.lastRace?.results.slice(0, 10) ?? [], [data.lastRace])
  const countdown = useMemo(() => formatCountdown(data.nextRace?.start ?? null, now), [data.nextRace, now])

  if (loading) {
    return (
      <div className="panel loading-panel">
        <div className="loading-spinner" aria-hidden />
        <p>Loading live championship data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel error-panel">
        <p>{error}</p>
        <button type="button" onClick={() => load()}>Retry</button>
      </div>
    )
  }

  return (
    <div className="overview">
      <section className="hero">
        {data.nextRace ? (
          <div className="hero__content">
            <p className="hero__eyebrow">Round {data.nextRace.round} - {data.nextRace.season}</p>
            <h1>{data.nextRace.name}</h1>
            <p className="hero__location">{data.nextRace.circuit} - {data.nextRace.locality}, {data.nextRace.country}</p>
            <div className="hero__meta">
              <div>
                <span className="label">Race start</span>
                <span>{formatDateTime(data.nextRace.start)}</span>
              </div>
              <div>
                <span className="label">Countdown</span>
                <span>{countdown ?? '--'}</span>
              </div>
            </div>
            {data.nextRace.sessions.length ? (
              <div className="hero__sessions">
                {data.nextRace.sessions.map(session => (
                  <div key={session.label}>
                    <span className="label">{session.label}</span>
                    <span>{formatDateTime(session.start)}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="hero__content">
            <h1>No races on the calendar</h1>
            <p className="hero__location">Check back later for the upcoming Grand Prix.</p>
          </div>
        )}
      </section>

      <div className="overview-panels">
        <section className="panel standings">
          <header>
            <h2>Driver Standings</h2>
            <span>{data.nextRace?.season ?? ''} Season</span>
          </header>
          <ol>
            {data.driverStandings.slice(0, 10).map(entry => (
              <li key={entry.position}>
                <span className="position">{entry.position}</span>
                <div className="driver">
                  <strong>{entry.driver}</strong>
                  <span>{entry.constructor}</span>
                </div>
                <div className="points">
                  <strong>{entry.points}</strong>
                  <span>{entry.wins} wins</span>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="panel constructors">
          <header>
            <h2>Constructor Standings</h2>
            <span>{data.nextRace?.season ?? ''}</span>
          </header>
          <ol>
            {data.constructorStandings.slice(0, 10).map(entry => (
              <li key={entry.position}>
                <span className="position">{entry.position}</span>
                <div className="driver">
                  <strong>{entry.name}</strong>
                  <span>{entry.wins} wins</span>
                </div>
                <div className="points">
                  <strong>{entry.points}</strong>
                  <span>pts</span>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="panel schedule">
          <header>
            <h2>Grand Prix Schedule</h2>
            <span>Next six rounds</span>
          </header>
          <ul>
            {upcomingRaces.map(race => (
              <li key={`${race.season}-${race.round}`}>
                <div>
                  <strong>{race.name}</strong>
                  <span>{race.locality}, {race.country}</span>
                </div>
                <div>
                  <span className="date">{formatDate(race.start)}</span>
                  <span className="time">{formatTime(race.start)}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel latest-result">
          <header>
            <h2>Latest Grand Prix</h2>
            {data.lastRace ? <span>{data.lastRace.race.name}</span> : <span>--</span>}
          </header>
          {data.lastRace ? (
            <table>
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>Driver</th>
                  <th>Team</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {resultsToShow.map(result => (
                  <tr key={result.position}>
                    <td>{result.position}</td>
                    <td>
                      <strong>{result.driver}</strong>
                      <span>{result.code ?? ''}</span>
                    </td>
                    <td>{result.constructor}</td>
                    <td>{result.time ?? result.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No race results available yet this season.</p>
          )}
        </section>
      </div>
    </div>
  )
}

export default OverviewPage
