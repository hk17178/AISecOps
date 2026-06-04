import { useEffect, useState } from 'react'
import FlipCard, { type BackRow } from '../components/FlipCard'
import { Card, SectionTitle } from '../components/ui'
import { apiGet } from '../lib/api'

type RecentAlert = {
  id: string
  ts: string
  host: string
  source: string
  severity: string
  title: string
  verdict: string
  confidence: number
}

type Dash = {
  total: number
  threats: number
  pending: number
  by_severity: Record<string, number>
  by_source: Record<string, number>
  recent: RecentAlert[]
  spent_cny: number
  monthly_cap_cny: number
  triage_calls: number
}

const SEV_DOT: Record<string, string> = { 严重: 'bg-terra', 高: 'bg-ochre', 中: 'bg-sage', 低: 'bg-clay' }
const VERDICT_CLS: Record<string, string> = { 真威胁: 'text-terra', 待研判: 'text-ochre', 误报: 'text-dim', 新: 'text-dim' }

function rows(o: Record<string, number>): BackRow[] {
  const r = Object.entries(o).map(([k, v]) => ({ k, v: String(v) }))
  return r.length ? r : [{ k: '(暂无)', v: '—' }]
}

export default function Dashboard() {
  const [d, setD] = useState<Dash | null>(null)

  useEffect(() => {
    apiGet<Dash>('/api/dashboard').then(setD).catch(() => setD(null))
  }, [])

  if (!d) return <div className="text-dim">加载中…</div>
  const pct = d.monthly_cap_cny ? Math.round((d.spent_cny / d.monthly_cap_cny) * 100) : 0

  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="告警总数" value={String(d.total)} delay={0} back={rows(d.by_severity)} />
        <FlipCard label="真威胁" value={String(d.threats)} valueClass="text-terra" delay={80} back={rows(d.by_source)} />
        <FlipCard label="待研判" value={String(d.pending)} valueClass="text-ochre" delay={160}
          back={[{ k: '分诊调用', v: String(d.triage_calls) }]} />
        <FlipCard label="本月成本" value={`¥${d.spent_cny}`} delay={240}
          back={[{ k: '上限', v: `¥${d.monthly_cap_cny}` }]} />
      </div>

      <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
        <Card>
          <SectionTitle>最新告警 · 真实告警库</SectionTitle>
          {d.recent.map((a) => (
            <div key={a.id} className="flex items-center justify-between py-2.5 border-b border-dotted border-line">
              <span className="flex items-center gap-2">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${SEV_DOT[a.severity] || 'bg-clay'} ${
                    a.severity === '严重' ? 'pulse-dot' : ''
                  }`}
                />
                <span className="text-dim text-[13px] w-12">{a.ts.slice(11, 16)}</span>
                <span>{a.title} · {a.host}</span>
              </span>
              <span className={`font-semibold ${VERDICT_CLS[a.verdict] || 'text-dim'}`}>{a.verdict}</span>
            </div>
          ))}
          {d.recent.length === 0 && <div className="text-dim py-4">暂无告警（接 SIEM webhook 或 POST /api/ingest/alert）</div>}
        </Card>
        <Card>
          <SectionTitle>本月预算</SectionTitle>
          <div className="flex justify-between py-2.5">
            <span>¥{d.spent_cny} / ¥{d.monthly_cap_cny}</span>
            <span className="text-ochre border border-ochre rounded-full px-2 text-[12px]">{pct}%</span>
          </div>
          <div className="h-2 bg-paper2 rounded-full mt-1.5 overflow-hidden">
            <div className="h-full bg-terra rounded-full bar-grow" style={{ width: `${pct}%` }} />
          </div>
        </Card>
      </div>
    </div>
  )
}
