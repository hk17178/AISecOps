import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiGet, apiPost } from '../lib/api'
import { useAuth } from '../auth'

type ReportMeta = { id: string; kind: string; title: string; summary: string; ts: string }
type ReportFull = ReportMeta & { markdown: string }
type Event = { id: string; title: string }

const KINDS = [
  { kind: 'daily', name: '安全日报', desc: '今日告警/真威胁/降噪/处置概览，管理层简版。' },
  { kind: 'weekly', name: '安全周报', desc: '本周趋势 + 关键指标 + 处置统计。' },
  { kind: 'incident', name: '事件复盘', desc: '选一个已确认安全事件，生成复盘报告。' },
]
const KIND_LABEL: Record<string, string> = { daily: '日报', weekly: '周报', incident: '复盘' }

export default function Report() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [list, setList] = useState<ReportMeta[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [current, setCurrent] = useState<ReportFull | null>(null)
  const [eventId, setEventId] = useState('')
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ reports: ReportMeta[] }>('/api/reports').then((d) => setList(d.reports))
    apiGet<{ events: Event[] }>('/api/events').then((d) => {
      setEvents(d.events)
      if (!eventId && d.events[0]) setEventId(d.events[0].id)
    })
  }
  useEffect(load, [])

  async function gen(kind: string) {
    if (kind === 'incident' && !eventId) return setMsg('请先在「关联分析」确认一个安全事件')
    setBusy(kind)
    setMsg('')
    try {
      const r = await apiPost<ReportFull>('/api/reports/generate', { kind, event_id: kind === 'incident' ? eventId : '', actor })
      setCurrent(r)
      load()
    } catch (e) {
      setMsg(`生成失败：${(e as Error).message}`)
    } finally {
      setBusy('')
    }
  }

  async function open(id: string) {
    const r = await apiGet<ReportFull>(`/api/reports/${id}`)
    setCurrent(r)
  }

  function exportMd(id: string) {
    // 直接下载后端导出的 .md（带 Content-Disposition）
    window.open(`/api/reports/${id}/export`, '_blank')
  }

  return (
    <div>
      <SectionTitle>报告模板 · 从真实数据一键生成</SectionTitle>
      <div className="grid grid-cols-3 gap-[18px] mb-2">
        {KINDS.map((t) => (
          <div key={t.kind} className="bg-paper border border-line rounded-[10px] p-[18px] lift">
            <div className="font-semibold mb-1.5">{t.name}</div>
            <p className="text-[13px] text-dim min-h-[40px]">{t.desc}</p>
            {t.kind === 'incident' && (
              <select value={eventId} onChange={(e) => setEventId(e.target.value)}
                className="w-full mb-2 bg-paper2 border border-line rounded-lg px-2 py-1.5 text-[13px]">
                {events.length === 0 && <option value="">（暂无安全事件）</option>}
                {events.map((ev) => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
              </select>
            )}
            <button onClick={() => gen(t.kind)} disabled={busy === t.kind} className={btnPrimary}>
              {busy === t.kind ? '生成中…' : '生成'}
            </button>
          </div>
        ))}
      </div>
      {msg && <div className="text-ochre text-[13px] mb-3">{msg}</div>}

      <div className="grid grid-cols-[1fr_300px] gap-[34px] items-start mt-4">
        {/* 预览 */}
        <Card>
          <div className="flex items-center justify-between mb-3">
            <SectionTitle>{current ? current.title : '报告预览'}</SectionTitle>
            {current && (
              <button className={btnGhost} onClick={() => exportMd(current.id)}>导出 Markdown</button>
            )}
          </div>
          {current ? (
            <pre className="whitespace-pre-wrap text-[13px] leading-relaxed font-mono bg-paper2 rounded-lg p-4 max-h-[560px] overflow-auto">
              {current.markdown}
            </pre>
          ) : (
            <div className="text-dim text-[14px] py-10 text-center">点上方「生成」从真实数据出一份报告，可预览与导出。</div>
          )}
        </Card>

        {/* 历史 */}
        <Card>
          <SectionTitle>历史报告</SectionTitle>
          {list.length === 0 && <div className="text-dim text-[13px] py-2">暂无</div>}
          {list.map((r) => (
            <div key={r.id} className="py-2.5 border-b border-dotted border-line text-[13.5px]">
              <div className="flex items-center gap-2">
                <Pill tone="dim">{KIND_LABEL[r.kind] || r.kind}</Pill>
                <button className="text-terra hover:underline truncate" onClick={() => open(r.id)}>{r.title}</button>
              </div>
              <div className="text-dim text-[12px] mt-0.5">{r.ts}</div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}
