import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost } from '../components/ui'
import { apiGet, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type AgentCfg = {
  name: string
  scenario: string
  prompt_key: string
  enabled: boolean
  confidence_threshold: number
  cross_check_mode: string
  model: string
}
type AgentInfo = { name: string; status: string; desc: string; config?: AgentCfg }

export default function Agent() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [providers, setProviders] = useState<string[]>([])
  const [modes, setModes] = useState<string[]>(['auto', 'on', 'off'])
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ agents: AgentInfo[]; providers: string[]; cross_check_modes: string[] }>('/api/agents').then((d) => {
      setAgents(d.agents)
      setProviders(d.providers)
      setModes(d.cross_check_modes)
    })
  }
  useEffect(load, [])

  async function patch(name: string, fields: Record<string, unknown>) {
    await apiPut(`/api/agents/${name.toLowerCase()}`, { ...fields, actor })
    setMsg(`已更新 ${name}（即时生效）`)
    load()
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <SectionTitle>AI Agent · 名册 + 运行时配置（改了即时生效）</SectionTitle>
        {msg && <span className="text-sage text-[13px]">{msg}</span>}
      </div>
      <div className="grid grid-cols-2 gap-[18px]">
        {agents.map((a) => (
          <Card key={a.name}>
            <div className="font-semibold mb-1 flex items-center gap-2">
              {a.name}
              <Pill tone={a.status === '实现' ? 'ok' : 'dim'}>{a.status}</Pill>
              {a.config && !a.config.enabled && <Pill tone="warn">已停用</Pill>}
            </div>
            <p className="text-[13px] text-dim mb-2">{a.desc}</p>

            {a.config ? (
              <div className="border-t border-dotted border-line pt-3 mt-2 flex flex-col gap-2 text-[13px]">
                <div className="flex items-center justify-between">
                  <span className="text-dim">启用</span>
                  <button onClick={() => patch(a.name, { enabled: !a.config!.enabled })}
                    className={`text-[12px] border rounded-full px-2 ${a.config.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                    {a.config.enabled ? '启用' : '停用'}
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-dim">置信度阈值</span>
                  <input type="number" min={0} max={1} step={0.05} defaultValue={a.config.confidence_threshold}
                    onBlur={(e) => patch(a.name, { confidence_threshold: parseFloat(e.target.value) })}
                    className="w-20 bg-paper2 border border-line rounded-lg px-2 py-1 text-[13px]" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-dim">双模型 cross-check</span>
                  <select value={a.config.cross_check_mode} onChange={(e) => patch(a.name, { cross_check_mode: e.target.value })}
                    className="bg-paper2 border border-line rounded-lg px-2 py-1 text-[13px]">
                    {modes.map((m) => <option key={m} value={m}>{m === 'auto' ? '自动(按高风险)' : m === 'on' ? '强制开' : '关'}</option>)}
                  </select>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-dim">大模型</span>
                  <select value={a.config.model} onChange={(e) => patch(a.name, { model: e.target.value })}
                    className="bg-paper2 border border-line rounded-lg px-2 py-1 text-[13px]">
                    {providers.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div className="flex items-center justify-between text-dim text-[12px]">
                  <span>Prompt</span>
                  <a className="text-terra hover:underline font-mono" href="/prompt">{a.config.prompt_key}</a>
                </div>
                <div className="text-dim text-[12px]">场景路由：<span className="font-mono">{a.config.scenario}</span></div>
              </div>
            ) : (
              <div className="text-dim text-[12px] mt-2">规划中：尚未编码，无运行时配置。</div>
            )}
          </Card>
        ))}
      </div>
      <div className="text-dim text-[13px] mt-3">
        Agent 是代码（类+逻辑），不在 UI 凭空新建；可调的是上述配置。模型改动写入场景路由（与「模型 & 成本」同一份）。
        <a className={`${btnGhost} ml-3 inline-block`} href="/agent" onClick={(e) => { e.preventDefault(); load() }}>刷新</a>
      </div>
    </div>
  )
}
