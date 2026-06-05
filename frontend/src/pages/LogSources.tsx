import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'

type Source = {
  id: string
  name: string
  kind: string
  endpoint: string
  enabled: boolean
  last_status: string
  last_tested: string
  queryable: boolean
  runtime: string
}
type Data = { sources: Source[]; kinds: string[]; queryable_kinds: string[]; outbound_enabled: boolean }

const STATUS_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 已连: 'ok', 失败: 't', 未测: 'dim', 未配置: 'warn' }

export default function LogSources() {
  const [d, setD] = useState<Data | null>(null)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('elasticsearch')
  const [endpoint, setEndpoint] = useState('')
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<Data>('/api/log-sources').then((x) => {
      setD(x)
      setKind(x.kinds[0])
    })
  }
  useEffect(load, [])

  async function add() {
    if (!name.trim()) return setMsg('数据源名不能为空')
    try {
      await apiPost('/api/tools', { name: name.trim(), category: 'data_sources', kind, endpoint: endpoint.trim() })
      setMsg(`已登记数据源「${name.trim()}」`)
      setName('')
      setEndpoint('')
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }
  async function test(s: Source) {
    const r = await apiPost<{ last_status: string }>(`/api/tools/${s.id}/test`, {})
    setMsg(`${s.name} 连通测试：${r.last_status}`)
    load()
  }
  async function toggle(s: Source) {
    await apiPut(`/api/tools/${s.id}`, { enabled: !s.enabled })
    load()
  }
  async function remove(s: Source) {
    if (!confirm(`删除数据源「${s.name}」？`)) return
    await apiDelete(`/api/tools/${s.id}`)
    load()
  }

  return (
    <div className="grid grid-cols-[1.5fr_1fr] gap-[34px] items-start">
      <Card>
        <SectionTitle>日志 / 数据源接入 · 登记 + 连通测试（对标 Splunk「Data inputs」）</SectionTitle>
        <div className="text-dim text-[12px] mb-3">
          出域开关：{d?.outbound_enabled ? '开' : '关'} · 仅 ES 已具备真实查询适配器，其余登记后查询适配器随用随接（ADR-0009）
        </div>
        {d?.sources.map((s) => (
          <div key={s.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="truncate">{s.name}</span>
                <Pill tone="dim">{s.kind}</Pill>
                <Pill tone={s.queryable ? 'ok' : 'warn'}>{s.queryable ? '可查询' : '已登记'}</Pill>
                {!s.enabled && <Pill tone="dim">已停用</Pill>}
              </div>
              <div className="text-dim text-[12px]">
                {s.endpoint || '（无端点）'} · {s.runtime}
                {s.last_tested && ` · 测于 ${s.last_tested.slice(5, 16)}`}
              </div>
            </span>
            <span className="shrink-0 flex gap-3 items-center">
              <Pill tone={STATUS_TONE[s.last_status] || 'dim'}>{s.last_status}</Pill>
              <button onClick={() => test(s)} className="text-sage hover:underline text-[12px]">测试</button>
              <button onClick={() => toggle(s)} className="text-dim hover:text-clay text-[12px]">{s.enabled ? '停用' : '启用'}</button>
              <button onClick={() => remove(s)} className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
            </span>
          </div>
        ))}
        {d?.sources.length === 0 && <div className="text-dim text-[13px] py-2">暂无数据源，右侧登记一个。</div>}
      </Card>

      <Card>
        <SectionTitle>登记数据源</SectionTitle>
        <div className="flex flex-col gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="名称，如 生产 ES / 机房 Zabbix"
            className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
          <select value={kind} onChange={(e) => setKind(e.target.value)}
            className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
            {d?.kinds.map((k) => (
              <option key={k} value={k}>{k}{d.queryable_kinds.includes(k) ? '（可查询）' : ''}</option>
            ))}
          </select>
          <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="端点，如 http://es:9200（可空）"
            className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] font-mono" />
          <button className={btnPrimary} onClick={add}>+ 登记并可连通测试</button>
          {msg && <div className="text-sage text-[13px]">{msg}</div>}
        </div>
        <div className="mt-4 text-dim text-[12px] leading-relaxed">
          支持种类：{d?.kinds.join(' / ')}。连通测试针对 HTTP 端点真实探测，受出域开关约束（C-22 防 SSRF）。
        </div>
        <div className="mt-3"><a className={btnGhost} href="#" onClick={(e) => { e.preventDefault(); load() }}>刷新</a></div>
      </Card>
    </div>
  )
}
