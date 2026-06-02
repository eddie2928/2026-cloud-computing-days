import client from './client'

export interface MusicTrack {
  trackName: string
  artistName: string
  previewUrl: string | null
  artworkUrl100: string | null
  collectionName: string
  trackViewUrl: string | null
}

export interface MusicSearchResult {
  ok: boolean
  status_code: number | null
  latency_ms: number
  count?: number
  results: MusicTrack[]
  error?: string
}

export async function searchMusic(term: string, limit = 10): Promise<MusicSearchResult> {
  const res = await client.get<MusicSearchResult>('/music/search', {
    params: { term, limit },
  })
  return res.data
}
