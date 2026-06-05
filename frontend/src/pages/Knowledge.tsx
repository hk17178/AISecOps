import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { Modal } from '../components/Modal'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'

type DocMeta = { id: string; title: string; category: string; source: string; version: number; updated: string }
type DocFull = DocMeta & { content: string }
type Hit = { doc_id: string; title: string; category: string; text: string; score: number }

const blank = { title: '', category: '历史告警处理记录', content: '', source: '' }

export default function Knowledge() {
  const [docs, setDocs] = useState<DocMeta[]>([])
  const [cats, setCats] = useState<string[]>([])
  const [chunks, setChunks] = useState(0)
  const [msg, setMsg] = useState('')

  // 新建/编辑弹框
  const [dlg, setDlg] = useState<{ id?: string; form: typeof blank } | null>(null)
  const [busy, setBusy] = useState(false)

  // 检索
  const [query, setQuery] = useState('主机疑似勒索 卷影被删')
  const [hits, setHits] = useState<Hit[] | null>(null)

  function load() {
    apiGet<{ docs: DocMeta[]; categories: string[]; indexed_chunks: number }>('/api/knowledge').then((d) => {
      setDocs(d.docs)
      setCats(d.categories)
      setChunks(d.indexed_chunks)
    })
  }
  useEffect(load, [])

  async function openEdit(id: string) {
    const d = await apiGet<DocFull>(`/api/knowledge/${id}`)
    setDlg({ id, form: { title: d.title, category: d.category, content: d.content, source: d.source } })
  }

  async function save() {
    if (!dlg) return
    if (!dlg.form.title.trim() || !dlg.form.content.trim()) {
      setMsg('标题与正文不能为空')
      return
    }
    setBusy(true)
    try {
      if (dlg.id) await apiPut(`/api/knowledge/${dlg.id}`, dlg.form)
      else await apiPost('/api/knowledge', dlg.form)
      setMsg(dlg.id ? '已更新并重建索引' : '已新建并入索引')
      setDlg(null)
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  async function remove(d: DocMeta) {
    if (!confirm(`删除「${d.title}」？同时移除其检索索引。`)) return
    await apiDelete(`/api/knowledge/${d.id}`)
    setMsg(`已删除 ${d.id}`)
    load()
  }

  async function search() {
    if (!query.trim()) return
    const r = await apiPost<{ hits: Hit[] }>('/api/knowledge/search', { query: query.trim(), top_k: 3 })
    setHits(r.hits)
  }

  function field(k: keyof typeof blank, v: string) {
    if (dlg) setDlg({ ...dlg, form: { ...dlg.form, [k]: v } })
  }

  return (
    <div className="grid grid-cols-[1.3fr_1fr] gap-[34px] items-start">
      {/* 知识库 CRUD */}
      <Card>
        <SectionTitle>知识库语料 · 增删改（写时即建检索索引）</SectionTitle>
        <div className="text-dim text-[12px] mb-3">
          共 {docs.length} 篇 · 已索引 {chunks} 块 · 经 Embedding→召回→Reranker(C-7) 供分诊检索增强
        </div>
        {docs.length === 0 && <div className="text-dim text-[13px] py-2">暂无知识。新建一篇案例/手册即可被检索召回。</div>}
        {docs.map((d) => (
          <div key={d.id} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] text-dim">{d.id}</span>
                <span className="truncate">{d.title}</span>
                <Pill tone="dim">{d.category}</Pill>
              </div>
              <div className="text-dim text-[12px]">v{d.version} · {d.source || '—'} · {d.updated}</div>
            </span>
            <span className="shrink-0 flex gap-3 items-center">
              <button onClick={() => openEdit(d.id)} className="text-dim hover:text-sage text-[13px]">编辑</button>
              <button onClick={() => remove(d)} className="text-dim hover:text-terra text-[16px] leading-none" title="删除">×</button>
            </span>
          </div>
        ))}
        <div className="mt-4 flex items-center gap-3">
          <button className={btnPrimary} onClick={() => setDlg({ form: { ...blank, category: cats[0] || blank.category } })}>+ 新建知识</button>
          {msg && <span className="text-sage text-[13px]">{msg}</span>}
        </div>
      </Card>

      {/* RAG 检索体验（召回 + 重排 + 出处） */}
      <Card>
        <SectionTitle>检索 · 召回→Reranker 重排→带出处</SectionTitle>
        <div className="flex flex-col gap-2">
          <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={2}
            placeholder="输入一段情境，看知识库召回什么"
            className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
          <button className={btnGhost} onClick={search}>检索</button>
        </div>
        <div className="mt-3">
          {hits === null && <div className="text-dim text-[13px]">输入情境后点检索，看 RAG 召回与出处。</div>}
          {hits?.length === 0 && <div className="text-dim text-[13px]">无命中。先在左侧建几篇知识。</div>}
          {hits?.map((h, i) => (
            <div key={i} className="py-2.5 border-b border-dotted border-line text-[13px]">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] text-sage">[{h.doc_id}]</span>
                <span className="truncate">{h.title}</span>
                <Pill tone="dim">{h.category}</Pill>
                <span className="text-dim text-[12px] ml-auto shrink-0">分 {h.score}</span>
              </div>
              <div className="text-dim text-[12.5px] mt-1 line-clamp-3">{h.text}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* 新建/编辑弹框 */}
      <Modal open={!!dlg} title={dlg?.id ? `编辑知识 ${dlg.id}` : '新建知识'} onClose={() => setDlg(null)}>
        {dlg && (
          <div className="flex flex-col gap-3">
            <input value={dlg.form.title} onChange={(e) => field('title', e.target.value)} placeholder="标题"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <select value={dlg.form.category} onChange={(e) => field('category', e.target.value)}
              className="bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
              {(cats.length ? cats : [blank.category]).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <textarea value={dlg.form.content} onChange={(e) => field('content', e.target.value)} rows={7}
              placeholder="正文（案例经验/手册/规程……检索会切块向量化）"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <input value={dlg.form.source} onChange={(e) => field('source', e.target.value)} placeholder="来源（可空）"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2 justify-end">
              <button className={btnGhost} onClick={() => setDlg(null)}>取消</button>
              <button className={btnPrimary} onClick={save} disabled={busy}>{busy ? '保存中…' : '保存'}</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
