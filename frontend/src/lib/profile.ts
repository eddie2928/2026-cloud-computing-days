export const GENDER_OPTIONS = [
  { value: 'male', label: '남' },
  { value: 'female', label: '여' },
  { value: 'other', label: '기타' },
  { value: 'private', label: '비공개' },
] as const

export function parseCsvTags(value: string): string[] {
  return value
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

export function stringifyTags(arr: string[]): string {
  return arr.join(', ')
}

export function normalizeNotificationTime(v: string): string | null {
  const trimmed = v.trim()
  if (!trimmed) return null
  return trimmed
}
