import { useState } from 'react'
import { apiPost } from '../lib/api'

type TriageResult = {
  agent: string
  ok: boolean
  data: { verdict: string; confidence: number; evidence: string[] }
  abstained: boolean
  note: string
}

export default function Triage() {
  const [host, setHost] = useState('WIN-APP-07')
  const [title, setTitle] = useState('检测到横向移动 (PsExec)，凭证 svc_backup')
  const [severity, setSeverity] = useState('严重')
  const [result, setResult] = useState<TriageResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  async function run() {
    setLoading(true)
    setErr('')
    setResult(null)
    try {
      const r = await apiPost<TriageResult>('/api/triage', { host, title, severity })
      setResult(r)
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  const inputCls = 'w-full border border-line rounded-lg bg-bg px-3 py-2.5 outline-none focus:border-clay'

  return (
    <div className="grid grid-cols-[1.4fr_1fr] gap-[34px]">
      <div className="bg-paper border border-line rounded-[10px] p-5">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">告警输入</div>
        <label className="block text-[13px] text-dim mb-1.5">主机</label>
        <input value={host} onChange={(e) => setHost(e.target.value)} className={`${inputCls} mb-4`} />
        <label className="block text-[13px] text-dim mb-1.5">告警描述</label>
        <textarea
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={`${inputCls} mb-4 min-h-[90px]`}
        />
        <label className="block text-[13px] text-dim mb-1.5">严重度</label>
        <input value={severity} onChange={(e) => setSeverity(e.target.value)} className={`${inputCls} mb-5`} />
        <button
          onClick={run}
          disabled={loading}
          className="bg-terra text-paper font-medium rounded-lg px-6 py-2.5 hover:bg-[#9a4527] disabled:opacity-50"
        >
          {loading ? '分诊中…' : '端到端分诊'}
        </button>
        <div className="text-dim text-[12px] mt-3">
          走 Orchestrator → Triage（ES 富化 + LLM）。无 API Key 时离线诚实转人工。
        </div>
      </div>

      <div className="bg-paper border border-line rounded-[10px] p-5">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">研判结果</div>
        {err && <div className="text-terra">{err}</div>}
        {!result && !err && <div className="text-dim">（等待分诊…）</div>}
        {result && (
          <div>
            <div className="text-[24px] font-semibold font-serif text-terra mb-1">
              {result.data.verdict}
            </div>
            <div className="text-dim text-[13px] mb-4">
              置信度 {result.data.confidence.toFixed(2)} ·{' '}
              {result.abstained ? '已转人工' : '已研判'}
            </div>
            {result.note && <div className="text-ochre text-[13px] mb-4">{result.note}</div>}
            {result.data.evidence.length > 0 && (
              <div>
                <div className="text-[12px] text-dim uppercase mb-2">证据</div>
                {result.data.evidence.map((ev, i) => (
                  <div key={i} className="py-1.5 border-b border-dotted border-line text-[14px]">
                    {ev}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
