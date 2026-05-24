export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export function getSeasonFromDate(dateStr: string): Season {
  const m = /^\d{4}-(\d{2})-\d{2}$/.test(dateStr)
    ? parseInt(dateStr.substring(5, 7), 10)
    : new Date().getMonth() + 1
  if (m === 12 || m <= 2) return 'winter'
  if (m <= 5) return 'spring'
  if (m <= 8) return 'summer'
  return 'autumn'
}

export function applySeason(dateStr: string): void {
  document.documentElement.dataset.season = getSeasonFromDate(dateStr)
}
