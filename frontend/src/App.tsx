import { Routes, Route } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Dedupe from './pages/Dedupe'
import Triage from './pages/Triage'
import Invest from './pages/Invest'
import Correlate from './pages/Correlate'
import Hunt from './pages/Hunt'
import Soar from './pages/Soar'
import Ticket from './pages/Ticket'
import Cockpit from './pages/Cockpit'
import Dispatch from './pages/Dispatch'
import Report from './pages/Report'
import Cmdb from './pages/Cmdb'
import Intel from './pages/Intel'
import Knowledge from './pages/Knowledge'
import AiCompliance from './pages/AiCompliance'
import Agent from './pages/Agent'
import Mcp from './pages/Mcp'
import LogSources from './pages/LogSources'
import Prompt from './pages/Prompt'
import Skills from './pages/Skills'
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
          <Route path="/correlate" element={<Correlate />} />
          <Route path="/hunt" element={<Hunt />} />
          <Route path="/soar" element={<Soar />} />
          <Route path="/ticket" element={<Ticket />} />
          <Route path="/cockpit" element={<Cockpit />} />
          <Route path="/dispatch" element={<Dispatch />} />
          <Route path="/report" element={<Report />} />
          <Route path="/cmdb" element={<Cmdb />} />
          <Route path="/intel" element={<Intel />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/ai-compliance" element={<AiCompliance />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/mcp" element={<Mcp />} />
          <Route path="/log-sources" element={<LogSources />} />
          <Route path="/prompt" element={<Prompt />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/cost" element={<Cost />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
