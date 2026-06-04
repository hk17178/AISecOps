import { Card, Row, SectionTitle } from '../components/ui'

const PROMPTS = [
  { path: 'triage/system.md', ver: 'v7 · 3 天前' },
  { path: 'investigation/system.md', ver: 'v4 · 1 周前' },
  { path: 'reporter/daily.md', ver: 'v2 · 2 周前' },
]

export default function Prompt() {
  return (
    <div>
      <SectionTitle>Prompt 版本 · git 管理（P-6 从 Day 1）</SectionTitle>
      <Card>
        {PROMPTS.map((p) => (
          <Row key={p.path}>
            <span>{p.path}</span>
            <span className="text-dim text-[13px]">{p.ver}</span>
          </Row>
        ))}
      </Card>
    </div>
  )
}
