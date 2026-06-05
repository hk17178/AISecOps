import { useEffect, useState } from 'react'
import FlipCard, { type BackRow } from '../components/FlipCard'
import { Card, Pill, SectionTitle } from '../components/ui'
import { apiGet } from '../lib/api'

type RecentAlert = {
  id: string; ts: string; host: string; source: string; severity: string; title: string; verdict: string; confidence: number
}
type Dash = {
  total: number; threats: number; pending: number
  by_severity: Record<string, number>; by_source: Record<string, number>; by_verdict: Record<string, number>
  recent: RecentAlert[]
  spent_cny: number; monthly_cap_cny: number; triage_calls: number
  trend: { date: string; count: number }[]
  dedupe_reduction: number
  ticket_board: { pending: number; in_progress: number; done: number; overdue: number }
  mttr_hours: number; events: number
  knowledge: { total: number; from_flywheel: number }
  cost_by_scenario: Record<string, number>
}

const SEV_DOT: Record<string, string> = { 严重: 'bg-terra', 高: 'bg-ochre', 中: 'bg-sage', 低: 'bg-clay' }
const VERDICT_CLS: Record<string, string> = { 真威胁: 'text-terra', 待研判: 'text-ochre', 误报: 'text-dim', 新: 'text-dim' }
const VERDICT_BAR: Record<string, string> = { 真威胁: 'bg-terra', 待研判: 'bg-ochre', 误报: 'bg-line', 新: 'bg-sage' }

function rows(o: Record<string, number>): BackRow[] {
  const r = Object.entries(o).map(([k, v]) => ({ k, v: String(v) }))
  return r.length ? r : [{ k: '(暂无)', v: '—' }]
}

function Bars({ data, color = 'bg-clay' }: { data: [string, number][]; color?: string }) {
  const max = Math.max(1, ...data.map(([, v]) => v))
  return (
    <div className="flex flex-col gap-1.5">
      {data.length === 0 && <div className="text-dim text-[13px]">暂无数据</div>}
      {data.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-[12.5px]">
          <span className="w-20 shrink-0 text-dim truncate">{k}</span>
          <div className="flex-1 h-3 bg-paper2 rounded-full overflow-hidden">
            <div className={`h-full ${color} rounded-full bar-grow`} style={{ width: `${(v / max) * 100}%` }} />
          </div>
          <span className="w-8 text-right">{v}</span>
        </div>
      ))}
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="flex-1 text-center">
      <div className={`text-[24px] font-serif ${tone || ''}`}>{value}</div>
      <div className="text-dim text-[12px]">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const [d, setD] = useState<Dash | null>(null)
  useEffect(() => {
    apiGet<Dash>('/api/dashboard').then(setD).catch(() => setD(null))
  }, [])
  if (!d) return <div className="text-dim">加载中…</div>
  const pct = d.monthly_cap_cny ? Math.round((d.spent_cny / d.monthly_cap_cny) * 100) : 0
  const tb = d.ticket_board

  return (
    <div className="flex flex-col gap-[26px]">
      <div className="grid grid-cols-4 gap-[18px]">
        <FlipCard label="告警总数" value={String(d.total)} delay={0} back={rows(d.by_severity)} />
        <FlipCard label="真威胁" value={String(d.threats)} valueClass="text-terra" delay={80} back={rows(d.by_source)} />
        <FlipCard label="待研判" value={String(d.pending)} valueClass="text-ochre" delay={160} back={[{ k: '分诊调用', v: String(d.triage_calls) }]} />
        <FlipCard label="本月成本" value={`¥${d.spent_cny}`} delay={240} back={[{ k: '上限', v: `¥${d.monthly_cap_cny}` }]} />
      </div>

      {/* 趋势 + 研判分布 */}
      <div className="grid grid-cols-2 gap-[26px]">
        <Card>
          <SectionTitle>告警趋势 · 近 7 天（降噪后）</SectionTitle>
          <Bars data={d.trend.map((t) => [t.date.slice(5), t.count])} color="bg-clay" />
        </Card>
        <Card>
          <SectionTitle>研判分布</SectionTitle>
          <div className="flex flex-col gap-1.5 mt-1">
            {Object.entries(d.by_verdict).length === 0 && <div className="text-dim text-[13px]">暂无</div>}
            {Object.entries(d.by_verdict).map(([k, v]) => {
              const max = Math.max(1, ...Object.values(d.by_verdict))
              return (
                <div key={k} className="flex items-center gap-2 text-[12.5px]">
                  <span className={`w-16 shrink-0 ${VERDICT_CLS[k] || 'text-dim'}`}>{k}</span>
                  <div className="flex-1 h-3 bg-paper2 rounded-full overflow-hidden">
                    <div className={`h-full ${VERDICT_BAR[k] || 'bg-clay'} rounded-full bar-grow`} style={{ width: `${(v / max) * 100}%` }} />
                  </div>
                  <span className="w-8 text-right">{v}</span>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* 工单看板 + 运营指标 */}
      <div className="grid grid-cols-2 gap-[26px]">
        <Card>
          <SectionTitle>HITL 工单看板 · 协作态</SectionTitle>
          <div className="flex gap-2 mt-2">
            <Stat label="待审批" value={tb.pending} tone="text-clay" />
            <Stat label="处理中" value={tb.in_progress} />
            <Stat label="已完成" value={tb.done} tone="text-sage" />
            <Stat label="超 SLA" value={tb.overdue} tone={tb.overdue ? 'text-terra' : ''} />
          </div>
          <div className="mt-3 text-dim text-[12px]">
            平均处置时长 MTTR：<b className="text-fg">{d.mttr_hours}h</b> · 已确认安全事件 {d.events}
          </div>
        </Card>
        <Card>
          <SectionTitle>运营健康度</SectionTitle>
          <div className="flex justify-between items-center text-[13px] mb-2">
            <span>降噪率</span>
            <span className="text-sage font-serif text-[18px]">{d.dedupe_reduction}%</span>
          </div>
          <div className="h-2 bg-paper2 rounded-full overflow-hidden mb-3">
            <div className="h-full bg-sage rounded-full bar-grow" style={{ width: `${d.dedupe_reduction}%` }} />
          </div>
          <div className="flex justify-between items-center text-[13px]">
            <span>知识库沉淀（反馈飞轮）</span>
            <span>
              <Pill tone="ok">共 {d.knowledge.total}</Pill>{' '}
              <Pill tone="warn">飞轮 {d.knowledge.from_flywheel}</Pill>
            </span>
          </div>
          <div className="mt-3 flex justify-between items-center text-[13px]">
            <span>本月预算</span>
            <span className="text-ochre border border-ochre rounded-full px-2 text-[12px]">{pct}%</span>
          </div>
          <div className="h-2 bg-paper2 rounded-full mt-1.5 overflow-hidden">
            <div className="h-full bg-terra rounded-full bar-grow" style={{ width: `${pct}%` }} />
          </div>
        </Card>
      </div>

      {/* 最新告警 + 成本按场景 */}
      <div className="grid grid-cols-[1.7fr_1fr] gap-[26px]">
        <Card>
          <SectionTitle>最新告警 · 真实告警库</SectionTitle>
          {d.recent.map((a) => (
            <div key={a.id} className="flex items-center justify-between py-2.5 border-b border-dotted border-line">
              <span className="flex items-center gap-2">
                <span className={`inline-block w-2 h-2 rounded-full ${SEV_DOT[a.severity] || 'bg-clay'} ${a.severity === '严重' ? 'pulse-dot' : ''}`} />
                <span className="text-dim text-[13px] w-12">{a.ts.slice(11, 16)}</span>
                <span>{a.title} · {a.host}</span>
              </span>
              <span className={`font-semibold ${VERDICT_CLS[a.verdict] || 'text-dim'}`}>{a.verdict}</span>
            </div>
          ))}
          {d.recent.length === 0 && <div className="text-dim py-4">暂无告警（接 SIEM webhook 或 POST /api/ingest/alert）</div>}
        </Card>
        <Card>
          <SectionTitle>LLM 成本 · 按场景（¥）</SectionTitle>
          <Bars data={Object.entries(d.cost_by_scenario).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, v])} color="bg-ochre" />
          {Object.keys(d.cost_by_scenario).length === 0 && <div className="text-dim text-[13px]">暂无 LLM 调用（配 LLM_API_KEY 后出真实成本）</div>}
        </Card>
      </div>
    </div>
  )
}
