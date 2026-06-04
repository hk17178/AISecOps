import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnPrimary, btnGhost } from '../components/ui'
import { apiGet, apiPost } from '../lib/api'
import { useAuth } from '../auth'

type ChainStep = { step: string; detail: string; refs: string[] }
type Conclusion = {
  is_incident: boolean
  title: string
  severity: string
  impact: string
  confidence: number
  attack_chain: ChainStep[]
  citations: string[]
  abstained?: boolean
  note?: string
}
type Cluster = { id: string; alert_ids: string[]; hosts: string[]; shared_ips: string[]; reason: string; size: number }
type Candidate = { cluster: Cluster; conclusion: Conclusion }
type SecEvent = { id: string; title: string; severity: string; alert_ids: string[]; status: string; ts: string }

export default function Correlate() {
  const { user } = useAuth()
  const [cands, setCands] = useState<Candidate[] | null>(null)
  const [events, setEvents] = useState<SecEvent[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const actor = user?.username || '未知'

  function loadEvents() {
    apiGet<{ events: SecEvent[] }>('/api/events').then((d) => setEvents(d.events)).catch(() => setEvents([]))
  }
  useEffect(loadEvents, [])

  async function run() {
    setBusy(true)
    setMsg('')
    try {
      const r = await apiPost<{ candidates: Candidate[] }>('/api/correlate', {})
      setCands(r.candidates)
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  async function confirm(c: Candidate) {
    const title = c.conclusion.title || `${c.cluster.hosts.join('/')} 关联事件`
    const ev = await apiPost<SecEvent>('/api/events/confirm', {
      title,
      severity: c.conclusion.severity || '高',
      summary: c.conclusion.impact,
      alert_ids: c.cluster.alert_ids,
      actor,
    })
    setMsg(`已确认为安全事件 ${ev.id}：${title}`)
    loadEvents()
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <button className={btnPrimary} onClick={run} disabled={busy}>
          {busy ? '分析中…' : '运行关联分析'}
        </button>
        <span className="text-dim text-[13px]">
          L08 规则/图把告警聚成候选事件簇 → 强模型出跨告警攻击链（每条结论附引用 C-24）
        </span>
        {msg && <span className="text-sage text-[13px]">{msg}</span>}
      </div>

      <div className="grid grid-cols-[1.8fr_1fr] gap-[34px] items-start">
        {/* 候选事件簇 + LLM 结论 */}
        <div className="flex flex-col gap-[18px]">
          {cands === null && <div className="text-dim text-[14px]">点「运行关联分析」生成候选事件簇。</div>}
          {cands?.length === 0 && <div className="text-dim text-[14px]">当前告警未发现可关联的事件簇。</div>}
          {cands?.map((c) => (
            <Card key={c.cluster.id}>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-serif font-semibold text-[15px]">{c.cluster.id}</span>
                <Pill tone="t">{c.cluster.size} 条告警</Pill>
                {c.conclusion.abstained ? (
                  <Pill tone="warn">待人工确认</Pill>
                ) : c.conclusion.is_incident ? (
                  <Pill tone="warn">疑似事件</Pill>
                ) : (
                  <Pill tone="ok">非事件</Pill>
                )}
                <span className="text-dim text-[12px] ml-auto">关联依据：{c.cluster.reason}</span>
              </div>

              <div className="text-[13px] text-dim mb-2">
                主机 {c.cluster.hosts.join('、') || '—'}
                {c.cluster.shared_ips.length > 0 && <> · IP {c.cluster.shared_ips.join('、')}</>}
                · 告警 {c.cluster.alert_ids.join(', ')}
              </div>

              {c.conclusion.abstained ? (
                <div className="text-ochre text-[13px] mb-2">
                  {c.conclusion.note || '置信度不足/离线，转人工确认'}（离线 stub 不臆造结论）
                </div>
              ) : (
                <>
                  <div className="text-[14px] mb-1">
                    <b>{c.conclusion.title || '（无定性）'}</b>
                    <span className="text-dim"> · {c.conclusion.severity} · 置信 {c.conclusion.confidence}</span>
                  </div>
                  {c.conclusion.impact && <div className="text-[13px] mb-2">影响面：{c.conclusion.impact}</div>}
                </>
              )}

              {/* 攻击链（每步带引用） */}
              {c.conclusion.attack_chain.length > 0 && (
                <div className="border-l-2 border-clay pl-3 mt-2 flex flex-col gap-2">
                  {c.conclusion.attack_chain.map((s, i) => (
                    <div key={i} className="text-[13px]">
                      <b>{i + 1}. {s.step}</b>
                      {s.detail && <span className="text-dim"> — {s.detail}</span>}
                      {s.refs.length > 0 && (
                        <span className="ml-1 text-[11px] text-terra">[{s.refs.join(', ')}]</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3">
                <button className={btnGhost} onClick={() => confirm(c)}>确认为安全事件</button>
              </div>
            </Card>
          ))}
        </div>

        {/* 已确认安全事件 */}
        <Card>
          <SectionTitle>已确认安全事件</SectionTitle>
          {events.length === 0 && <div className="text-dim text-[13px] py-2">暂无。确认候选簇后出现在这里。</div>}
          {events.map((e) => (
            <div key={e.id} className="py-2.5 border-b border-dotted border-line text-[13.5px]">
              <div className="flex items-center gap-2">
                <span className="text-dim font-mono text-[12px]">{e.id}</span>
                <Pill tone={e.severity === '严重' || e.severity === '高' ? 'warn' : 'dim'}>{e.severity}</Pill>
                <Pill tone="ok">{e.status}</Pill>
              </div>
              <div className="mt-1">{e.title}</div>
              <div className="text-dim text-[12px]">告警 {e.alert_ids.join(', ')} · {e.ts}</div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}
