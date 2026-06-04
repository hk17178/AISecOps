import { useEffect, useState } from 'react'
import FlipCard from '../components/FlipCard'
import { Card, Pill, SectionTitle, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type Rule = { id: string; name: string; kind: string; pattern: string; enabled: boolean; hits: number }
type Suppressed = { id: string; host: string; title: string; reason: string }
type Stats = {
  raw_total: number
  after: number
  reduction_pct: number
  breakdown: { exact_window_merged: number; suppressed: number }
  rules: Rule[]
  rules_total: number
  rules_enabled: number
  suppressed_recent: Suppressed[]
}

const KIND_LABEL: Record<string, string> = { host: '主机通配', source: '来源', keyword: '关键字', ip: 'IP' }

export default function Dedupe() {
  const { user } = useAuth()
  const [s, setS] = useState<Stats | null>(null)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('keyword')
  const [pattern, setPattern] = useState('')
  const [msg, setMsg] = useState('')
  const actor = user?.username || '未知'

  function load() {
    apiGet<Stats>('/api/dedupe/stats').then(setS).catch(() => setS(null))
  }
  useEffect(load, [])

  async function addRule() {
    if (!name.trim() || !pattern.trim()) {
      setMsg('规则名与匹配内容不能为空')
      return
    }
    try {
      await apiPost('/api/suppression-rules', { name: name.trim(), kind, pattern: pattern.trim(), actor })
      setMsg(`已新建规则「${name.trim()}」，即时生效`)
      setName('')
      setPattern('')
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }

  async function toggle(r: Rule) {
    await apiPut(`/api/suppression-rules/${r.id}`, { enabled: !r.enabled, actor })
    load()
  }
  async function remove(r: Rule) {
    await apiDelete(`/api/suppression-rules/${r.id}`)
    setMsg(`已删除规则「${r.name}」`)
    load()
  }

  if (!s) return <div className="text-dim">加载中…</div>

  const merged = s.breakdown.exact_window_merged
  const supp = s.breakdown.suppressed
  const maxBar = Math.max(merged, supp, 1)

  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="原始事件数" value={s.raw_total.toLocaleString('en-US')} delay={0}
          back={[{ k: '含被折叠/抑制', v: `${merged + supp}` }]} />
        <FlipCard label="降噪后" value={s.after.toLocaleString('en-US')} valueClass="text-terra" delay={80}
          back={[{ k: '精确去重+归并', v: `-${merged}` }, { k: '抑制规则', v: `-${supp}` }]} />
        <FlipCard label="降噪率" value={`${s.reduction_pct}%`} valueClass="text-ochre" delay={160}
          back={[{ k: '目标', v: '≥70%' }]} />
        <FlipCard label="抑制规则" value={String(s.rules_total)} delay={240}
          back={[{ k: '启用', v: String(s.rules_enabled) }, { k: '停用', v: String(s.rules_total - s.rules_enabled) }]} />
      </div>

      <div className="grid grid-cols-[1.7fr_1fr] gap-[34px] items-start">
        <div className="flex flex-col gap-[18px]">
          {/* 降噪手段拆分（真实数字） */}
          <Card>
            <SectionTitle>降噪手段拆分 · 分诊前执行</SectionTitle>
            {[
              { label: '精确去重 + 时间窗归并（同指纹）', v: merged },
              { label: '抑制规则（已知噪声，标记可回溯）', v: supp },
            ].map((m) => (
              <div key={m.label} className="mb-3">
                <div className="flex justify-between text-[14px] mb-1">
                  <span>{m.label}</span>
                  <b>{m.v.toLocaleString('en-US')}</b>
                </div>
                <div className="h-2 bg-paper2 rounded-full overflow-hidden">
                  <div className="h-full bg-terra rounded-full bar-grow" style={{ width: `${(m.v / maxBar) * 100}%` }} />
                </div>
              </div>
            ))}
            <div className="flex justify-between text-[14px] mb-1 opacity-50">
              <span>关联聚合（L08 同一事件）</span>
              <Pill tone="warn">下一步</Pill>
            </div>
            <div className="text-dim text-[13px] mt-2">
              数字来自真实告警库：去重靠指纹 hash(来源+主机+标题)，归并靠 5min 滑动窗，抑制靠下方规则。
            </div>
          </Card>

          {/* 被抑制告警（可回溯，非丢弃） */}
          <Card>
            <SectionTitle>最近被抑制告警 · 可回溯（标记而非丢弃）</SectionTitle>
            {s.suppressed_recent.length === 0 && <div className="text-dim text-[13px] py-2">暂无被抑制告警</div>}
            {s.suppressed_recent.map((a) => (
              <div key={a.id} className="flex justify-between items-center py-2 border-b border-dotted border-line text-[13.5px]">
                <span className="truncate mr-2">
                  <span className="text-dim font-mono text-[12px]">{a.id}</span> {a.host} · {a.title}
                </span>
                <span className="text-dim text-[12px] shrink-0">{a.reason}</span>
              </div>
            ))}
          </Card>
        </div>

        {/* 抑制规则 CRUD */}
        <Card>
          <SectionTitle>抑制规则 · 增删改（即时生效）</SectionTitle>
          {s.rules.map((r) => (
            <div key={r.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
              <span className="min-w-0">
                <div className="truncate">{r.name}</div>
                <div className="text-dim text-[12px]">
                  {KIND_LABEL[r.kind] || r.kind}: <span className="font-mono">{r.pattern}</span> · 命中 {r.hits}
                </div>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <button onClick={() => toggle(r)}
                  className={`text-[12px] border rounded-full px-2 ${r.enabled ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                  {r.enabled ? '启用' : '停用'}
                </button>
                <button onClick={() => remove(r)} className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
              </span>
            </div>
          ))}

          <div className="mt-4 flex flex-col gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="规则名，如 健康检查心跳"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2">
              <select value={kind} onChange={(e) => setKind(e.target.value)}
                className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                <option value="keyword">关键字</option>
                <option value="host">主机通配</option>
                <option value="source">来源</option>
                <option value="ip">IP</option>
              </select>
              <input value={pattern} onChange={(e) => setPattern(e.target.value)}
                placeholder={kind === 'host' ? 'DEV-*' : kind === 'ip' ? '185.x.x.x' : '匹配内容'}
                className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] font-mono" />
            </div>
            <button className={btnPrimary} onClick={addRule}>+ 新建规则</button>
            {msg && <div className="text-[13px] text-sage">{msg}</div>}
          </div>
        </Card>
      </div>
    </div>
  )
}
