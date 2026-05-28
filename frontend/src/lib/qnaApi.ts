import client from '../api/client'

export interface UndoResponse {
  question: string
  sequence: number
  suggestions: string[]
  pending_schedules: Array<{ period_start: string; period_end: string; situation: string }>
  removed_schedule_keys: string[]
}

export interface FinalizeResponse {
  diary: string
}

export async function undoQna(
  session_id: number,
  target_sequence: number,
  mode: 'keep' | 'discard',
): Promise<UndoResponse> {
  const res = await client.post<UndoResponse>('/qna/undo', { session_id, target_sequence, mode })
  return res.data
}

export async function finalizeQna(session_id: number): Promise<FinalizeResponse> {
  const res = await client.post<FinalizeResponse>('/qna/finalize', { session_id })
  return res.data
}
