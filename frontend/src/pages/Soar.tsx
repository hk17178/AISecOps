import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Playbook = {
  id: string
  name: string
  trigger_verdict: string
  trigger_keyword: string
  actions: string[]
  risk: string
  enabled: boolean
  runs: number
}
type Run = {
  id: string
  playbook_name: string
  target: string
  action: string
  status: string
  ticket_id: string
  ts: string
}
type AlertRow = { id: string; host: string; title: string }

const ACTIONS = ['封禁 IP', '隔离主机', '禁用账号']
const STATUS_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = {
  待审: 'warn',
  已执行: 'ok',
  已撤销: 'dim',
  已驳回: 'dim',
}

export default function Soar() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [pbs, setPbs] = useState<Playbook[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [alerts, setAlerts] = useState<AlertRow[]>([])
  const [name, setName] = useState('')
  const [action, setAction] = useState('隔离主机')
  const [keyword, setKeyword] = useState('')
  const [trigPb, setTrigPb] = useState('')
  const [trigAlert, setTrigAlert] = useState('')
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<{ playbooks: Playbook[] }>('/api/playbooks').then((d) => {
      setPbs(d.playbooks)
      if (!trigPb && d.playbooks[0]) setTrigPb(d.playbooks[0].id)
    })
    apiGet<{ runs: Run[] }>('/api/soar/runs').then((d) => setRuns(d.runs))
    apiGet<{ alerts: AlertRow[] }>('/api/alerts').then((d) => {
      setAlerts(d.alerts)
      if (!trigAlert && d.alerts[0]) setTrigAlert(d.alerts[0].id)
    })
  }
  useEffect(load, [])

  async function addPb() {
    if (!name.trim()) return setMsg('剧本名不能为空')
    try {
      await apiPost('/api/playbooks', { name: name.trim(), actions: [action], trigger_keyword: keyword.trim(), actor })
      setMsg(`已新建剧本「${name.trim()}」`)
      setName('')
      setKeyword('')
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }

  async function trigger() {
    try {
      const r = await apiPost<{ ticket: { id: string } }>('/api/soar/trigger', {
        playbook_id: trigPb,
        alert_id: trigAlert,
        actor,
      })
      setMsg(`已触发 → 建 HITL 工单 ${r.ticket.id}（去「工单 & HITL」批准后执行）`)
      load()
    } catch (e) {
      setMsg(`触发失败：${(e as Error).message}`)
    }
  }

  async function undo(r: Run) {
    await apiPost(`/api/soar/runs/${r.id}/undo`, {})
    setMsg(`已撤销 ${r.id}`)
    load()
  }

  return (
    <div>
      <div className="text-dim text-[13px] mb-4">
        剧本 = 触发条件 → 动作。触发**不直接动手**：先建 HITL 工单（C-8），人工批准后才执行，可撤销。{msg && <span className="text-sage ml-2">{msg}</span>}
      </div>

      <div className="grid grid-cols-[1.4fr_1fr] gap-[34px] items-start">
        <div className="flex flex-col gap-[18px]">
          {/* 手动触发 */}
          <Card>
            <SectionTitle>触发处置 · 对告警执行剧本</SectionTitle>
            <div className="flex flex-wrap gap-2 items-center">
              <select value={trigPb} onChange={(e) => setTrigPb(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]">
                {pbs.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <span className="text-dim text-[13px]">对</span>
              <select value={trigAlert} onChange={(e) => setTrigAlert(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] max-w-[280px]">
                {alerts.map((a) => <option key={a.id} value={a.id}>{a.host} · {a.title}</option>)}
              </select>
              <button className={btnPrimary} onClick={trigger}>触发（建审批单）</button>
            </div>
          </Card>

          {/* 剧本列表 + CRUD */}
          <Card>
            <SectionTitle>处置剧本 · 增删改 / 启停</SectionTitle>
            {pbs.map((p) => (
              <div key={p.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
                <span className="min-w-0">
                  <div className="flex items-center gap-2">
                    {p.name}
                    <Pill tone={p.risk === '高' ? 't' : 'warn'}>{p.risk}风险</Pill>
                  </div>
                  <div className="text-dim text-[12px]">
                    触发 {p.trigger_verdict}{p.trigger_keyword && ` + 含「${p.trigger_keyword}」`} → {p.actions.join('、')} · 触发 {p.runs} 次
                  </div>
                </span>
                <span className="flex items-center gap-2 shrink-0">
                  <button onClick={async () => { await apiPut(`/api/playbooks/${p.id}`, { enabled: !p.enabled, actor }); load() }}
                    className={`text-[12px] border rounded-full px-2 ${p.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                    {p.enabled ? '启用' : '停用'}
                  </button>
                  <button onClick={async () => { await apiDelete(`/api/playbooks/${p.id}`); load() }}
                    className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
                </span>
              </div>
            ))}

            <div className="mt-4 flex flex-col gap-2">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="剧本名，如 C2 外连封禁"
                className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
              <div className="flex gap-2">
                <select value={action} onChange={(e) => setAction(e.target.value)}
                  className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                  {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
                <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="触发关键字（标题含，可空）"
                  className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
              </div>
              <button className={btnGhost} onClick={addPb}>+ 新建剧本</button>
            </div>
          </Card>
        </div>

        {/* 执行历史 */}
        <Card>
          <SectionTitle>执行历史 · 留痕可撤销</SectionTitle>
          {runs.length === 0 && <div className="text-dim text-[13px] py-2">暂无执行记录</div>}
          {runs.map((r) => (
            <div key={r.id} className="py-2.5 border-b border-dotted border-line text-[13.5px]">
              <div className="flex items-center gap-2">
                <span className="text-dim font-mono text-[12px]">{r.id}</span>
                <Pill tone={STATUS_TONE[r.status] || 'dim'}>{r.status}</Pill>
                {r.status === '已执行' && (
                  <button onClick={() => undo(r)} className="ml-auto text-dim hover:text-terra text-[12px]">撤销</button>
                )}
              </div>
              <div className="mt-1">{r.playbook_name} · {r.action} → {r.target}</div>
              <div className="text-dim text-[12px]">工单 {r.ticket_id || '—'} · {r.ts}</div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}
