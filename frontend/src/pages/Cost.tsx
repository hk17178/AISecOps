import { useEffect, useState } from 'react'
import FlipCard, { type BackRow } from '../components/FlipCard'
import { Card, Pill, Row, SectionTitle } from '../components/ui'
import { apiGet } from '../lib/api'

type CostData = {
  monthly_cap_cny: number
  spent_cny: number
  remaining_cny: number
  total_calls: number
  total_tokens: number
  by_provider: Record<string, number>
  by_scenario: Record<string, number>
  providers: { name: string; model: string; outbound: boolean }[]
}

function toRows(obj: Record<string, number>, empty: string): BackRow[] {
  const rows = Object.entries(obj).map(([k, v]) => ({ k, v: String(v) }))
  return rows.length ? rows : [{ k: empty, v: '—' }]
}

export default function Cost() {
  const [c, setC] = useState<CostData | null>(null)

  useEffect(() => {
    apiGet<CostData>('/api/cost').then(setC).catch(() => setC(null))
  }, [])

  if (!c) return <div className="text-dim">加载中…</div>

  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="本月成本" value={`¥${c.spent_cny}`} valueClass="text-terra" delay={0}
          back={[{ k: '上限', v: `¥${c.monthly_cap_cny}` }, { k: '余量', v: `¥${c.remaining_cny}` }]} />
        <FlipCard label="调用次数" value={String(c.total_calls)} delay={80}
          back={toRows(c.by_scenario, '(暂无调用)')} />
        <FlipCard label="Token 总量" value={String(c.total_tokens)} delay={160}
          back={toRows(c.by_provider, '(暂无)')} />
        <FlipCard label="预算余量" value={`¥${c.remaining_cny}`} valueClass="text-ochre" delay={240}
          back={[{ k: '上限', v: `¥${c.monthly_cap_cny}` }, { k: '已用', v: `¥${c.spent_cny}` }]} />
      </div>
      <Card className="max-w-[760px]">
        <SectionTitle>Provider 路由 · 真实配置（来自 .env）</SectionTitle>
        {c.providers.map((p) => (
          <Row key={p.name}>
            <span>
              {p.name} <span className="text-dim text-[13px]">{p.model}</span>
            </span>
            <Pill tone={p.outbound ? 'warn' : 'ok'}>{p.outbound ? '出域' : '本地'}</Pill>
          </Row>
        ))}
      </Card>
      <div className="text-dim text-[13px] mt-3">
        数字为本进程真实统计；离线 stub 下成本为 0，调用后实时累计。
      </div>
    </div>
  )
}
