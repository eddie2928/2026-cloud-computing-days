import { useState, useEffect } from 'react'
import { getMockDate, MOCK_DATE_EVENT } from '../lib/mockDate'

export function useMockDate(): string {
  const [date, setDate] = useState(getMockDate)

  useEffect(() => {
    const handler = () => setDate(getMockDate())
    window.addEventListener(MOCK_DATE_EVENT, handler)
    return () => window.removeEventListener(MOCK_DATE_EVENT, handler)
  }, [])

  return date
}
