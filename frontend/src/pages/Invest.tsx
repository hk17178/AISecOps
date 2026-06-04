import { useState } from 'react'
import { Card, SectionTitle, btnPrimary } from '../components/ui'
import { apiPost } from '../lib/api'

type TimelineItem = { time: string; event: string; source: string }
type InvestResult = {
  agent: string
  ok: boolean
  data: {
    summary: string
    attack_chain: string
    confidence: number
    timeline: TimelineItem[]
    log_count: number
  }
  abstained: boolean
  note: string
}

const inputCls = 'w-full border border-line rounded-lg bg-bg px-3 py-2.5 outline-none focus:border-clay'

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
        <Card>
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
      </div>
    </div>
  )
}
