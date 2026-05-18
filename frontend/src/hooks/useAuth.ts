import { useState, useCallback } from 'react'
import client from '../api/client'

export function useAuth() {
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null)

  const checkAuth = useCallback(async () => {
    try {
      await client.get('/me')
      setIsAuthed(true)
    } catch {
      setIsAuthed(false)
    }
  }, [])

  const login = useCallback(async (password: string) => {
    await client.post('/login', { password })
    setIsAuthed(true)
  }, [])

  const logout = useCallback(async () => {
    await client.post('/logout')
    setIsAuthed(false)
  }, [])

  return { isAuthed, checkAuth, login, logout }
}
