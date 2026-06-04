import { Routes, Route } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Triage from './pages/Triage'
import Settings from './pages/Settings'
import Placeholder from './pages/Placeholder'
import { NAV } from './nav'

const REAL_PAGES = new Set(['dashboard', 'triage', 'settings'])

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
          <Route path="/triage" element={<Triage />} />
          <Route path="/settings" element={<Settings />} />
          {NAV.filter((n) => !REAL_PAGES.has(n.key)).map((n) => (
            <Route key={n.key} path={n.path} element={<Placeholder label={n.label} tag={n.tag} />} />
          ))}
        </Route>
      </Routes>
    </AuthProvider>
  )
}
