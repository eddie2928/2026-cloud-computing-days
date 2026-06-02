import client from './client'
import type { TasteFormData } from '../lib/taste'

export async function getTasteProfile(): Promise<TasteFormData> {
  const res = await client.get<TasteFormData>('/taste-profile')
  return res.data
}

export async function putTasteProfile(payload: TasteFormData): Promise<TasteFormData> {
  const res = await client.put<TasteFormData>('/taste-profile', payload)
  return res.data
}
