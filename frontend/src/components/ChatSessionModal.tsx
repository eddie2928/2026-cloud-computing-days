import { Modal } from './Modal'
import { ChatSessionPanel } from './ChatSessionPanel'

interface Props {
  date: string | null
  onClose: () => void
  onComplete: (diaryBody: string) => void
}

export function ChatSessionModal({ date, onClose, onComplete }: Props) {
  return (
    <Modal open={!!date} onClose={onClose}>
      {date && (
        <ChatSessionPanel
          date={date}
          onComplete={onComplete}
          onClose={onClose}
        />
      )}
    </Modal>
  )
}
