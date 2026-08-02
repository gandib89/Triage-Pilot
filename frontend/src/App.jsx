
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TicketList from './pages/TicketList'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/tickets" replace />} />
        <Route path="/tickets" element={<TicketList />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App