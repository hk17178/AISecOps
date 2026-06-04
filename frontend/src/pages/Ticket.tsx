import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { Modal } from '../components/Modal'
import { apiGet, apiPost } from '../lib/api'
import { useAuth } from '../auth'

type Ticket = {
  id: string
  action: string
  target: string
  risk: string
  status: string
  ts: string
  reason: string
  decided_by: string
  decided_at: string
}

type AuditEntry = {
  timestamp: string
  actor: string
  action: string
  target: string
  details: { reason?: string; ticket_action?: string; ticket_target?: string }
}

const ACTION_LABEL: Record<string, string> = { ticket_approve: '批准', ticket_reject: '驳回' }

export default function Ticket() {
  const { user } = useAuth()
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [dlg, setDlg] = useState<{ id: string; kind: 'approve' | 'reject'; action: string; target: string } | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const t = await apiGet<{ tickets: Ticket[] }>('/api/tickets').catch(() => ({ tickets: [] }))
    setTickets(t.tickets)
    const a = await apiGet<{ entries: AuditEntry[] }>('/api/audit').catch(() => ({ entries: [] }))
    setAudit(a.entries.filter((e) => e.action.startsWith('ticket_')))
  }

  useEffect(() => {
    load()
  }, [])

  function openDialog(t: Ticket, kind: 'approve' | 'reject') {
    setReason('')
    setDlg({ id: t.id, kind, action: t.action, target: t.target })
  }

  async function confirm() {
    if (!dlg) return
    setBusy(true)
    try {
      await apiPost(`/api/tickets/${dlg.id}/${dlg.kind}`, { reason, actor: user?.username ?? '未知' })
      setDlg(null)
      await load()
    } finally {
      setBusy(false)
    }
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
              <th className="text-right font-normal pb-2.5">操作 / 结果</th>
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
                      <button onClick={() => openDialog(t, 'approve')} className="bg-terra text-paper rounded-lg px-3 py-1.5 text-[13px] hover:bg-[#9a4527]">批准</button>
                      <button onClick={() => openDialog(t, 'reject')} className="border border-clay rounded-lg px-3 py-1.5 text-[13px] hover:bg-paper2">驳回</button>
                    </span>
                  ) : (
                    <span>
                      <span className={t.status === '已批准' ? 'text-sage' : 'text-dim'}>{t.status}</span>
                      {t.reason && <span className="text-dim text-[12px]"> · {t.reason}</span>}
                      {t.decided_by && <span className="text-dim text-[12px]">（{t.decided_by}）</span>}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <SectionTitle>最近审批 · 审计留痕（C-23 不可篡改）</SectionTitle>
      <Card>
        {audit.length === 0 && <div className="text-dim">暂无审批记录</div>}
        {audit.map((e, i) => (
          <div key={i} className="flex justify-between py-2 border-b border-dotted border-line text-[14px]">
            <span>
              <span className="text-dim text-[13px]">{e.timestamp.slice(11, 19)}</span>{' '}
              <b>{e.actor}</b> {ACTION_LABEL[e.action] ?? e.action} {e.target}
              {e.details?.reason && <span className="text-dim"> · 理由：{e.details.reason}</span>}
            </span>
          </div>
        ))}
      </Card>

      <Modal
        open={!!dlg}
        title={`${dlg?.kind === 'approve' ? '批准' : '驳回'}工单 ${dlg?.id ?? ''}`}
        onClose={() => setDlg(null)}
      >
        <div className="text-[14px] mb-3">
          动作：<b>{dlg?.action}</b> · 对象：{dlg?.target}
        </div>
        <label className="block text-[13px] text-dim mb-1.5">审批理由（写入审计）</label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={dlg?.kind === 'approve' ? '如：确认横移属实，批准隔离' : '如：经核实为误报，驳回'}
          className="w-full border border-line rounded-lg bg-bg px-3 py-2.5 mb-4 outline-none focus:border-clay min-h-[80px]"
        />
        <div className="flex gap-2 justify-end">
          <button onClick={() => setDlg(null)} className={btnGhost}>取消</button>
          <button onClick={confirm} disabled={busy} className={btnPrimary}>
            {busy ? '提交中…' : '确认'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
