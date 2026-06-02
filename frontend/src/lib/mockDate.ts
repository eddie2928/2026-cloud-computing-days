import { getSeoulToday } from './today'

const KEY = 'days_mock_date'
const EVENT = 'days-mock-date-changed'

export function getMockDate(): string {
  return localStorage.getItem(KEY) ?? getSeoulToday()
}

export function setMockDate(date: string): void {
  localStorage.setItem(KEY, date)
  window.dispatchEvent(new Event(EVENT))
}

export function clearMockDate(): void {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function hasMockDate(): boolean {
  return localStorage.getItem(KEY) !== null
}

export { EVENT as MOCK_DATE_EVENT }
