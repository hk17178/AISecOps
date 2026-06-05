import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { apiDelete, apiGet, apiPost } from '../lib/api'
import { useAuth } from '../auth'

type PromptMeta = { key: string; active_version: number; versions: number; updated: string }
type Version = { key: string; version: number; content: string; note: string; author: string; ts: string; active: boolean }
type Detail = { key: string; active_version: number; versions: Version[] }

export default function Prompt() {
  const { user } = useAuth()
  const actor = user?.username || '未知'
  const [list, setList] = useState<PromptMeta[]>([])
  const [sel, setSel] = useState('')
  const [detail, setDetail] = useState<Detail | null>(null)
  const [content, setContent] = useState('')
  const [note, setNote] = useState('')
  const [msg, setMsg] = useState('')

  function loadList() {
    apiGet<{ prompts: PromptMeta[] }>('/api/prompts').then((d) => {
      setList(d.prompts)
      if (!sel && d.prompts[0]) select(d.prompts[0].key)
    })
  }
  function select(key: string) {
    setSel(key)
    apiGet<Detail>(`/api/prompts/${key}`).then((d) => {
      setDetail(d)
      const act = d.versions.find((v) => v.active)
      setContent(act?.content || '')
      setNote('')
    })
  }
  useEffect(loadList, [])

  async function save() {
    if (!content.trim()) return setMsg('内容不能为空')
    await apiPost(`/api/prompts/${sel}`, { content, note: note.trim(), actor })
    setMsg('已保存为新版本')
    select(sel)
    loadList()
  }
  async function rollback(version: number) {
    await apiPost(`/api/prompts/${sel}/rollback`, { version, actor })
    setMsg(`已回滚到 v${version}`)
    select(sel)
    loadList()
  }
  async function createKey() {
    const key = prompt('新 Prompt key（形如 hunting/system）')?.trim()
    if (!key) return
    if (!key.includes('/')) return setMsg('key 形如 scenario/system')
    try {
      await apiPost(`/api/prompts/${key}`, { content: '你是…（请编辑）', note: '新建', actor })
      setMsg(`已新建 ${key}`)
      loadList()
      select(key)
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }
  async function removeKey() {
    if (!sel || !confirm(`删除 Prompt「${sel}」及其所有版本？`)) return
    await apiDelete(`/api/prompts/${sel}`)
    setMsg(`已删除 ${sel}`)
    setSel('')
    setDetail(null)
    setContent('')
    loadList()
  }

  const activeVer = detail?.versions.find((v) => v.active)

  return (
    <div className="grid grid-cols-[240px_1fr] gap-[34px] items-start">
      {/* Prompt 列表 */}
      <Card>
        <div className="flex items-center justify-between mb-1">
          <SectionTitle>Prompt（版本化 P-6）</SectionTitle>
          <button onClick={createKey} className="text-sage hover:underline text-[12px]">+ 新建</button>
        </div>
        {list.map((p) => (
          <button key={p.key} onClick={() => select(p.key)}
            className={`block w-full text-left py-2 px-2 rounded-lg text-[13px] ${sel === p.key ? 'bg-[#f3ead7] font-semibold' : 'hover:bg-paper2'}`}>
            <div className="font-mono truncate">{p.key}</div>
            <div className="text-dim text-[11px]">v{p.active_version} · {p.versions} 个版本</div>
          </button>
        ))}
      </Card>

      {/* 编辑 + 历史 */}
      <div className="flex flex-col gap-[18px]">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <SectionTitle>{sel ? `编辑 ${sel}` : '选择一个 Prompt'}</SectionTitle>
            <span className="flex items-center gap-2">
              {activeVer && <Pill tone="ok">当前 v{activeVer.version}</Pill>}
              {sel && <button onClick={removeKey} className="text-dim hover:text-terra text-[12px]">删除</button>}
            </span>
          </div>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={8}
            className="w-full bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px] leading-relaxed font-mono" />
          <div className="flex gap-2 mt-2 items-center">
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="本次修改说明（可空）"
              className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <button className={btnPrimary} onClick={save}>保存为新版本</button>
          </div>
          {msg && <div className="text-sage text-[13px] mt-2">{msg}</div>}
        </Card>

        <Card>
          <SectionTitle>版本历史 · 可回滚</SectionTitle>
          {detail?.versions.map((v) => (
            <div key={v.version} className="py-2.5 border-b border-dotted border-line text-[13.5px]">
              <div className="flex items-center gap-2">
                <span className="font-semibold">v{v.version}</span>
                {v.active && <Pill tone="ok">活跃</Pill>}
                <span className="text-dim text-[12px]">{v.author} · {v.ts}{v.note && ` · ${v.note}`}</span>
                {!v.active && (
                  <button className={`${btnGhost} ml-auto !py-1 !px-2 text-[12px]`} onClick={() => rollback(v.version)}>
                    回滚到此版本
                  </button>
                )}
              </div>
              <div className="text-dim text-[12px] mt-1 font-mono whitespace-pre-wrap line-clamp-2">{v.content}</div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}
