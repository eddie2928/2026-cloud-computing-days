import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface Props {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: Props) {
  const { isAuthed, checkAuth } = useAuth()

  useEffect(() => {
    if (isAuthed === null) {
      checkAuth()
    }
  }, [isAuthed, checkAuth])

  if (isAuthed === null) return <div>Loading...</div>
  if (!isAuthed) return <Navigate to="/login" replace />

  return <>{children}</>
}
