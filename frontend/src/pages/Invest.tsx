import { useState } from 'react'
import { Card, Pill, SectionTitle, btnPrimary } from '../components/ui'
import { apiPost } from '../lib/api'

type TimelineItem = { time: string; event: string; source: string }
type KillChain = { stages_hit: string[]; depth: number; coverage: number; summary: string }
type AttackGraph = { pivots: { node: string; degree: number }[]; paths: string[][]; node_count: number }
type Ueba = { entity: string; risk: number; reasons: string[] }
type Compromise = { host: string; score: number; level: string; reasons: string[] }
type InvestResult = {
  agent: string
  ok: boolean
  data: {
    summary: string
    attack_chain: string
    confidence: number
    timeline: TimelineItem[]
    log_count: number
    kill_chain: KillChain
    attack_graph: AttackGraph
    ueba: Ueba[]
    compromise: Compromise
  }
  abstained: boolean
  note: string
}

const inputCls = 'w-full border border-line rounded-lg bg-bg px-3 py-2.5 outline-none focus:border-clay'
const LEVEL_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 低: 'dim', 中: 'warn', 高: 't', 危急: 't' }
const KC_STAGES = ['侦察', '武器化', '投递', '利用', '安装', '命令控制', '目标行动']

export default function Invest() {
  const [host, setHost] = useState('WIN-APP-07')
  const [question, setQuestion] = useState('这次入侵的攻击链是什么？')
  const [r, setR] = useState<InvestResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    setR(null)
    try {
      setR(await apiPost<InvestResult>('/api/investigate', { host, question }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
      <Card>
        <SectionTitle>攻击时间线{r ? ` · ${r.data.log_count} 条日志（来自 ES）` : ''}</SectionTitle>
        {!r && <div className="text-dim">（在右侧填主机/问题，点"开始调查"）</div>}
        {r && r.data.timeline.length === 0 && <div className="text-dim">无相关日志</div>}
        {r &&
          r.data.timeline.map((t, i) => (
            <div key={i} className="flex gap-3 py-3 border-b border-dotted border-line fade-up" style={{ animationDelay: `${i * 80}ms` }}>
              <span className="text-terra font-semibold w-16">{t.time}</span>
              <div>
                <div>{t.event}</div>
                <div className="text-dim text-[12px] mt-0.5">{t.source}</div>
              </div>
            </div>
          ))}
      </Card>

      <div>
        <Card className="mb-5">
          <SectionTitle>调查</SectionTitle>
          <label className="block text-[13px] text-dim mb-1.5">主机</label>
          <input value={host} onChange={(e) => setHost(e.target.value)} className={`${inputCls} mb-3`} />
          <label className="block text-[13px] text-dim mb-1.5">问题</label>
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} className={`${inputCls} mb-3 min-h-[70px]`} />
          <button onClick={run} disabled={loading} className={btnPrimary}>
            {loading ? '调查中…' : '开始调查'}
          </button>
        </Card>
        <Card className="mb-5">
          <SectionTitle>调查结论</SectionTitle>
          {!r && <div className="text-dim">—</div>}
          {r && (
            <div>
              <div className="text-[14px] mb-2">{r.data.summary || '（无模型 / 证据不足，需人工）'}</div>
              {r.data.attack_chain && (
                <div className="text-[13px] text-dim mb-2">攻击链：{r.data.attack_chain}</div>
              )}
              <div className="text-dim text-[12px]">
                置信度 {r.data.confidence.toFixed(2)} · {r.abstained ? '转人工' : '已研判'}
              </div>
              {r.note && <div className="text-ochre text-[13px] mt-2">{r.note}</div>}
            </div>
          )}
        </Card>

        {r && (
          <Card>
            <SectionTitle>安全算法分析 · L08（确定性）</SectionTitle>
            {/* 失陷研判 */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[13px] text-dim">失陷研判</span>
              <Pill tone={LEVEL_TONE[r.data.compromise.level] || 'dim'}>
                {r.data.compromise.level} · {r.data.compromise.score}
              </Pill>
            </div>
            {r.data.compromise.reasons.length > 0 && (
              <div className="text-dim text-[12px] mb-3">{r.data.compromise.reasons.join('；')}</div>
            )}

            {/* Kill Chain 进度 */}
            <div className="text-[13px] text-dim mb-1.5">Kill Chain · {r.data.kill_chain.summary}</div>
            <div className="flex gap-1 mb-3 flex-wrap">
              {KC_STAGES.map((s, i) => {
                const hit = r.data.kill_chain.stages_hit.includes(s)
                const reached = i < r.data.kill_chain.depth
                return (
                  <span
                    key={s}
                    className={`text-[11px] px-1.5 py-0.5 rounded ${
                      hit ? 'bg-terra/15 text-terra' : reached ? 'bg-line/40 text-dim' : 'text-dim/50'
                    }`}
                  >
                    {s}
                  </span>
                )
              })}
            </div>

            {/* 攻击图枢纽 + 路径 */}
            {r.data.attack_graph.pivots.length > 0 && (
              <div className="text-[12px] mb-1">
                <span className="text-dim">攻击图枢纽：</span>
                {r.data.attack_graph.pivots.slice(0, 3).map((p) => `${p.node}(度${p.degree})`).join('、')}
              </div>
            )}
            {r.data.attack_graph.paths.length > 0 && (
              <div className="text-[12px] mb-2 text-terra">
                可达路径：{r.data.attack_graph.paths.map((p) => p.join('→')).join(' ｜ ')}
              </div>
            )}

            {/* UEBA Top */}
            {r.data.ueba.length > 0 && (
              <div className="text-[12px] mt-2">
                <span className="text-dim">UEBA 高风险：</span>
                {r.data.ueba.slice(0, 3).map((u) => `${u.entity}(${u.risk})`).join('、')}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
