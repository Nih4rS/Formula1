export type LapTelemetry = {
  driver?: string
  distance_m: number[]
  speed_kph: number[]
  cum_lap_time_s: number[]
  [key: string]: unknown
}

export type TrackMapPayload = {
  track_map?: {
    X: number[]
    Y: number[]
  }
  corners?: Array<{
    Number: number
    X: number
    Y: number
  }>
  sectors?: Array<{
    X: number[]
    Y: number[]
  }>
  [key: string]: unknown
}

const defaultRequestInit = (signal?: AbortSignal): RequestInit => (signal ? { signal } : {})

export async function listYears(signal?: AbortSignal): Promise<string[]> {
  try {
    // Heuristic: fetch directory listing index.json if provided; else attempt probing common years.
    // For simplicity, try a small fetch to a manifest, else fallback to recent range.
  const res = await fetch('data/index.json', defaultRequestInit(signal))
    if (res.ok) {
      const j = await res.json()
      if (Array.isArray(j.years)) return j.years.map(String)
    }
  } catch {}
  const now = new Date().getFullYear()
  const years = [] as string[]
  for (let y = 2018; y <= now; y++) years.push(String(y))
  return years
}

export async function listEvents(year: string, signal?: AbortSignal): Promise<string[]> {
  try {
  const res = await fetch(`data/${year}/events.json`, defaultRequestInit(signal))
    if (res.ok) return (await res.json()) as string[]
  } catch {}
  // Fallback: try to fetch a known sessions.json index for each dir via precomputed list
  // Without a manifest, we can’t read directories from static hosting. Expect Actions to write events.json.
  return []
}

export async function listSessions(year: string, event: string, signal?: AbortSignal): Promise<string[]> {
  try {
  const res = await fetch(`data/${year}/${event}/sessions.json`, defaultRequestInit(signal))
    if (res.ok) return (await res.json()) as string[]
  } catch {}
  return ['FP1','FP2','FP3','SQ','SS','Q','R']
}

export async function listDrivers(year: string, event: string, session: string, signal?: AbortSignal): Promise<string[]> {
  try {
  const res = await fetch(`data/${year}/${event}/${session}/drivers.json`, defaultRequestInit(signal))
    if (res.ok) return (await res.json()) as string[]
  } catch {}
  return []
}

export async function loadLap(year: string, event: string, session: string, driver: string, signal?: AbortSignal): Promise<LapTelemetry> {
  const res = await fetch(`data/${year}/${event}/${session}/${driver}_bestlap.json`, defaultRequestInit(signal))
  if (!res.ok) throw new Error('Lap not found')
  return res.json() as Promise<LapTelemetry>
}

export async function loadMapData(year?: string, event?: string, signal?: AbortSignal): Promise<TrackMapPayload | null> {
  if (!year || !event) return null
  const out: TrackMapPayload = {}
  const files = ['track_map.json','corners.json','sectors.json']
  await Promise.all(files.map(async f => {
    const r = await fetch(`data/${year}/${event}/${f}`, defaultRequestInit(signal))
    if (r.ok) out[f.replace('.json','')] = await r.json()
  }))
  return out
}

