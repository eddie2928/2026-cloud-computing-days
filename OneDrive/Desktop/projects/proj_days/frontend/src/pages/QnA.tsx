import { useState, type FormEvent } from 'react'
import client from '../api/client'

interface QnAState {
  sessionId: number
  question: string
  sequence: number
  answers: { seq: number; q: string; a: string }[]
}

export function QnA() {
  const [date, setDate] = useState('')
  const [qnaState, setQnaState] = useState<QnAState | null>(null)
  const [answer, setAnswer] = useState('')
  const [diary, setDiary] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [completed, setCompleted] = useState(false)

  const handleStart = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const resp = await client.post('/qna/start', { diary_date: date })
      const data = resp.data
      setQnaState({
        sessionId: data.session_id,
        question: data.question,
        sequence: data.sequence,
        answers: [],
      })
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError('이미 완료된 날짜입니다.')
        setCompleted(true)
      } else {
        setError('오류가 발생했습니다.')
      }
    }
  }

  const handleAnswer = async (e: FormEvent) => {
    e.preventDefault()
    if (!qnaState) return
    setError('')
    try {
      const resp = await client.post('/qna/answer', {
        session_id: qnaState.sessionId,
        sequence: qnaState.sequence,
        answer,
      })
      const data = resp.data

      const newAnswers = [
        ...qnaState.answers,
        { seq: qnaState.sequence, q: qnaState.question, a: answer },
      ]
      const stored = JSON.parse(localStorage.getItem(`qna:${date}`) || '[]')
      localStorage.setItem(
        `qna:${date}`,
        JSON.stringify([...stored, { seq: qnaState.sequence, q: qnaState.question, a: answer }])
      )

      if (data.completed) {
        setDiary(data.diary)
        setQnaState({ ...qnaState, answers: newAnswers })
      } else {
        setQnaState({
          ...qnaState,
          question: data.next_question,
          sequence: data.sequence,
          answers: newAnswers,
        })
        setAnswer('')
      }
    } catch {
      setError('답변 제출 중 오류가 발생했습니다.')
    }
  }

  if (diary) {
    return (
      <div style={{ padding: 24 }}>
        <h2>일기 생성 완료</h2>
        <p>{date}의 일기:</p>
        <div style={{
          background: '#f9fafb',
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          padding: 16,
          whiteSpace: 'pre-wrap',
        }}>
          {diary}
        </div>
      </div>
    )
  }

  if (qnaState) {
    return (
      <div style={{ padding: 24, maxWidth: 600 }}>
        <h2>질문 {qnaState.sequence} / 5</h2>
        <p style={{ fontSize: 18, fontWeight: 500 }}>{qnaState.question}</p>
        <form onSubmit={handleAnswer}>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={4}
            style={{ width: '100%', padding: 8, marginTop: 8 }}
            placeholder="답변을 입력하세요..."
            required
          />
          {error && <p role="alert" style={{ color: 'red' }}>{error}</p>}
          <button type="submit" disabled={!answer} style={{ marginTop: 12, padding: '8px 24px' }}>
            제출
          </button>
        </form>
      </div>
    )
  }

  return (
    <div style={{ padding: 24, maxWidth: 400 }}>
      <h2>QnA 작성</h2>
      <form onSubmit={handleStart}>
        <label htmlFor="diary-date">날짜 선택</label>
        <input
          id="diary-date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          required
          style={{ display: 'block', width: '100%', marginTop: 8, padding: 8 }}
        />
        {error && <p role="alert" style={{ color: 'red' }}>{error}</p>}
        <button
          type="submit"
          disabled={!date || completed}
          style={{ marginTop: 16, padding: '8px 24px' }}
        >
          {completed ? '이미 완료됨' : '시작'}
        </button>
      </form>
    </div>
  )
}
