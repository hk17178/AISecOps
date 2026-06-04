import { Card, Pill, Row, SectionTitle } from '../components/ui'

const IOCS = [
  { v: 'evil-c2[.]top', type: '域名', tone: 't' as const, note: '命中 1 主机 · 09:31' },
  { v: '185.220.x.x', type: 'IP', tone: 't' as const, note: 'Tor 出口 · 高危' },
  { v: 'a1b2…f9', type: '哈希', tone: 'warn' as const, note: 'PsExec 变体' },
]

export default function Intel() {
  return (
    <div>
      <SectionTitle>最新 IoC</SectionTitle>
      <Card>
        {IOCS.map((i) => (
          <Row key={i.v}>
            <span className="flex items-center gap-2">
              {i.v} <Pill tone={i.tone}>{i.type}</Pill>
            </span>
            <span className="text-dim text-[13px]">{i.note}</span>
          </Row>
        ))}
      </Card>
    </div>
  )
}
