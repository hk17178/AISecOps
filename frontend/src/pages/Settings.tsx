import { useEffect, useState } from 'react'
import { apiGet, apiPut } from '../lib/api'

type Config = {
  llm_base_url: string
  llm_model: string
  llm_api_key_set: boolean
  monthly_budget_cny: number
  allow_outbound: boolean
  es_hosts: string
  wechat_webhook_set: boolean
}

export default function Settings() {
  const [cfg, setCfg] = useState<Config | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState('')

  useEffect(() => {
    apiGet<Config>('/api/config').then(setCfg).catch(() => setCfg(null))
  }, [])

  async function save() {
    const body: Record<string, unknown> = {}
    if (apiKey) body.llm_api_key = apiKey
    const r = await apiPut<{ note: string }>('/api/config', body)
    setSaved(r.note)
  }

  const inputCls = 'w-full border border-line rounded-lg bg-bg px-3 py-2.5 outline-none focus:border-clay'
  const row = 'flex justify-between py-2.5 border-b border-dotted border-line text-[14px]'

  return (
    <div className="max-w-[760px]">
      <div className="bg-paper border border-line rounded-[10px] p-5 mb-5">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">大模型 · 在此配置（P-18：配置走页面）</div>
        <label className="block text-[13px] text-dim mb-1.5">
          LLM API Key {cfg?.llm_api_key_set && <span className="text-sage">（已配置）</span>}
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="填入即更新；留空不改"
          className={`${inputCls} mb-3`}
        />
        <div className={row}>
          <span className="text-dim">Base URL</span>
          <span>{cfg?.llm_base_url ?? '—'}</span>
        </div>
        <div className={row}>
          <span className="text-dim">模型</span>
          <span>{cfg?.llm_model ?? '—'}</span>
        </div>
        <div className={row}>
          <span className="text-dim">月度预算</span>
          <span>¥{cfg?.monthly_budget_cny ?? '—'}</span>
        </div>
        <div className={row}>
          <span className="text-dim">出域开关（C-32）</span>
          <span className={cfg?.allow_outbound ? 'text-ochre' : 'text-sage'}>
            {cfg?.allow_outbound ? '开' : '关'}
          </span>
        </div>
        <button onClick={save} className="bg-terra text-paper font-medium rounded-lg px-6 py-2.5 mt-4 hover:bg-[#9a4527]">
          保存
        </button>
        {saved && <div className="text-ochre text-[13px] mt-3">{saved}</div>}
      </div>

      <div className="bg-paper border border-line rounded-[10px] p-5">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">数据源 / 通知</div>
        <div className={row}>
          <span className="text-dim">Elasticsearch</span>
          <span>{cfg?.es_hosts ?? '—'}</span>
        </div>
        <div className={row}>
          <span className="text-dim">企业微信通知</span>
          <span className={cfg?.wechat_webhook_set ? 'text-sage' : 'text-dim'}>
            {cfg?.wechat_webhook_set ? '已配置' : '未配置'}
          </span>
        </div>
      </div>
    </div>
  )
}
