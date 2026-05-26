import { useEffect, useState, useId } from 'react'
import { Icon } from './Icon'

interface Props {
  open: boolean
  onClose: () => void
  mode: 'all' | 'ios-safari'
}

const SECTIONS = [
  {
    key: 'iphone',
    label: 'iPhone (Safari)',
    icon: 'share-ios',
    content: [
      'Safari로 접속한 뒤 ① 하단 공유 버튼 → ② \'홈 화면에 추가\' → ③ 우측 상단 \'추가\'.',
      'Chrome·Firefox 등 다른 브라우저에서는 설치되지 않으니 Safari로 열어주세요.',
    ],
  },
  {
    key: 'android',
    label: 'Android',
    icon: 'download',
    content: [
      '보통 설치 안내가 자동으로 떠요.',
      '안 뜨면 ⋮ 메뉴 → \'앱 설치\' 또는 \'홈 화면에 추가\'.',
    ],
  },
  {
    key: 'mac',
    label: 'Mac',
    icon: 'download',
    content: [
      'Chrome·Edge: 주소창 오른쪽 설치 아이콘 클릭.',
      'Safari 17 이상: 파일 메뉴 → \'Dock에 추가\'.',
    ],
  },
  {
    key: 'windows',
    label: 'Windows PC',
    icon: 'download',
    content: [
      'Chrome·Edge: 주소창 오른쪽 설치 아이콘 클릭.',
      'Firefox는 설치를 지원하지 않으니 Chrome 또는 Edge를 사용하세요.',
    ],
  },
]

export function InstallGuideModal({ open, onClose, mode }: Props) {
  const titleId = useId()
  const [openSection, setOpenSection] = useState<string | null>(mode === 'ios-safari' ? 'iphone' : null)

  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const sections = mode === 'ios-safari'
    ? SECTIONS.filter(s => s.key === 'iphone')
    : SECTIONS

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(30,28,24,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        zIndex: 9999,
        animation: 'days-fade-in 200ms var(--ease-out) both',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 440,
          background: 'var(--paper-pure)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          boxShadow: 'var(--shadow-3)',
          padding: '28px 28px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
          animation: 'days-pop 300ms var(--ease-soft) both',
        }}
      >
        {/* header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2
            id={titleId}
            style={{
              margin: 0,
              font: '600 17px/1.2 var(--font-sans)',
              color: 'var(--ink-deep)',
              letterSpacing: '-0.01em',
            }}
          >
            {mode === 'ios-safari' ? 'iPhone에 설치하는 방법' : '앱으로 설치하기'}
          </h2>
          <button
            aria-label="닫기"
            onClick={onClose}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 32,
              height: 32,
              borderRadius: 999,
              border: '1px solid var(--line)',
              background: 'var(--paper-bone)',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            <Icon name="close" size={15} color="var(--ink-meta)" />
          </button>
        </div>

        {/* sections */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sections.map(section => {
            const isOpen = mode === 'ios-safari' || openSection === section.key
            return (
              <div
                key={section.key}
                style={{
                  borderRadius: 12,
                  border: '1px solid var(--line)',
                  overflow: 'hidden',
                }}
              >
                <button
                  onClick={() => setOpenSection(isOpen && mode !== 'ios-safari' ? null : section.key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    width: '100%',
                    padding: '12px 16px',
                    border: 0,
                    background: isOpen ? 'var(--sage-wash)' : 'var(--paper-bone)',
                    cursor: mode === 'ios-safari' ? 'default' : 'pointer',
                    textAlign: 'left',
                    transition: 'background 150ms var(--ease-out)',
                  }}
                >
                  <Icon name={section.icon} size={17} color="var(--sage-forest)" />
                  <span
                    style={{
                      flex: 1,
                      font: '500 14px/1 var(--font-sans)',
                      color: 'var(--ink-deep)',
                    }}
                  >
                    {section.label}
                  </span>
                  {mode !== 'ios-safari' && (
                    <Icon
                      name={isOpen ? 'chevron-left' : 'chevron-right'}
                      size={15}
                      color="var(--ink-meta)"
                      style={{ transform: isOpen ? 'rotate(-90deg)' : 'rotate(90deg)', transition: 'transform 150ms' }}
                    />
                  )}
                </button>
                {isOpen && (
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                      padding: '12px 16px',
                      font: '400 13px/1.7 var(--font-sans)',
                      color: 'var(--ink-meta)',
                      borderTop: '1px solid var(--line)',
                    }}
                  >
                    {section.content.map((line, i) => (
                      <span key={i}>{line}</span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
