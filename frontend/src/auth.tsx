import { createContext, useContext, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { apiPost } from './lib/api'

export type User = { username: string; role: string }

type AuthContextType = {
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>(null!)

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('aisecops_user')
    return saved ? (JSON.parse(saved) as User) : null
  })

  async function login(username: string, password: string) {
    const u = await apiPost<User>('/api/login', { username, password })
    setUser(u)
    localStorage.setItem('aisecops_user', JSON.stringify(u))
  }

  function logout() {
    setUser(null)
    localStorage.removeItem('aisecops_user')
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const loc = useLocation()
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />
  return <>{children}</>
}
