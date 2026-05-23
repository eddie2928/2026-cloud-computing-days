import client from '../api/client'

export interface DiarySearchItem {
  date: string
  snippet: string
  emotion: string
}

export async function searchDiaries(q: string): Promise<DiarySearchItem[]> {
  if (!q.trim()) return []
  const res = await client.get('/diary/search', { params: { q } })
  return res.data.results as DiarySearchItem[]
}
