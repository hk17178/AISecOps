import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle } from '../components/ui'
import { apiGet, apiPost } from '../lib/api'

type Ticket = {
  id: string
  action: string
  target: string
  risk: string
  status: string
  ts: string
}

export default function Ticket() {
  const [tickets, setTickets] = useState<Ticket[]>([])

  const load = () =>
    apiGet<{ tickets: Ticket[] }>('/api/tickets')
      .then((d) => setTickets(d.tickets))
      .catch(() => setTickets([]))

  useEffect(() => {
    load()
  }, [])

  async function decide(id: string, kind: 'approve' | 'reject') {
    await apiPost(`/api/tickets/${id}/${kind}`, {})
    await load()
  }

  const pending = tickets.filter((t) => t.status === '待审').length

  return (
    <div>
      <SectionTitle>HITL 审批队列 · {pending} 待处理 · 真工单库</SectionTitle>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="text-[12px] text-dim uppercase tracking-wide">
              <th className="text-left font-normal pb-2.5">工单</th>
              <th className="text-left font-normal pb-2.5">动作</th>
              <th className="text-left font-normal pb-2.5">对象</th>
              <th className="text-left font-normal pb-2.5">风险</th>
              <th className="text-right font-normal pb-2.5">操作</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{t.id}</td>
                <td className="py-3">{t.action}</td>
                <td className="py-3">{t.target}</td>
                <td className="py-3">
                  <Pill tone={t.risk === '高' ? 't' : 'warn'}>{t.risk}</Pill>
                </td>
                <td className="py-3 text-right">
                  {t.status === '待审' ? (
                    <span className="flex gap-2 justify-end">
                      <button
                        onClick={() => decide(t.id, 'approve')}
                        className="bg-terra text-paper rounded-lg px-3 py-1.5 text-[13px] hover:bg-[#9a4527]"
                      >
                        批准
                      </button>
                      <button
                        onClick={() => decide(t.id, 'reject')}
                        className="border border-clay rounded-lg px-3 py-1.5 text-[13px] hover:bg-paper2"
                      >
                        驳回
                      </button>
                    </span>
                  ) : (
                    <span className={t.status === '已批准' ? 'text-sage' : 'text-dim'}>{t.status}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
