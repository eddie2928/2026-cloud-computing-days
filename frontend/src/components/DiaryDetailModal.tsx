import { useEffect, useState } from 'react'
import client from '../api/client'
import { type EmotionKey, EMOTION_EMOJI } from '../lib/emotions'
import { Modal } from './Modal'
import { EmotionPicker } from './EmotionPicker'

interface Props {
  date: string | null
  onClose: () => void
  onUpdated: () => void
}

export function DiaryDetailModal({ date, onClose, onUpdated }: Props) {
  const [body, setBody] = useState('')
  const [emotion, setEmotion] = useState<EmotionKey>('neutral')
  const [editingBody, setEditingBody] = useState(false)
  const [editedBody, setEditedBody] = useState('')
  const [showEmotionPicker, setShowEmotionPicker] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!date) return
    setLoading(true)
    setEditingBody(false)
    setEditedBody('')
    setShowEmotionPicker(false)
    client.get(`/diary/${date}`)
      .then((r) => {
        setBody(r.data.body)
        setEmotion(r.data.emotion as EmotionKey)
      })
      .finally(() => setLoading(false))
  }, [date])

  const handleClose = () => {
    if (editingBody && editedBody !== body) {
      if (!window.confirm('저장하지 않은 변경사항이 있습니다. 닫으시겠어요?')) return
    }
    onClose()
  }

  const handleEmotionChange = async (newEmotion: EmotionKey) => {
    setShowEmotionPicker(false)
    const prev = emotion
    setEmotion(newEmotion)
    try {
      await client.patch(`/diary/${date}/emotion`, { emotion: newEmotion })
      onUpdated()
    } catch {
      setEmotion(prev)
    }
  }

  const handleSaveBody = async () => {
    if (!date || !editedBody.trim()) return
    setSaving(true)
    try {
      const resp = await client.patch(`/diary/${date}/body`, { body: editedBody })
      setBody(resp.data.body)
      setEditingBody(false)
      setEditedBody('')
      onUpdated()
    } catch {
      // keep editing state
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={!!date} onClose={handleClose}>
      {loading ? (
        <div style={{ padding: 24, textAlign: 'center', color: '#6b7280' }}>로딩 중...</div>
      ) : (
        <>
          <div style={{ marginBottom: 20, paddingRight: 32 }}>
            <p style={{ margin: 0, fontSize: 13, color: '#9ca3af' }}>{date}</p>
            <h2 style={{ margin: '4px 0 0', fontSize: 18 }}>일기</h2>
          </div>

          {/* 감정 영역 */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>감정</span>
              <button
                onClick={() => setShowEmotionPicker((v) => !v)}
                style={{
                  fontSize: 28,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  lineHeight: 1,
                }}
                title="감정 변경"
              >
                {EMOTION_EMOJI[emotion]}
              </button>
            </div>
            {showEmotionPicker && (
              <EmotionPicker value={emotion} onChange={handleEmotionChange} />
            )}
          </div>

          {/* 본문 영역 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>일기 내용</span>
              {!editingBody && (
                <button
                  onClick={() => { setEditingBody(true); setEditedBody(body) }}
                  style={{ fontSize: 12, color: '#4f46e5', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                >
                  편집
                </button>
              )}
            </div>

            {editingBody ? (
              <>
                <textarea
                  value={editedBody}
                  onChange={(e) => setEditedBody(e.target.value)}
                  rows={10}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #d1d5db',
                    fontFamily: 'inherit',
                    fontSize: 14,
                    lineHeight: 1.8,
                    resize: 'vertical',
                    boxSizing: 'border-box',
                  }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 8, justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => { setEditingBody(false); setEditedBody('') }}
                    style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db', background: 'white', cursor: 'pointer', fontSize: 14 }}
                  >
                    취소
                  </button>
                  <button
                    onClick={handleSaveBody}
                    disabled={saving || !editedBody.trim()}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 8,
                      border: 'none',
                      background: saving || !editedBody.trim() ? '#e5e7eb' : '#4f46e5',
                      color: saving || !editedBody.trim() ? '#9ca3af' : 'white',
                      cursor: saving || !editedBody.trim() ? 'not-allowed' : 'pointer',
                      fontSize: 14,
                      fontWeight: 600,
                    }}
                  >
                    {saving ? '저장 중...' : '저장'}
                  </button>
                </div>
              </>
            ) : (
              <div
                style={{
                  background: '#f9fafb',
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  padding: 16,
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.8,
                  fontSize: 14,
                }}
              >
                {body}
              </div>
            )}
          </div>
        </>
      )}
    </Modal>
  )
}
