import client from '../api/client'

export async function fetchStreak(): Promise<number> {
  const res = await client.get('/user/streak')
  return res.data.streak as number
}
