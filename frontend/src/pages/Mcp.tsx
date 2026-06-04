import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Adapter = {
  id: string
  name: string
  category: string
  kind: string
  endpoint: string
  enabled: boolean
  last_status: string
  last_tested: string
  runtime?: string
}

const ST_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 已连: 'ok', 失败: 't', 未配置: 'dim', 未测: 'dim' }

export default function Mcp() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [adapters, setAdapters] = useState<Adapter[]>([])
  const [cats, setCats] = useState<string[]>([])
  const [outbound, setOutbound] = useState(false)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('data_sources')
  const [kind, setKind] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ adapters: Adapter[]; categories: string[]; outbound_enabled: boolean }>('/api/tools').then((d) => {
      setAdapters(d.adapters)
      setCats(d.categories)
      setOutbound(d.outbound_enabled)
    })
  }
  useEffect(load, [])

  async function add() {
    if (!name.trim()) return setMsg('适配器名不能为空')
    await apiPost('/api/tools', { name: name.trim(), category, kind: kind.trim(), endpoint: endpoint.trim(), actor })
    setMsg(`已新增适配器「${name.trim()}」`)
    setName(''); setKind(''); setEndpoint('')
    load()
  }
  async function test(a: Adapter) {
    const r = await apiPost<Adapter>(`/api/tools/${a.id}/test`, {})
    setMsg(`测试 ${a.name}：${r.last_status}`)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <SectionTitle>工具适配器 · 薄适配器（ADR-0004）增删/启停/测连</SectionTitle>
        <Pill tone={outbound ? 'ok' : 'warn'}>{outbound ? '出域开 · 外网端点可测' : '出域关 · 外网端点测连跳过'}</Pill>
      </div>
      {msg && <div className="text-sage text-[13px] mb-2">{msg}</div>}

      <Card>
        <table className="w-full">
          <thead>
            <tr className="text-[12px] text-dim uppercase tracking-wide">
              <th className="text-left font-normal pb-2.5">名称</th>
              <th className="text-left font-normal pb-2.5">分类</th>
              <th className="text-left font-normal pb-2.5">端点</th>
              <th className="text-left font-normal pb-2.5">状态</th>
              <th className="text-right font-normal pb-2.5">操作</th>
            </tr>
          </thead>
          <tbody>
            {adapters.map((a) => (
              <tr key={a.id} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{a.name}<div className="text-dim text-[11px]">{a.kind}</div></td>
                <td className="py-3 text-dim text-[13px]">{a.category}</td>
                <td className="py-3 text-dim text-[12px] font-mono max-w-[200px] truncate">{a.endpoint || '—'}</td>
                <td className="py-3">
                  <Pill tone={ST_TONE[a.last_status] || 'dim'}>{a.last_status}</Pill>
                  {a.runtime && <div className="text-dim text-[11px] mt-0.5">{a.runtime}</div>}
                </td>
                <td className="py-3 text-right whitespace-nowrap">
                  <button className="text-ochre hover:text-terra text-[13px] mr-3" onClick={() => test(a)}>测连</button>
                  <button onClick={async () => { await apiPut(`/api/tools/${a.id}`, { enabled: !a.enabled, actor }); load() }}
                    className={`text-[12px] border rounded-full px-2 mr-3 ${a.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                    {a.enabled ? '启用' : '停用'}
                  </button>
                  <button className="text-dim hover:text-terra text-[13px]" onClick={async () => { await apiDelete(`/api/tools/${a.id}`); load() }}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mt-4 max-w-[760px]">
        <SectionTitle>新增适配器</SectionTitle>
        <div className="grid grid-cols-4 gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="名称*"
            className="bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px]" />
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px]">
            {cats.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input value={kind} onChange={(e) => setKind(e.target.value)} placeholder="kind，如 siem"
            className="bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px]" />
          <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="探测端点 URL（可空）"
            className="bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px] font-mono" />
        </div>
        <button className={`${btnPrimary} mt-3`} onClick={add}>+ 新增适配器</button>
        <span className={`${btnGhost} ml-2`} onClick={load} role="button">刷新</span>
      </Card>
    </div>
  )
}
