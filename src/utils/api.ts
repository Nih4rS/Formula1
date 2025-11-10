const ERGAST_BASE = 'https://ergast.com/api/f1'

type ErgastSession = {
  date: string
  time?: string
}

type ErgastRace = {
  season: string
  round: string
  url?: string
  raceName: string
  Circuit: {
    circuitId: string
    url?: string
    circuitName: string
    Location: {
      lat: string
      long: string
      locality: string
      country: string
    }
  }
  date: string
  time?: string
  FirstPractice?: ErgastSession
  SecondPractice?: ErgastSession
  ThirdPractice?: ErgastSession
  Sprint?: ErgastSession
  SprintShootout?: ErgastSession
  Qualifying?: ErgastSession
}

type ErgastRaceTable = {
  MRData: {
    RaceTable: {
      season: string
      Races: ErgastRace[]
    }
  }
}

type ErgastStandingsTable<T> = {
  MRData: {
    StandingsTable: {
      season: string
      StandingsLists: Array<{
        round: string
        DriverStandings?: ErgastDriverStanding[]
        ConstructorStandings?: ErgastConstructorStanding[]
      }>
    }
  }
}

type ErgastDriverStanding = {
  position: string
  points: string
  wins: string
  Driver: {
    driverId: string
    code?: string
    givenName: string
    familyName: string
    nationality: string
  }
  Constructors: Array<{
    constructorId: string
    name: string
  }>
}

type ErgastConstructorStanding = {
  position: string
  points: string
  wins: string
  Constructor: {
    constructorId: string
    name: string
    nationality: string
  }
}

type ErgastResults = {
  MRData: {
    RaceTable: {
      Races: Array<ErgastRace & {
        Results: ErgastRaceResult[]
      }>
    }
  }
}

type ErgastRaceResult = {
  position: string
  points: string
  status: string
  Driver: {
    driverId: string
    code?: string
    givenName: string
    familyName: string
  }
  Constructor: {
    constructorId: string
    name: string
  }
  Time?: {
    time: string
  }
  FastestLap?: {
    Time: { time: string }
  }
}

export type SessionSummary = {
  label: string
  start: Date | null
}

export type RaceSummary = {
  season: string
  round: number
  name: string
  circuit: string
  locality: string
  country: string
  start: Date | null
  sessions: SessionSummary[]
  circuitId: string
  url?: string
}

export type DriverStanding = {
  position: number
  driver: string
  code?: string
  constructor: string
  points: number
  wins: number
}

export type ConstructorStanding = {
  position: number
  name: string
  points: number
  wins: number
}

export type RaceResult = {
  race: RaceSummary
  results: Array<{
    position: number
    driver: string
    code?: string
    constructor: string
    points: number
    status: string
    time?: string
    fastestLap?: string
  }>
}

async function fetchErgast<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${ERGAST_BASE}${path}`, {
    signal,
    headers: {
      accept: 'application/json'
    }
  })
  if (!response.ok) {
    throw new Error(`Ergast request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

function parseDate(date?: string, time?: string): Date | null {
  if (!date) return null
  const normalisedTime = time
    ? time.endsWith('Z') || time.endsWith('z')
      ? time
      : `${time}Z`
    : '00:00:00Z'
  const isoString = `${date}T${normalisedTime}`
  const value = new Date(isoString)
  if (Number.isNaN(value.getTime())) return null
  return value
}

function pickSessions(race: ErgastRace): SessionSummary[] {
  const sessionMap: Array<[keyof ErgastRace, string]> = [
    ['FirstPractice', 'FP1'],
    ['SecondPractice', 'FP2'],
    ['ThirdPractice', 'FP3'],
    ['SprintShootout', 'Sprint Shootout'],
    ['Sprint', 'Sprint'],
    ['Qualifying', 'Qualifying']
  ]

  return sessionMap
    .map(([key, label]) => {
      const session = race[key] as ErgastSession | undefined
      return session ? { label, start: parseDate(session.date, session.time) } : null
    })
    .filter((s): s is SessionSummary => Boolean(s))
}

function toRaceSummary(race: ErgastRace): RaceSummary {
  const { Circuit } = race
  return {
    season: race.season,
    round: Number.parseInt(race.round, 10) || 0,
    name: race.raceName,
    circuit: Circuit.circuitName,
    locality: Circuit.Location.locality,
    country: Circuit.Location.country,
    start: parseDate(race.date, race.time),
    sessions: pickSessions(race),
    circuitId: Circuit.circuitId,
    url: race.url
  }
}

export async function fetchSeasonSchedule(season: string | number = 'current', signal?: AbortSignal): Promise<RaceSummary[]> {
  const data = await fetchErgast<ErgastRaceTable>(`/${season}.json?limit=100`, signal)
  return data.MRData.RaceTable.Races.map(toRaceSummary)
}

export async function fetchNextRace(season: string | number = 'current', signal?: AbortSignal): Promise<RaceSummary | null> {
  const data = await fetchErgast<ErgastRaceTable>(`/${season}/next.json`, signal)
  const race = data.MRData.RaceTable.Races[0]
  return race ? toRaceSummary(race) : null
}

export async function fetchLastRaceResults(season: string | number = 'current', signal?: AbortSignal): Promise<RaceResult | null> {
  const data = await fetchErgast<ErgastResults>(`/${season}/last/results.json`, signal)
  const race = data.MRData.RaceTable.Races[0]
  if (!race) return null
  const summary = toRaceSummary(race)
  const results = (race.Results ?? []).map(result => ({
    position: Number.parseInt(result.position, 10) || 0,
    driver: `${result.Driver.givenName} ${result.Driver.familyName}`.trim(),
    code: result.Driver.code,
    constructor: result.Constructor.name,
    points: Number.parseFloat(result.points) || 0,
    status: result.status,
    time: result.Time?.time,
    fastestLap: result.FastestLap?.Time?.time
  }))
  return { race: summary, results }
}

export async function fetchDriverStandings(season: string | number = 'current', signal?: AbortSignal): Promise<DriverStanding[]> {
  const data = await fetchErgast<ErgastStandingsTable<ErgastDriverStanding>>(`/${season}/driverStandings.json`, signal)
  const firstList = data.MRData.StandingsTable.StandingsLists[0]
  const standings = firstList?.DriverStandings ?? []
  return standings.map(entry => ({
    position: Number.parseInt(entry.position, 10) || 0,
    driver: `${entry.Driver.givenName} ${entry.Driver.familyName}`.trim(),
    code: entry.Driver.code,
  constructor: entry.Constructors?.[0]?.name ?? 'N/A',
    points: Number.parseFloat(entry.points) || 0,
    wins: Number.parseInt(entry.wins, 10) || 0
  }))
}

export async function fetchConstructorStandings(season: string | number = 'current', signal?: AbortSignal): Promise<ConstructorStanding[]> {
  const data = await fetchErgast<ErgastStandingsTable<ErgastConstructorStanding>>(`/${season}/constructorStandings.json`, signal)
  const firstList = data.MRData.StandingsTable.StandingsLists[0]
  const standings = firstList?.ConstructorStandings ?? []
  return standings.map(entry => ({
    position: Number.parseInt(entry.position, 10) || 0,
    name: entry.Constructor.name,
    points: Number.parseFloat(entry.points) || 0,
    wins: Number.parseInt(entry.wins, 10) || 0
  }))
}
