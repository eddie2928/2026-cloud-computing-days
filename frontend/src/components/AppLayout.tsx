import type { ReactNode } from 'react'
import { ScreenContainer } from './days/ScreenContainer'
import { BottomNav } from './layout/BottomNav'
import { GlobalHeader } from './layout/GlobalHeader'
import { DayModalProvider } from '../hooks/useDayModal'
import { useDayModal } from '../hooks/dayModalContext'
import { DayModal } from './calendar/DayModal'

const BG_CLOUDS = `
  radial-gradient(circle at 78% 22%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 18%),
  radial-gradient(ellipse 480px 320px at 18% 78%, #C8DFCA 0%, transparent 55%),
  radial-gradient(ellipse 360px 260px at 88% 88%, #DCE7CC 0%, transparent 55%),
  radial-gradient(ellipse 280px 220px at 12% 28%, #EBEFE8 0%, transparent 55%),
  linear-gradient(180deg, #FCF6EC 0%, #E3F2E4 100%)
`

function DayModalMount() {
  const { dayModalDate, closeDayModal } = useDayModal()
  if (!dayModalDate) return null
  return <DayModal date={dayModalDate} onClose={closeDayModal} />
}

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <DayModalProvider>
      <div style={{ background: BG_CLOUDS, minHeight: '100dvh' }}>
        <GlobalHeader />
        <ScreenContainer style={{ paddingTop: 52, paddingBottom: 80 }}>
          <main style={{ flex: 1, minWidth: 0 }}>{children}</main>
        </ScreenContainer>
        <BottomNav />
        <DayModalMount />
      </div>
    </DayModalProvider>
  )
}
