import { Cards3, Pill, SectionTitle } from '../components/ui'

const AGENTS = [
  { name: 'Orchestrator', status: '运行', tone: 'ok' as const, desc: '统一调度，禁省略。' },
  { name: 'Triage', status: '运行', tone: 'ok' as const, desc: '告警分诊，含 abstain。' },
  { name: 'Investigation', status: '运行', tone: 'ok' as const, desc: '事件取证 + 时间线。' },
  { name: 'Responder', status: '待命', tone: 'warn' as const, desc: '处置执行，经 HITL。' },
  { name: 'Reporter', status: '运行', tone: 'ok' as const, desc: '报告生成。' },
  { name: 'Tuning', status: '周扫', tone: 'dim' as const, desc: '反馈调优（不训 DSLM）。' },
]

export default function Agent() {
  return (
    <div>
      <SectionTitle>Agent 编排 · Orchestrator 调度</SectionTitle>
      <Cards3>
        {AGENTS.map((a) => (
          <div key={a.name} className="bg-paper border border-line rounded-[10px] p-[18px] lift">
            <div className="font-semibold mb-1.5 flex items-center gap-2">
              {a.name} <Pill tone={a.tone}>{a.status}</Pill>
            </div>
            <p className="text-[13px] text-dim">{a.desc}</p>
          </div>
        ))}
      </Cards3>
    </div>
  )
}
