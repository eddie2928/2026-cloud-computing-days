import { useState, useCallback } from 'react'
import { Modal } from './Modal'
import { ChatSessionPanel } from './ChatSessionPanel'

interface Props {
  date: string | null
  onClose: () => void
  onComplete: (diaryBody: string) => void
}

export function ChatSessionModal({ date, onClose, onComplete }: Props) {
  const [progress, setProgress] = useState(0)
  const [noticeShown, setNoticeShown] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [showFinalizingNotice, setShowFinalizingNotice] = useState(false)

  const handleClose = useCallback(() => {
    if (finalizing) {
      setShowFinalizingNotice(true)
      setTimeout(() => setShowFinalizingNotice(false), 2500)
      return
    }
    if (progress >= 1 && !noticeShown) {
      setNoticeShown(true)
      setShowToast(true)
      setTimeout(() => {
        setShowToast(false)
        onClose()
      }, 1500)
      return
    }
    onClose()
  }, [finalizing, progress, noticeShown, onClose])

  return (
    <Modal open={!!date} onClose={handleClose}>
      {date && (
        <div style={{ position: 'relative' }}>
          {showToast && (
            <div
              role="status"
              aria-live="polite"
              style={{
                position: 'absolute', top: -8, left: 0, right: 0,
                background: '#1f2937', color: 'white',
                borderRadius: 8, padding: '10px 16px',
                fontSize: 13, textAlign: 'center', zIndex: 10,
              }}
            >
              진행 상황은 저장됐어요. 같은 날짜를 다시 클릭하면 이어서 할 수 있어요.
            </div>
          )}
          {showFinalizingNotice && (
            <div
              role="status"
              aria-live="polite"
              style={{
                position: 'absolute', top: -8, left: 0, right: 0,
                background: '#4f46e5', color: 'white',
                borderRadius: 8, padding: '10px 16px',
                fontSize: 13, textAlign: 'center', zIndex: 10,
              }}
            >
              거의 다 됐어요, 잠시만 기다려주세요.
            </div>
          )}
          <ChatSessionPanel
            date={date}
            onComplete={onComplete}
            onClose={handleClose}
            onProgressChange={setProgress}
            onFinalizingChange={setFinalizing}
          />
        </div>
      )}
    </Modal>
  )
}
