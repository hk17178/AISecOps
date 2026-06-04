import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await login(username, password)
      nav('/')
    } catch {
      setErr('登录失败，请检查用户名 / 密码')
    } finally {
      setLoading(false)
    }
  }

  const inputCls =
    'w-full border border-line rounded-lg bg-bg px-3 py-2.5 outline-none focus:border-clay'

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <form onSubmit={submit} className="w-[360px] bg-paper border border-line rounded-[10px] p-8">
        <div className="text-[26px] font-semibold font-serif tracking-wide">AISECOPS</div>
        <div className="text-dim text-sm mb-7">安全运营台</div>

        <label className="block text-[13px] text-dim mb-1.5">用户名</label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className={`${inputCls} mb-4`}
          autoComplete="username"
        />

        <label className="block text-[13px] text-dim mb-1.5">密码</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={`${inputCls} mb-2`}
          autoComplete="current-password"
        />

        {err && <div className="text-terra text-[13px] mb-2">{err}</div>}

        <button
          disabled={loading}
          className="w-full bg-terra text-paper font-medium rounded-lg py-2.5 mt-3 hover:bg-[#9a4527] disabled:opacity-50"
        >
          {loading ? '登录中…' : '登录'}
        </button>

        <div className="text-dim text-[12px] mt-5 text-center">内部系统 · 仅授权人员</div>
      </form>
    </div>
  )
}
