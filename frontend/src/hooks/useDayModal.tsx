import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { DayModalContext } from './dayModalContext'

export function DayModalProvider({ children }: { children: ReactNode }) {
  const [date, setDate] = useState<string | null>(null)

  const openDayModal = useCallback((d: string) => setDate(d), [])
  const closeDayModal = useCallback(() => setDate(null), [])

  const value = useMemo(
    () => ({ dayModalDate: date, openDayModal, closeDayModal }),
    [date, openDayModal, closeDayModal]
  )

  return <DayModalContext.Provider value={value}>{children}</DayModalContext.Provider>
}
