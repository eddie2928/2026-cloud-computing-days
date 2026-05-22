export interface CalendarEntry {
  date: string;
  emotion?: string;
}

export interface WeekDay {
  date: string;
  emotion?: string;
}

export function getWeekWindow(entries: CalendarEntry[], today: string): WeekDay[] {
  const todayDate = new Date(today);
  const result: WeekDay[] = [];
  const entryMap = new Map(entries.map(e => [e.date, e.emotion]));

  for (let i = -3; i <= 3; i++) {
    const d = new Date(todayDate);
    d.setDate(todayDate.getDate() + i);
    const dateStr = d.toISOString().split('T')[0];
    result.push({ date: dateStr, emotion: entryMap.get(dateStr) });
  }

  return result;
}
