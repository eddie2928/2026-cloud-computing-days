import { useState, type FormEvent } from 'react'
import { GENDER_OPTIONS, parseCsvTags, stringifyTags, normalizeNotificationTime } from '../lib/profile'

export interface ProfileFormValue {
  nickname: string
  gender: string
  age: number | ''
  occupation: string
  hobbies: string[]
  interests: string[]
  notification_time: string | null
}

interface Props {
  initial: ProfileFormValue
  submitLabel: string
  onSubmit: (v: ProfileFormValue) => Promise<void>
  onCancel?: () => void
}

export function ProfileForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [nickname, setNickname] = useState(initial.nickname)
  const [gender, setGender] = useState(initial.gender)
  const [age, setAge] = useState(initial.age === '' ? '' : String(initial.age))
  const [occupation, setOccupation] = useState(initial.occupation)
  const [hobbiesCsv, setHobbiesCsv] = useState(stringifyTags(initial.hobbies))
  const [interestsCsv, setInterestsCsv] = useState(stringifyTags(initial.interests))
  const [notificationTime, setNotificationTime] = useState(initial.notification_time ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await onSubmit({
        nickname,
        gender,
        age: age === '' ? '' : Number(age),
        occupation,
        hobbies: parseCsvTags(hobbiesCsv),
        interests: parseCsvTags(interestsCsv),
        notification_time: normalizeNotificationTime(notificationTime),
      })
    } catch {
      setError('저장 중 오류가 발생했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <label htmlFor="nickname">닉네임 *</label>
        <input
          id="nickname"
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          required
          minLength={1}
          maxLength={30}
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      <fieldset style={{ border: '1px solid #ccc', padding: 12 }}>
        <legend>성별 *</legend>
        {GENDER_OPTIONS.map((opt) => (
          <label key={opt.value} style={{ marginRight: 16 }}>
            <input
              type="radio"
              name="gender"
              value={opt.value}
              checked={gender === opt.value}
              onChange={() => setGender(opt.value)}
              required
            />
            {' '}{opt.label}
          </label>
        ))}
      </fieldset>

      <div>
        <label htmlFor="age">나이 *</label>
        <input
          id="age"
          type="number"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          required
          min={1}
          max={149}
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      <div>
        <label htmlFor="occupation">직업</label>
        <input
          id="occupation"
          type="text"
          value={occupation}
          onChange={(e) => setOccupation(e.target.value)}
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      <div>
        <label htmlFor="hobbies">취미 (콤마로 구분)</label>
        <input
          id="hobbies"
          type="text"
          value={hobbiesCsv}
          onChange={(e) => setHobbiesCsv(e.target.value)}
          placeholder="예: 독서, 요가"
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      <div>
        <label htmlFor="interests">관심사 (콤마로 구분)</label>
        <input
          id="interests"
          type="text"
          value={interestsCsv}
          onChange={(e) => setInterestsCsv(e.target.value)}
          placeholder="예: 커리어, 건강"
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      <div>
        <label htmlFor="notification_time">알림 시간</label>
        <input
          id="notification_time"
          type="time"
          value={notificationTime}
          onChange={(e) => setNotificationTime(e.target.value)}
          style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
        />
      </div>

      {error && <p role="alert" style={{ color: 'red' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="submit" disabled={submitting} style={{ padding: '8px 24px' }}>
          {submitting ? '저장 중...' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} style={{ padding: '8px 16px' }}>
            취소
          </button>
        )}
      </div>
    </form>
  )
}
