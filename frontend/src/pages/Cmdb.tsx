import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Asset = {
  id: string
  host: string
  ip: string
  role: string
  importance: string
  status: string
  owner: string
  note: string
}

const IMP_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 关键: 't', 高: 'warn', 中: 'dim', 低: 'dim' }
const ST_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 正常: 'ok', 观察: 'warn', 已隔离: 't', 下线: 'dim' }
const EMPTY = { host: '', ip: '', role: '', importance: '中', status: '正常', owner: '', note: '' }

export default function Cmdb() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [assets, setAssets] = useState<Asset[]>([])
  const [imps, setImps] = useState<string[]>(['关键', '高', '中', '低'])
  const [stats, setStats] = useState<string[]>(['正常', '观察', '已隔离', '下线'])
  const [editing, setEditing] = useState<string | null>(null)
  const [form, setForm] = useState({ ...EMPTY })
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ assets: Asset[]; importance_options: string[]; status_options: string[] }>('/api/assets').then((d) => {
      setAssets(d.assets)
      setImps(d.importance_options)
      setStats(d.status_options)
    })
  }
  useEffect(load, [])

  function startNew() {
    setEditing('new')
    setForm({ ...EMPTY })
  }
  function startEdit(a: Asset) {
    setEditing(a.id)
    setForm({ host: a.host, ip: a.ip, role: a.role, importance: a.importance, status: a.status, owner: a.owner, note: a.note })
  }

  async function save() {
    if (!form.host.trim()) return setMsg('主机名不能为空')
    try {
      if (editing === 'new') await apiPost('/api/assets', { ...form, actor })
      else await apiPut(`/api/assets/${editing}`, { ...form, actor })
      setMsg('已保存')
      setEditing(null)
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }

  async function remove(a: Asset) {
    await apiDelete(`/api/assets/${a.id}`)
    setMsg(`已删除 ${a.host}`)
    load()
  }

  const F = (k: keyof typeof form) => ({
    value: form[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm((f) => ({ ...f, [k]: e.target.value })),
    className: 'bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px]',
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <SectionTitle>资产清单 · CMDB（手填，分诊会引用「重要度」升级风险）</SectionTitle>
        <button className={btnPrimary} onClick={startNew}>+ 新增资产</button>
      </div>
      {msg && <div className="text-sage text-[13px] mb-2">{msg}</div>}

      {editing && (
        <Card className="mb-4">
          <SectionTitle>{editing === 'new' ? '新增资产' : `编辑 ${editing}`}</SectionTitle>
          <div className="grid grid-cols-4 gap-2">
            <input {...F('host')} placeholder="主机名*" />
            <input {...F('ip')} placeholder="IP" />
            <input {...F('role')} placeholder="角色，如 域控" />
            <input {...F('owner')} placeholder="负责人" />
            <select {...F('importance')}>{imps.map((i) => <option key={i} value={i}>{i}</option>)}</select>
            <select {...F('status')}>{stats.map((s) => <option key={s} value={s}>{s}</option>)}</select>
            <input {...F('note')} placeholder="备注" className={`${F('note').className} col-span-2`} />
          </div>
          <div className="flex gap-2 mt-3">
            <button className={btnPrimary} onClick={save}>保存</button>
            <button className={btnGhost} onClick={() => setEditing(null)}>取消</button>
          </div>
        </Card>
      )}

      <Card>
        <table className="w-full">
          <thead>
            <tr className="text-[12px] text-dim uppercase tracking-wide">
              <th className="text-left font-normal pb-2.5">主机</th>
              <th className="text-left font-normal pb-2.5">IP</th>
              <th className="text-left font-normal pb-2.5">角色</th>
              <th className="text-left font-normal pb-2.5">重要度</th>
              <th className="text-left font-normal pb-2.5">状态</th>
              <th className="text-left font-normal pb-2.5">负责人</th>
              <th className="text-right font-normal pb-2.5">操作</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{a.host}</td>
                <td className="py-3 text-dim">{a.ip}</td>
                <td className="py-3">{a.role}</td>
                <td className="py-3"><Pill tone={IMP_TONE[a.importance] || 'dim'}>{a.importance}</Pill></td>
                <td className="py-3"><Pill tone={ST_TONE[a.status] || 'dim'}>{a.status}</Pill></td>
                <td className="py-3 text-dim">{a.owner}</td>
                <td className="py-3 text-right whitespace-nowrap">
                  <button className="text-ochre hover:text-terra text-[13px] mr-3" onClick={() => startEdit(a)}>编辑</button>
                  <button className="text-dim hover:text-terra text-[13px]" onClick={() => remove(a)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
