import { useState } from 'react'
import { Cards3, Pill, SectionTitle } from '../components/ui'

const PLAYBOOKS = [
  { name: '封禁 IP', risk: 't' as const, riskLabel: '高风险', desc: '触发：C2 外连确认 → 防火墙封禁。必经双模型 + HITL。' },
  { name: '隔离主机', risk: 't' as const, riskLabel: '高风险', desc: '触发：横移迹象 → EDR 隔离。必经 HITL 审批。' },
  { name: '禁用账号', risk: 'warn' as const, riskLabel: '中风险', desc: '触发：凭证滥用 → AD 禁用。' },
]

export default function Soar() {
  const [enabled, setEnabled] = useState<Record<string, boolean>>({})
  return (
    <div>
      <SectionTitle>处置剧本 · 高风险默认 HITL</SectionTitle>
      <Cards3>
        {PLAYBOOKS.map((p) => (
          <div key={p.name} className="bg-paper border border-line rounded-[10px] p-[18px] lift">
            <div className="font-semibold mb-1.5 flex items-center gap-2">
              {p.name} <Pill tone={p.risk}>{p.riskLabel}</Pill>
            </div>
            <p className="text-[13px] text-dim min-h-[54px]">{p.desc}</p>
            <button
              onClick={() => setEnabled((e) => ({ ...e, [p.name]: !e[p.name] }))}
              className={`mt-3 rounded-lg px-4 py-2 text-[13px] ${
                enabled[p.name]
                  ? 'bg-sage text-paper'
                  : 'border border-clay hover:bg-paper2'
              }`}
            >
              {enabled[p.name] ? '已启用' : '启用'}
            </button>
          </div>
        ))}
      </Cards3>
    </div>
  )
}
