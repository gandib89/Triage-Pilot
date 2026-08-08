import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import TicketList from './pages/TicketList'
import TicketDetail from './pages/TicketDetail'
import NewTicket from './pages/NewTicket'
import TriageQueue from './pages/TriageQueue'
import DecisionDetail from './pages/DecisionDetail'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

function App() {
  return (
    <BrowserRouter>
      <div className="atmosphere" aria-hidden="true" />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/tickets" element={<ProtectedRoute roles={['customer']} redirectTo="/triage"><Layout><TicketList /></Layout></ProtectedRoute>} />
        <Route path="/tickets/new" element={<ProtectedRoute roles={['customer']} redirectTo="/triage"><Layout><NewTicket /></Layout></ProtectedRoute>} />
        <Route path="/tickets/:id" element={<ProtectedRoute roles={['customer']} redirectTo="/triage"><Layout><TicketDetail /></Layout></ProtectedRoute>} />
        <Route path="/triage" element={<ProtectedRoute roles={['staff', 'admin']} redirectTo="/tickets"><Layout><TriageQueue /></Layout></ProtectedRoute>} />
        <Route path="/triage/:id" element={<ProtectedRoute roles={['staff', 'admin']} redirectTo="/tickets"><Layout><DecisionDetail /></Layout></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
