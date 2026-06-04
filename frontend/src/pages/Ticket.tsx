import { useState } from 'react'

type Ticket = {
  id: string
  action: string
  target: string
  risk: '高' | '中'
  status: '待审' | '已批准' | '已驳回'
}

const INITIAL: Ticket[] = [
  { id: 'TKT-204', action: '隔离主机', target: 'WIN-APP-07', risk: '高', status: '待审' },
  { id: 'TKT-203', action: '禁用账号', target: 'svc_backup', risk: '高', status: '待审' },
  { id: 'TKT-201', action: '封禁 IP', target: '185.x.x.x', risk: '中', status: '待审' },
]

export default function Ticket() {
  const [tickets, setTickets] = useState<Ticket[]>(INITIAL)

  function decide(id: string, status: '已批准' | '已驳回') {
    setTickets((ts) => ts.map((t) => (t.id === id ? { ...t, status } : t)))
  }

  return (
    <div>
      <div className="text-[13px] text-dim uppercase tracking-wide mb-3">
        HITL 审批队列 · {tickets.filter((t) => t.status === '待审').length} 待处理
      </div>
      <div className="bg-paper border border-line rounded-[10px] p-5 lift">
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
                  <span className={`text-[12px] border rounded-full px-2 ${t.risk === '高' ? 'text-terra border-terra' : 'text-ochre border-ochre'}`}>
                    {t.risk}
                  </span>
                </td>
                <td className="py-3 text-right">
                  {t.status === '待审' ? (
                    <span className="flex gap-2 justify-end">
                      <button onClick={() => decide(t.id, '已批准')} className="bg-terra text-paper rounded-lg px-3 py-1.5 text-[13px] hover:bg-[#9a4527]">
                        批准
                      </button>
                      <button onClick={() => decide(t.id, '已驳回')} className="border border-clay rounded-lg px-3 py-1.5 text-[13px] hover:bg-paper2">
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
      </div>
    </div>
  )
}
