import { useEffect, useState } from 'react'
import FlipCard, { type BackRow } from '../components/FlipCard'
import { Card, Pill, Row, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPut } from '../lib/api'
import { useAuth } from '../auth'

type CostData = {
  monthly_cap_cny: number
  spent_cny: number
  remaining_cny: number
  total_calls: number
  total_tokens: number
  by_provider: Record<string, number>
  by_scenario: Record<string, number>
  providers: { name: string; model: string; outbound: boolean }[]
}

type ProviderInfo = { name: string; model: string; stub: boolean; outbound: boolean }
type RouteRow = { scenario: string; provider: string; model: string; available: boolean }
type Routing = { routes: RouteRow[]; providers: ProviderInfo[]; default: string | null }

function toRows(obj: Record<string, number>, empty: string): BackRow[] {
  const rows = Object.entries(obj).map(([k, v]) => ({ k, v: String(v) }))
  return rows.length ? rows : [{ k: empty, v: '—' }]
}

export default function Cost() {
  const { user } = useAuth()
  const [c, setC] = useState<CostData | null>(null)
  const [r, setR] = useState<Routing | null>(null)
  const [scenario, setScenario] = useState('')
  const [provider, setProvider] = useState('')
  const [msg, setMsg] = useState('')

  function loadRouting() {
    apiGet<Routing>('/api/routing')
      .then((d) => {
        setR(d)
        if (!provider && d.providers[0]) setProvider(d.providers[0].name)
      })
      .catch(() => setR(null))
  }

  useEffect(() => {
    apiGet<CostData>('/api/cost').then(setC).catch(() => setC(null))
    loadRouting()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function save() {
    if (!scenario.trim()) {
      setMsg('请填场景（如 L07/report）')
      return
    }
    try {
      await apiPut('/api/routing', { scenario: scenario.trim(), provider, actor: user?.username || '未知' })
      setMsg(`已保存：${scenario.trim()} → ${provider}`)
      setScenario('')
      loadRouting()
    } catch (e) {
      setMsg(`保存失败：${(e as Error).message}`)
    }
  }

  async function remove(s: string) {
    await apiDelete(`/api/routing/${s}`)
    setMsg(`已删除：${s}（回退默认模型）`)
    loadRouting()
  }

  if (!c) return <div className="text-dim">加载中…</div>

  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="本月成本" value={`¥${c.spent_cny}`} valueClass="text-terra" delay={0}
          back={[{ k: '上限', v: `¥${c.monthly_cap_cny}` }, { k: '余量', v: `¥${c.remaining_cny}` }]} />
        <FlipCard label="调用次数" value={String(c.total_calls)} delay={80}
          back={toRows(c.by_scenario, '(暂无调用)')} />
        <FlipCard label="Token 总量" value={String(c.total_tokens)} delay={160}
          back={toRows(c.by_provider, '(暂无)')} />
        <FlipCard label="预算余量" value={`¥${c.remaining_cny}`} valueClass="text-ochre" delay={240}
          back={[{ k: '上限', v: `¥${c.monthly_cap_cny}` }, { k: '已用', v: `¥${c.spent_cny}` }]} />
      </div>

      <div className="grid grid-cols-2 gap-[18px] items-start">
        {/* 可用模型档位 */}
        <Card>
          <SectionTitle>可用模型档位（来自 .env / LLM_PROFILES）</SectionTitle>
          {(r?.providers ?? []).map((p) => (
            <Row key={p.name}>
              <span>
                {p.name} <span className="text-dim text-[13px]">{p.model}</span>
              </span>
              <span className="flex gap-1.5">
                {p.stub && <Pill tone="warn">stub</Pill>}
                <Pill tone={p.outbound ? 'warn' : 'ok'}>{p.outbound ? '出域' : '本地'}</Pill>
              </span>
            </Row>
          ))}
          <div className="text-dim text-[13px] mt-3">
            没配 API Key 时档位以 stub 占位，路由仍可演示；配置见系统设置 / .env 的 LLM_PROFILES。
          </div>
        </Card>

        {/* 场景 → 模型 路由（§4.4 按功能分配大模型，可编辑） */}
        <Card>
          <SectionTitle>场景 → 模型路由 · 按功能分配大模型</SectionTitle>
          {(r?.routes ?? []).map((row) => (
            <Row key={row.scenario}>
              <span className="font-mono text-[13px]">{row.scenario}</span>
              <span className="flex items-center gap-2">
                <Pill tone={row.available ? 't' : 'warn'}>{row.provider}</Pill>
                <span className="text-dim text-[12px]">{row.model}</span>
                <button className="text-dim hover:text-terra text-[16px] leading-none" title="删除（回退默认）"
                  onClick={() => remove(row.scenario)}>×</button>
              </span>
            </Row>
          ))}
          {!r?.routes?.length && <div className="text-dim text-[13px] py-2">暂无路由，默认全用 {r?.default}</div>}

          <div className="mt-4 flex gap-2 items-center">
            <input value={scenario} onChange={(e) => setScenario(e.target.value)} placeholder="场景，如 L07/report"
              className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] font-mono" />
            <select value={provider} onChange={(e) => setProvider(e.target.value)}
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]">
              {(r?.providers ?? []).map((p) => (
                <option key={p.name} value={p.name}>{p.name}</option>
              ))}
            </select>
            <button className={btnPrimary} onClick={save}>保存</button>
          </div>
          {msg && <div className="text-[13px] text-sage mt-2">{msg}</div>}
          <div className="text-dim text-[13px] mt-3">
            分诊/降噪 → 便宜快模型；调查/关联/报告 → 强模型。改动持久化（DB），写操作记审计。
          </div>
        </Card>
      </div>

      <div className="text-dim text-[13px] mt-3">
        数字为本进程真实统计；离线 stub 下成本为 0，调用后实时累计。
        <a className={`${btnGhost} ml-3 inline-block`} href="/cost" onClick={(e) => { e.preventDefault(); loadRouting() }}>
          刷新路由
        </a>
      </div>
    </div>
  )
}
