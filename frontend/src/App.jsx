
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TicketList from './pages/TicketList'
import TicketDetail from './pages/TicketDetail'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/tickets" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/tickets" element={<ProtectedRoute><TicketList /></ProtectedRoute>} />
        <Route path="/tickets/:id" element={<ProtectedRoute><TicketDetail /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App