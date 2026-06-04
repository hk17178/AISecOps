import { useEffect, useState } from 'react'
import { Cards3, Pill, SectionTitle } from '../components/ui'
import { apiGet } from '../lib/api'

type AgentInfo = { name: string; status: string; desc: string }

export default function Agent() {
  const [agents, setAgents] = useState<AgentInfo[]>([])

  useEffect(() => {
    apiGet<{ agents: AgentInfo[] }>('/api/agents')
      .then((d) => setAgents(d.agents))
      .catch(() => setAgents([]))
  }, [])

  return (
    <div>
      <SectionTitle>Agent 名册 · 真实代码实现状态（来自后端）</SectionTitle>
      <Cards3>
        {agents.map((a) => (
          <div key={a.name} className="bg-paper border border-line rounded-[10px] p-[18px] lift">
            <div className="font-semibold mb-1.5 flex items-center gap-2">
              {a.name} <Pill tone={a.status === '实现' ? 'ok' : 'dim'}>{a.status}</Pill>
            </div>
            <p className="text-[13px] text-dim">{a.desc}</p>
          </div>
        ))}
      </Cards3>
    </div>
  )
}
