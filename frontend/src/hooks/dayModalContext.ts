import { createContext, useContext } from 'react'

export interface DayModalContextValue {
  dayModalDate: string | null
  openDayModal: (date: string) => void
  closeDayModal: () => void
}

export const DayModalContext = createContext<DayModalContextValue | null>(null)

export function useDayModal(): DayModalContextValue {
  const ctx = useContext(DayModalContext)
  if (!ctx) {
    return {
      dayModalDate: null,
      openDayModal: () => {},
      closeDayModal: () => {},
    }
  }
  return ctx
}
