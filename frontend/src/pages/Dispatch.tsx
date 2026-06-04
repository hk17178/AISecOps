import { Card, Pill, Row, SectionTitle, btnGhost } from '../components/ui'

const CHANNELS = [
  { name: '企业微信 · @值班群', status: '已连', tone: 'ok' as const },
  { name: '钉钉', status: '未配', tone: 'dim' as const },
  { name: '邮件 · soc@corp', status: '未配', tone: 'dim' as const },
  { name: 'Webhook（通用）', status: '已连', tone: 'ok' as const },
  { name: '回写工单系统', status: '已连', tone: 'ok' as const },
  { name: '回写 SIEM / 防火墙', status: '按需', tone: 'warn' as const },
]

const RULES = [
  { n: '01', r: '真威胁 + 严重 → 企微@值班 + 自动开工单', ch: '渠道：企微 · 工单' },
  { n: '02', r: '真威胁 + C2 外连 → 回写防火墙封禁工单', ch: '渠道：回写 SIEM' },
  { n: '03', r: '待研判 → 仅入 HITL 队列，不外发打扰', ch: '渠道：无' },
  { n: '04', r: '误报 → 静默归档', ch: '渠道：无' },
]

export default function Dispatch() {
  return (
    <div className="grid grid-cols-2 gap-[34px]">
      <Card>
        <SectionTitle>外发渠道（首个=企业微信，ADR-0010）</SectionTitle>
        {CHANNELS.map((c) => (
          <Row key={c.name}>
            <span>{c.name}</span>
            <Pill tone={c.tone}>{c.status}</Pill>
          </Row>
        ))}
      </Card>
      <Card>
        <SectionTitle>外发规则 · 命中即分发</SectionTitle>
        {RULES.map((r) => (
          <div key={r.n} className="flex gap-3 py-2.5 border-b border-dotted border-line">
            <span className="text-terra font-semibold">{r.n}</span>
            <div>
              <div className="text-[14px]">{r.r}</div>
              <div className="text-dim text-[12px] mt-0.5">{r.ch}</div>
            </div>
          </div>
        ))}
        <button className={`${btnGhost} mt-3`}>+ 新建规则</button>
      </Card>
    </div>
  )
}
