import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Login } from './pages/Login'
import { Hub } from './pages/Hub'
import { Calendar } from './pages/Calendar'
import { Diary } from './pages/Diary'
import { Qna } from './pages/QnA'
import { Profile } from './pages/Profile'
import { Onboarding } from './pages/Onboarding'
import { Admin } from './pages/Admin'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './components/AppLayout'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<ProtectedRoute requireProfile={false}><Onboarding /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to="/hub" replace />} />
        <Route path="/hub" element={<ProtectedRoute><AppLayout><Hub /></AppLayout></ProtectedRoute>} />
        <Route path="/calendar" element={<ProtectedRoute><AppLayout><Calendar /></AppLayout></ProtectedRoute>} />
        <Route path="/diary/:date" element={<ProtectedRoute><AppLayout><Diary /></AppLayout></ProtectedRoute>} />
        <Route path="/qna/:date" element={<ProtectedRoute><AppLayout><Qna /></AppLayout></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><AppLayout><Profile /></AppLayout></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute><AppLayout><Admin /></AppLayout></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/hub" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
