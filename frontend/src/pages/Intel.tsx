import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost } from '../lib/api'
import { useAuth } from '../auth'

type IoC = { id: string; value: string; type: string; severity: string; note: string; hits: number }
type AlertRow = { id: string; host: string; title: string; verdict: string; ioc_hits: string[] }

const SEV_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 高: 't', 中: 'warn', 低: 'dim' }

export default function Intel() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [iocs, setIocs] = useState<IoC[]>([])
  const [types, setTypes] = useState<string[]>(['域名', 'IP', '哈希', 'URL'])
  const [hitAlerts, setHitAlerts] = useState<AlertRow[]>([])
  const [value, setValue] = useState('')
  const [type, setType] = useState('域名')
  const [severity, setSeverity] = useState('高')
  const [note, setNote] = useState('')
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ iocs: IoC[]; type_options: string[] }>('/api/iocs').then((d) => {
      setIocs(d.iocs)
      setTypes(d.type_options)
    })
    apiGet<{ alerts: AlertRow[] }>('/api/alerts').then((d) => setHitAlerts(d.alerts.filter((a) => a.ioc_hits?.length)))
  }
  useEffect(load, [])

  async function add() {
    if (!value.trim()) return setMsg('IoC 值不能为空')
    try {
      await apiPost('/api/iocs', { value: value.trim(), type, severity, note: note.trim(), actor })
      setMsg(`已新增 IoC「${value.trim()}」`)
      setValue('')
      setNote('')
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }

  async function remove(i: IoC) {
    await apiDelete(`/api/iocs/${i.id}`)
    setMsg(`已删除 ${i.value}`)
    load()
  }

  return (
    <div className="grid grid-cols-[1.3fr_1fr] gap-[34px] items-start">
      {/* IoC 库 + CRUD */}
      <Card>
        <SectionTitle>威胁情报 IoC · 增删（命中告警自动标红 + 计数）</SectionTitle>
        {iocs.map((i) => (
          <div key={i.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono">{i.value}</span>
                <Pill tone={SEV_TONE[i.severity] || 'dim'}>{i.type}</Pill>
              </div>
              <div className="text-dim text-[12px]">{i.note || '—'} · 命中 {i.hits} 次</div>
            </span>
            <button onClick={() => remove(i)} className="text-dim hover:text-terra text-[16px] leading-none shrink-0" title="删除">×</button>
          </div>
        ))}
        <div className="mt-4 flex flex-col gap-2">
          <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="IoC 值，如 evil-c2.top"
            className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] font-mono" />
          <div className="flex gap-2">
            <select value={type} onChange={(e) => setType(e.target.value)}
              className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
              {types.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}
              className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
              <option value="高">高</option><option value="中">中</option><option value="低">低</option>
            </select>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="备注（可空）"
              className="flex-1 min-w-0 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
          </div>
          <button className={btnPrimary} onClick={add}>+ 新增 IoC</button>
          {msg && <div className="text-sage text-[13px]">{msg}</div>}
        </div>
      </Card>

      {/* 命中告警（标红体现） */}
      <Card>
        <SectionTitle>IoC 命中告警 · 标红</SectionTitle>
        {hitAlerts.length === 0 && <div className="text-dim text-[13px] py-2">当前无告警命中情报库。灌一条含 IoC 值的告警即出现。</div>}
        {hitAlerts.map((a) => (
          <div key={a.id} className="py-2.5 border-b border-dotted border-line text-[13.5px]">
            <div className="flex items-center gap-2">
              <span className="text-dim font-mono text-[12px]">{a.id}</span>
              <span className="text-terra font-semibold">命中</span>
              <Pill tone={a.verdict === '真威胁' ? 't' : 'dim'}>{a.verdict}</Pill>
            </div>
            <div className="mt-1">{a.host} · {a.title}</div>
            <div className="text-terra text-[12px] mt-0.5">IoC：{a.ioc_hits.join('、')}</div>
          </div>
        ))}
        <div className="mt-3">
          <a className={btnGhost} href="/dedupe" onClick={(e) => { e.preventDefault(); load() }}>刷新</a>
        </div>
      </Card>
    </div>
  )
}
