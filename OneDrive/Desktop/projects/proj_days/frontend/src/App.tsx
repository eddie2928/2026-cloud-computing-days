import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Login } from './pages/Login'
import { QnA } from './pages/QnA'
import { CalendarPage } from './pages/CalendarPage'
import { DiaryView } from './pages/DiaryView'
import { Profile } from './pages/Profile'

function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const showSidebar = pathname !== '/login'

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {showSidebar && <Sidebar />}
      <main style={{ flex: 1 }}>{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/qna" element={<QnA />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/diary/:date" element={<DiaryView />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/" element={<Navigate to="/qna" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
