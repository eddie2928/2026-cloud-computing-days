import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import client from '../api/client'

interface Props {
  children: React.ReactNode
  requireProfile?: boolean
}

export function ProtectedRoute({ children, requireProfile = true }: Props) {
  const { isAuthed, checkAuth } = useAuth()
  const [profileChecked, setProfileChecked] = useState(false)
  const [hasProfile, setHasProfile] = useState<boolean | null>(null)

  useEffect(() => {
    if (isAuthed === null) {
      checkAuth()
    }
  }, [isAuthed, checkAuth])

  useEffect(() => {
    if (isAuthed !== true || !requireProfile) return
    client.get('/profile').then(() => {
      setHasProfile(true)
      setProfileChecked(true)
    }).catch((e) => {
      if (e.response?.status === 404) {
        setHasProfile(false)
      }
      setProfileChecked(true)
    })
  }, [isAuthed, requireProfile])

  if (isAuthed === null) return <div>Loading...</div>
  if (!isAuthed) return <Navigate to="/login" replace />
  if (!requireProfile) return <>{children}</>
  if (!profileChecked) return <div>Loading...</div>
  if (hasProfile === false) return <Navigate to="/onboarding" replace />

  return <>{children}</>
}
