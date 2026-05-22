import type { CalendarEntry } from './week';

export function searchEntries(entries: CalendarEntry[], q: string): CalendarEntry[] {
  if (!q) return [];
  return entries.filter(e => e.date.includes(q));
}
