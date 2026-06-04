import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Channel = { id: string; name: string; kind: string; url_masked: string; configured: boolean; enabled: boolean }
type Rule = {
  id: string
  name: string
  trigger_verdict: string
  trigger_severity: string
  trigger_keyword: string
  channel_id: string
  channel_name: string
  enabled: boolean
  hits: number
}
type SendRec = { id: string; channel_name: string; kind: string; title: string; status: string; note: string; error: string; ts: string }

const KIND_LABEL: Record<string, string> = { wechat: '企业微信', dingtalk: '钉钉', webhook: '通用 Webhook' }

export default function Dispatch() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [chans, setChans] = useState<Channel[]>([])
  const [rules, setRules] = useState<Rule[]>([])
  const [recs, setRecs] = useState<SendRec[]>([])
  const [outbound, setOutbound] = useState(false)
  const [msg, setMsg] = useState('')
  // 新渠道
  const [cName, setCName] = useState('')
  const [cKind, setCKind] = useState('wechat')
  const [cUrl, setCUrl] = useState('')
  // 新规则
  const [rName, setRName] = useState('')
  const [rChannel, setRChannel] = useState('')
  const [rSeverity, setRSeverity] = useState('')
  const [rKeyword, setRKeyword] = useState('')

  function load() {
    apiGet<{ channels: Channel[]; outbound_enabled: boolean }>('/api/channels').then((d) => {
      setChans(d.channels)
      setOutbound(d.outbound_enabled)
      if (!rChannel && d.channels[0]) setRChannel(d.channels[0].id)
    })
    apiGet<{ rules: Rule[] }>('/api/dispatch-rules').then((d) => setRules(d.rules))
    apiGet<{ records: SendRec[] }>('/api/dispatch/records').then((d) => setRecs(d.records))
  }
  useEffect(load, [])

  async function addChannel() {
    if (!cName.trim()) return setMsg('渠道名不能为空')
    await apiPost('/api/channels', { name: cName.trim(), kind: cKind, url: cUrl.trim(), actor })
    setMsg(`已新建渠道「${cName.trim()}」`)
    setCName(''); setCUrl('')
    load()
  }
  async function testChannel(c: Channel) {
    const r = await apiPost<{ status: string; note: string; error: string }>(`/api/channels/${c.id}/test`, {})
    setMsg(`测试 ${c.name}：${r.status}${r.note ? `（${r.note}）` : ''}${r.error ? ` ${r.error}` : ''}`)
    load()
  }
  async function addRule() {
    if (!rName.trim() || !rChannel) return setMsg('规则名与渠道不能为空')
    await apiPost('/api/dispatch-rules', {
      name: rName.trim(), channel_id: rChannel, trigger_severity: rSeverity, trigger_keyword: rKeyword.trim(), actor,
    })
    setMsg(`已新建规则「${rName.trim()}」`)
    setRName(''); setRKeyword('')
    load()
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 text-[13px]">
        <Pill tone={outbound ? 'ok' : 'warn'}>{outbound ? '出域开启 · 真实发送' : '出域关闭 · stub 不真实外发'}</Pill>
        <span className="text-dim">处置完→通知人。命中规则即发到渠道，全程留发送记录。</span>
        {msg && <span className="text-sage">{msg}</span>}
      </div>

      <div className="grid grid-cols-2 gap-[34px] items-start">
        {/* 渠道 CRUD */}
        <Card>
          <SectionTitle>外发渠道 · 增删改 / 测连（首个=企微，ADR-0010）</SectionTitle>
          {chans.map((c) => (
            <div key={c.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
              <span className="min-w-0">
                <div className="flex items-center gap-2">{c.name} <Pill tone="dim">{KIND_LABEL[c.kind] || c.kind}</Pill></div>
                <div className="text-dim text-[12px]">{c.configured ? `webhook ${c.url_masked}` : '未配 webhook'}</div>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <button onClick={() => testChannel(c)} className="text-[12px] text-ochre hover:text-terra">测连</button>
                <button onClick={async () => { await apiPut(`/api/channels/${c.id}`, { enabled: !c.enabled, actor }); load() }}
                  className={`text-[12px] border rounded-full px-2 ${c.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                  {c.enabled ? '启用' : '停用'}
                </button>
                <button onClick={async () => { await apiDelete(`/api/channels/${c.id}`); load() }}
                  className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
              </span>
            </div>
          ))}
          <div className="mt-4 flex flex-col gap-2">
            <input value={cName} onChange={(e) => setCName(e.target.value)} placeholder="渠道名，如 值班群"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2">
              <select value={cKind} onChange={(e) => setCKind(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                <option value="wechat">企业微信</option>
                <option value="dingtalk">钉钉</option>
                <option value="webhook">通用 Webhook</option>
              </select>
              <input value={cUrl} onChange={(e) => setCUrl(e.target.value)} placeholder="webhook 地址（密钥，不回显）"
                className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] font-mono" />
            </div>
            <button className={btnGhost} onClick={addChannel}>+ 新建渠道</button>
          </div>
        </Card>

        {/* 规则 CRUD */}
        <Card>
          <SectionTitle>外发规则 · 命中即分发</SectionTitle>
          {rules.map((r) => (
            <div key={r.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
              <span className="min-w-0">
                <div className="truncate">{r.name}</div>
                <div className="text-dim text-[12px]">
                  {r.trigger_verdict}{r.trigger_severity && `·${r.trigger_severity}`}{r.trigger_keyword && `·含「${r.trigger_keyword}」`} → {r.channel_name} · 命中 {r.hits}
                </div>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <button onClick={async () => { await apiPut(`/api/dispatch-rules/${r.id}`, { enabled: !r.enabled, actor }); load() }}
                  className={`text-[12px] border rounded-full px-2 ${r.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                  {r.enabled ? '启用' : '停用'}
                </button>
                <button onClick={async () => { await apiDelete(`/api/dispatch-rules/${r.id}`); load() }}
                  className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
              </span>
            </div>
          ))}
          <div className="mt-4 flex flex-col gap-2">
            <input value={rName} onChange={(e) => setRName(e.target.value)} placeholder="规则名，如 严重真威胁外发"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2">
              <select value={rChannel} onChange={(e) => setRChannel(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {chans.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <select value={rSeverity} onChange={(e) => setRSeverity(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                <option value="">不限严重度</option>
                <option value="严重">严重</option>
                <option value="高">高</option>
              </select>
              <input value={rKeyword} onChange={(e) => setRKeyword(e.target.value)} placeholder="关键字(可空)"
                className="flex-1 min-w-0 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            </div>
            <button className={btnGhost} onClick={addRule}>+ 新建规则（默认触发 真威胁）</button>
          </div>
        </Card>
      </div>

      {/* 发送记录 */}
      <Card className="mt-[18px]">
        <SectionTitle>发送记录 · 成功/失败可追溯</SectionTitle>
        {recs.length === 0 && <div className="text-dim text-[13px] py-2">暂无发送记录</div>}
        {recs.map((r) => (
          <div key={r.id} className="flex justify-between items-center py-2 border-b border-dotted border-line text-[13.5px]">
            <span className="truncate mr-2">
              <span className="text-dim font-mono text-[12px]">{r.id}</span> {r.channel_name} · {r.title}
            </span>
            <span className="flex items-center gap-2 shrink-0">
              <span className="text-dim text-[12px]">{r.note || r.error}</span>
              <Pill tone={r.status === '成功' ? 'ok' : 'warn'}>{r.status}</Pill>
              <span className="text-dim text-[12px]">{r.ts}</span>
            </span>
          </div>
        ))}
      </Card>
    </div>
  )
}
