import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle } from '../components/ui'
import { apiGet, apiPut } from '../lib/api'

type Item = {
  id: string
  action: string
  target: string
  risk: string
  status: string
  assignee: string
  progress: string
  sla_due: string
  overdue: boolean
  age_hours: number
  last_note: string
}
type Load = { assignee: string; open: number; overdue: number }
type Cockpit = { items: Item[]; workload: Load[]; counts: Record<string, number> }

const PROG = ['待处理', '处理中', '已完成', '已挂起']
const RISK_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 高: 't', 中: 'warn', 低: 'dim' }

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="flex-1 text-center">
      <div className={`text-[26px] font-serif ${tone || ''}`}>{value}</div>
      <div className="text-dim text-[12px]">{label}</div>
    </div>
  )
}

export default function Cockpit() {
  const [d, setD] = useState<Cockpit | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})

  function load() {
    apiGet<Cockpit>('/api/cockpit').then(setD)
  }
  useEffect(load, [])

  async function assign(id: string) {
    const who = (draft[`a${id}`] || '').trim()
    if (!who) return
    await apiPut(`/api/tickets/${id}/assign`, { assignee: who })
    load()
  }
  async function setProgress(id: string, progress: string) {
    await apiPut(`/api/tickets/${id}/progress`, { progress, note: draft[`n${id}`] || '' })
    load()
  }
  const c = d?.counts || {}

  return (
    <div className="flex flex-col gap-[28px]">
      {/* 汇总 */}
      <Card>
        <SectionTitle>协作驾驶舱 · 全局在办总览（管理层只读看进展，少打扰技术）</SectionTitle>
        <div className="flex gap-2 mt-2">
          <Stat label="在办" value={c.open || 0} />
          <Stat label="处理中" value={c.in_progress || 0} />
          <Stat label="已完成" value={c.done || 0} />
          <Stat label="待审批" value={c.pending_approval || 0} tone="text-clay" />
          <Stat label="超 SLA" value={c.overdue || 0} tone={c.overdue ? 'text-terra' : ''} />
          <Stat label="安全事件" value={c.events || 0} />
        </div>
      </Card>

      <div className="grid grid-cols-[1.7fr_1fr] gap-[28px] items-start">
        {/* 在办工单看板 */}
        <Card>
          <SectionTitle>在办工单 · 谁在处理 / 进展 / SLA</SectionTitle>
          {d?.items.length === 0 && <div className="text-sage text-[13px] py-2">当前无在办工单。</div>}
          {d?.items.map((it) => (
            <div key={it.id} className={`py-3 border-b border-dotted border-line ${it.overdue ? 'bg-terra/5' : ''}`}>
              <div className="flex items-center gap-2 flex-wrap text-[14px]">
                <span className="font-mono text-[12px] text-dim">{it.id}</span>
                <span>{it.action} · {it.target}</span>
                <Pill tone={RISK_TONE[it.risk] || 'dim'}>{it.risk}</Pill>
                <Pill tone="dim">{it.status}</Pill>
                {it.overdue && <Pill tone="t">超 SLA</Pill>}
                <span className="text-dim text-[12px] ml-auto">已 {it.age_hours}h · 限 {it.sla_due.slice(5, 16)}</span>
              </div>
              {it.last_note && <div className="text-dim text-[12px] mt-1">最新：{it.last_note}</div>}
              <div className="flex gap-2 mt-2 items-center flex-wrap">
                <input
                  defaultValue={it.assignee}
                  onChange={(e) => setDraft({ ...draft, [`a${it.id}`]: e.target.value })}
                  placeholder="指派给…"
                  className="w-28 bg-paper2 border border-line rounded px-2 py-1 text-[12px]"
                />
                <button onClick={() => assign(it.id)} className="text-sage hover:underline text-[12px]">指派</button>
                <span className="text-line">|</span>
                <span className="text-dim text-[12px]">进度：{it.progress}</span>
                {PROG.map((p) => (
                  <button key={p} onClick={() => setProgress(it.id, p)}
                    className={`text-[12px] px-1.5 py-0.5 rounded ${it.progress === p ? 'bg-clay/15 text-clay' : 'text-dim hover:text-clay'}`}>
                    {p}
                  </button>
                ))}
                <input
                  onChange={(e) => setDraft({ ...draft, [`n${it.id}`]: e.target.value })}
                  placeholder="进展备注（可空）"
                  className="flex-1 min-w-[120px] bg-paper2 border border-line rounded px-2 py-1 text-[12px]"
                />
              </div>
            </div>
          ))}
        </Card>

        {/* 按处理人负载 */}
        <Card>
          <SectionTitle>按处理人负载</SectionTitle>
          {d?.workload.length === 0 && <div className="text-dim text-[13px]">暂无在办。</div>}
          {d?.workload.map((w) => (
            <div key={w.assignee} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[13.5px]">
              <span>{w.assignee}</span>
              <span className="flex gap-2 items-center">
                <Pill tone="dim">在办 {w.open}</Pill>
                {w.overdue > 0 && <Pill tone="t">超时 {w.overdue}</Pill>}
              </span>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}
