import { Routes, Route } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Dedupe from './pages/Dedupe'
import Triage from './pages/Triage'
import Invest from './pages/Invest'
import Hunt from './pages/Hunt'
import Soar from './pages/Soar'
import Ticket from './pages/Ticket'
import Dispatch from './pages/Dispatch'
import Chat from './pages/Chat'
import Report from './pages/Report'
import Cmdb from './pages/Cmdb'
import Intel from './pages/Intel'
import Agent from './pages/Agent'
import Mcp from './pages/Mcp'
import Prompt from './pages/Prompt'
import Cost from './pages/Cost'
import Settings from './pages/Settings'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/dedupe" element={<Dedupe />} />
          <Route path="/triage" element={<Triage />} />
          <Route path="/invest" element={<Invest />} />
          <Route path="/hunt" element={<Hunt />} />
          <Route path="/soar" element={<Soar />} />
          <Route path="/ticket" element={<Ticket />} />
          <Route path="/dispatch" element={<Dispatch />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/report" element={<Report />} />
          <Route path="/cmdb" element={<Cmdb />} />
          <Route path="/intel" element={<Intel />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/mcp" element={<Mcp />} />
          <Route path="/prompt" element={<Prompt />} />
          <Route path="/cost" element={<Cost />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
