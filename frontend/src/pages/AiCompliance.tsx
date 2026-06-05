import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { Modal } from '../components/Modal'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'

type AiAsset = {
  id: string
  name: string
  kind: string
  provider: string
  status: string
  owner: string
  outbound: boolean
  sensitivity: string
  risk_class: string
  discovered: string
  note: string
}
type Finding = { asset_id: string; asset_name: string; severity: string; rule: string; message: string; suggestion: string }
type Shadow = { name: string; model: string; outbound: boolean; reason: string }
type Options = { kinds: string[]; status: string[]; sensitivity: string[]; risk_class: string[] }
type Overview = {
  assets: AiAsset[]
  findings: Finding[]
  shadow_candidates: Shadow[]
  counts: Record<string, number>
  options: Options
}

const STATUS_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 已批准: 'ok', 待评审: 'warn', 影子: 't' }
const RISK_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 最小: 'dim', 有限: 'ok', 高: 'warn', 不可接受: 't' }
const SEV_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { P0: 't', P1: 'warn', P2: 'dim' }
const blank = { name: '', kind: 'LLM', provider: '', status: '待评审', owner: '', outbound: false, sensitivity: '内部', risk_class: '有限', note: '' }

export default function AiCompliance() {
  const [d, setD] = useState<Overview | null>(null)
  const [dlg, setDlg] = useState<{ id?: string; form: typeof blank } | null>(null)
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<Overview>('/api/ai-compliance').then(setD)
  }
  useEffect(load, [])

  async function save() {
    if (!dlg) return
    if (!dlg.form.name.trim()) return setMsg('名称不能为空')
    try {
      if (dlg.id) await apiPut(`/api/ai-compliance/${dlg.id}`, dlg.form)
      else await apiPost('/api/ai-compliance', dlg.form)
      setMsg(dlg.id ? '已更新' : '已登记')
      setDlg(null)
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }
  async function remove(a: AiAsset) {
    if (!confirm(`删除 AI 资产「${a.name}」？`)) return
    await apiDelete(`/api/ai-compliance/${a.id}`)
    load()
  }
  function f(k: keyof typeof blank, v: string | boolean) {
    if (dlg) setDlg({ ...dlg, form: { ...dlg.form, [k]: v } })
  }
  const opt = d?.options
  const c = d?.counts || {}

  return (
    <div className="grid grid-cols-[1.4fr_1fr] gap-[34px] items-start">
      {/* AI 资产清单 */}
      <Card>
        <SectionTitle>AI 资产清单 · 增删改（Shadow AI 治理 C-3）</SectionTitle>
        <div className="text-dim text-[12px] mb-3">
          共 {c.total || 0} · 已批准 {c.approved || 0} · 待评审 {c.pending || 0} · 影子 {c.shadow || 0}
        </div>
        {d?.assets.map((a) => (
          <div key={a.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="truncate">{a.name}</span>
                <Pill tone={STATUS_TONE[a.status] || 'dim'}>{a.status}</Pill>
                <Pill tone={RISK_TONE[a.risk_class] || 'dim'}>风险:{a.risk_class}</Pill>
                {a.outbound && <Pill tone="warn">出域</Pill>}
              </div>
              <div className="text-dim text-[12px]">
                {a.kind} · {a.provider || '—'} · 属主 {a.owner || '（缺）'} · {a.discovered}
              </div>
            </span>
            <span className="shrink-0 flex gap-3 items-center">
              <button onClick={() => setDlg({ id: a.id, form: { ...blank, ...a } })} className="text-dim hover:text-sage text-[13px]">编辑</button>
              <button onClick={() => remove(a)} className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
            </span>
          </div>
        ))}
        <div className="mt-4 flex items-center gap-3">
          <button className={btnPrimary} onClick={() => setDlg({ form: { ...blank } })}>+ 登记 AI 资产</button>
          {msg && <span className="text-sage text-[13px]">{msg}</span>}
        </div>
      </Card>

      <div>
        {/* Shadow AI 发现 */}
        <Card className="mb-5">
          <SectionTitle>Shadow AI 发现 · 在用未登记</SectionTitle>
          <div className="text-dim text-[12px] mb-2">比对平台在用 LLM provider 与已审批清单</div>
          {d?.shadow_candidates.length === 0 && <div className="text-sage text-[13px]">无影子 AI：在用 provider 均已登记审批。</div>}
          {d?.shadow_candidates.map((s, i) => (
            <div key={i} className="py-2 border-b border-dotted border-line text-[13px]">
              <div className="flex items-center gap-2">
                <span className="font-mono">{s.name}</span>
                <Pill tone="t">影子候选</Pill>
                {s.outbound && <Pill tone="warn">出域</Pill>}
              </div>
              <div className="text-dim text-[12px]">{s.model} · {s.reason}</div>
            </div>
          ))}
        </Card>

        {/* 合规体检 findings */}
        <Card>
          <SectionTitle>合规体检 · 发现 {d?.findings.length || 0}（P0:{c.p0 || 0} P1:{c.p1 || 0}）</SectionTitle>
          {d?.findings.length === 0 && <div className="text-sage text-[13px]">未发现合规问题。</div>}
          {d?.findings.map((x, i) => (
            <div key={i} className="py-2 border-b border-dotted border-line text-[13px]">
              <div className="flex items-center gap-2">
                <Pill tone={SEV_TONE[x.severity] || 'dim'}>{x.severity}</Pill>
                <span className="font-semibold">{x.rule}</span>
                <span className="text-dim text-[12px]">{x.asset_name}</span>
              </div>
              <div className="mt-0.5">{x.message}</div>
              <div className="text-dim text-[12px] mt-0.5">建议：{x.suggestion}</div>
            </div>
          ))}
        </Card>
      </div>

      {/* 登记/编辑弹框 */}
      <Modal open={!!dlg} title={dlg?.id ? `编辑 ${dlg.id}` : '登记 AI 资产'} onClose={() => setDlg(null)}>
        {dlg && opt && (
          <div className="flex flex-col gap-3">
            <input value={dlg.form.name} onChange={(e) => f('name', e.target.value)} placeholder="名称"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2">
              <select value={dlg.form.kind} onChange={(e) => f('kind', e.target.value)} className="flex-1 bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {opt.kinds.map((k) => <option key={k}>{k}</option>)}
              </select>
              <input value={dlg.form.provider} onChange={(e) => f('provider', e.target.value)} placeholder="provider"
                className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            </div>
            <div className="flex gap-2">
              <select value={dlg.form.status} onChange={(e) => f('status', e.target.value)} className="flex-1 bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {opt.status.map((k) => <option key={k}>{k}</option>)}
              </select>
              <select value={dlg.form.risk_class} onChange={(e) => f('risk_class', e.target.value)} className="flex-1 bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {opt.risk_class.map((k) => <option key={k}>风险:{k}</option>)}
              </select>
            </div>
            <div className="flex gap-2 items-center">
              <select value={dlg.form.sensitivity} onChange={(e) => f('sensitivity', e.target.value)} className="flex-1 bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {opt.sensitivity.map((k) => <option key={k}>数据:{k}</option>)}
              </select>
              <input value={dlg.form.owner} onChange={(e) => f('owner', e.target.value)} placeholder="属主"
                className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            </div>
            <label className="flex items-center gap-2 text-[13px] text-dim">
              <input type="checkbox" checked={dlg.form.outbound} onChange={(e) => f('outbound', e.target.checked)} /> 出域（数据离境/到外部）
            </label>
            <input value={dlg.form.note} onChange={(e) => f('note', e.target.value)} placeholder="备注"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2 justify-end">
              <button className={btnGhost} onClick={() => setDlg(null)}>取消</button>
              <button className={btnPrimary} onClick={save}>保存</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
