import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Config = {
  llm_base_url: string
  llm_model: string
  llm_api_key_set: boolean
  monthly_budget_cny: number
  allow_outbound: boolean
  es_hosts: string
  wechat_webhook_set: boolean
}
type User = { username: string; role: string; enabled: boolean }

export default function Settings() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [cfg, setCfg] = useState<Config | null>(null)
  const [form, setForm] = useState<Record<string, unknown>>({})
  const [apiKey, setApiKey] = useState('')
  const [webhook, setWebhook] = useState('')
  const [msg, setMsg] = useState('')
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<string[]>(['管理员', '分析师', '普通查看'])
  const [nu, setNu] = useState({ username: '', password: '', role: '分析师' })

  function load() {
    apiGet<Config>('/api/config').then((c) => { setCfg(c); setForm({}) })
    apiGet<{ users: User[]; roles: string[] }>('/api/users').then((d) => { setUsers(d.users); setRoles(d.roles) })
  }
  useEffect(load, [])

  async function saveConfig() {
    const body: Record<string, unknown> = { ...form, actor }
    if (apiKey) body.llm_api_key = apiKey
    if (webhook) body.wechat_webhook = webhook
    const r = await apiPut<{ note: string }>('/api/config', body)
    setMsg(r.note)
    setApiKey(''); setWebhook('')
    load()
  }

  async function addUser() {
    if (!nu.username.trim() || !nu.password) return setMsg('用户名与初始口令不能为空')
    try {
      await apiPost('/api/users', { ...nu, username: nu.username.trim(), actor })
      setMsg(`已新增用户 ${nu.username.trim()}`)
      setNu({ username: '', password: '', role: '分析师' })
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }

  if (!cfg) return <div className="text-dim">加载中…</div>
  const v = (k: keyof Config) => (k in form ? form[k] : cfg[k])
  const inputCls = 'border border-line rounded-lg bg-paper2 px-3 py-2 text-[13px]'

  return (
    <div className="grid grid-cols-2 gap-[34px] items-start">
      {/* 系统配置 */}
      <Card>
        <SectionTitle>系统配置 · 存 DB（P-18，敏感键加密）</SectionTitle>
        <div className="flex flex-col gap-2.5">
          <label className="text-[13px] text-dim">LLM API Key {cfg.llm_api_key_set && <span className="text-sage">（已配置）</span>}</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="填入即更新；留空不改" className={inputCls} />
          <label className="text-[13px] text-dim">Base URL</label>
          <input value={String(v('llm_base_url'))} onChange={(e) => setForm((f) => ({ ...f, llm_base_url: e.target.value }))} className={inputCls} />
          <label className="text-[13px] text-dim">模型</label>
          <input value={String(v('llm_model'))} onChange={(e) => setForm((f) => ({ ...f, llm_model: e.target.value }))} className={inputCls} />
          <label className="text-[13px] text-dim">月度预算 (¥)</label>
          <input type="number" value={String(v('monthly_budget_cny'))} onChange={(e) => setForm((f) => ({ ...f, monthly_budget_cny: parseFloat(e.target.value) }))} className={inputCls} />
          <label className="text-[13px] text-dim">Elasticsearch</label>
          <input value={String(v('es_hosts'))} onChange={(e) => setForm((f) => ({ ...f, es_hosts: e.target.value }))} className={inputCls} />
          <label className="text-[13px] text-dim">企业微信 webhook {cfg.wechat_webhook_set && <span className="text-sage">（已配置）</span>}</label>
          <input type="password" value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="填入即更新；留空不改" className={inputCls} />
          <div className="flex items-center justify-between mt-1">
            <span className="text-[13px] text-dim">出域开关（C-32）</span>
            <button onClick={() => setForm((f) => ({ ...f, allow_outbound: !v('allow_outbound') }))}
              className={`text-[12px] border rounded-full px-2 ${v('allow_outbound') ? 'text-ochre border-ochre' : 'text-sage border-sage'}`}>
              {v('allow_outbound') ? '开' : '关'}
            </button>
          </div>
        </div>
        <button className={`${btnPrimary} mt-4`} onClick={saveConfig}>保存配置</button>
        {msg && <div className="text-sage text-[13px] mt-2">{msg}</div>}
      </Card>

      {/* 用户与 RBAC */}
      <Card>
        <SectionTitle>用户管理 · RBAC（口令 scrypt 哈希）</SectionTitle>
        {users.map((u) => (
          <div key={u.username} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span className="flex items-center gap-2">
              {u.username}
              {!u.enabled && <Pill tone="warn">停用</Pill>}
            </span>
            <span className="flex items-center gap-2">
              <select value={u.role} onChange={(e) => apiPut(`/api/users/${u.username}`, { role: e.target.value, actor }).then(load)}
                className="bg-paper2 border border-line rounded-lg px-2 py-1 text-[12px]">
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <button onClick={() => apiPut(`/api/users/${u.username}`, { enabled: !u.enabled, actor }).then(load)}
                className={`text-[12px] border rounded-full px-2 ${u.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                {u.enabled ? '启用' : '停用'}
              </button>
              {u.username !== 'admin' && (
                <button onClick={() => apiDelete(`/api/users/${u.username}`).then(load)} className="text-dim hover:text-terra text-[16px] leading-none">×</button>
              )}
            </span>
          </div>
        ))}
        <div className="mt-4 flex flex-col gap-2">
          <div className="flex gap-2">
            <input value={nu.username} onChange={(e) => setNu({ ...nu, username: e.target.value })} placeholder="用户名"
              className={`${inputCls} flex-1`} />
            <input type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} placeholder="初始口令"
              className={`${inputCls} flex-1`} />
            <select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })} className={inputCls}>
              {roles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <button className={btnGhost} onClick={addUser}>+ 新增用户</button>
        </div>
        <div className="text-dim text-[12px] mt-3">默认 admin / analyst，口令 aisecops。会话令牌鉴权为后续增强。</div>
      </Card>
    </div>
  )
}
