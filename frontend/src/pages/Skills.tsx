import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle, btnGhost, btnPrimary } from '../components/ui'
import { Modal } from '../components/Modal'
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api'

type Skill = {
  id: string
  name: string
  category: string
  scenario: string
  steps: string[]
  refs: string[]
  enabled: boolean
  version: number
}
type Data = { skills: Skill[]; categories: string[] }
const CAT_TONE: Record<string, 'ok' | 'warn' | 't' | 'dim'> = { 调查SOP: 'ok', 处置SOP: 't', 排障SOP: 'warn', 合规SOP: 'dim' }
const blank = { name: '', category: '调查SOP', scenario: '', stepsText: '' }

export default function Skills() {
  const [d, setD] = useState<Data | null>(null)
  const [dlg, setDlg] = useState<{ id?: string; form: typeof blank } | null>(null)
  const [msg, setMsg] = useState('')

  function load() {
    apiGet<Data>('/api/skills').then(setD)
  }
  useEffect(load, [])

  async function save() {
    if (!dlg) return
    const steps = dlg.form.stepsText.split('\n').map((s) => s.trim()).filter(Boolean)
    if (!dlg.form.name.trim() || steps.length === 0) return setMsg('名称与至少一个步骤不能为空')
    const body = { name: dlg.form.name.trim(), category: dlg.form.category, scenario: dlg.form.scenario.trim(), steps }
    try {
      if (dlg.id) await apiPut(`/api/skills/${dlg.id}`, body)
      else await apiPost('/api/skills', body)
      setMsg(dlg.id ? '已更新' : '已新建 SOP')
      setDlg(null)
      load()
    } catch (e) {
      setMsg(`失败：${(e as Error).message}`)
    }
  }
  async function toggle(s: Skill) {
    await apiPut(`/api/skills/${s.id}`, { enabled: !s.enabled })
    load()
  }
  async function remove(s: Skill) {
    if (!confirm(`删除 SOP「${s.name}」？`)) return
    await apiDelete(`/api/skills/${s.id}`)
    load()
  }
  function edit(s: Skill) {
    setDlg({ id: s.id, form: { name: s.name, category: s.category, scenario: s.scenario, stepsText: s.steps.join('\n') } })
  }
  function f(k: keyof typeof blank, v: string) {
    if (dlg) setDlg({ ...dlg, form: { ...dlg.form, [k]: v } })
  }

  return (
    <div className="flex flex-col gap-[24px]">
      <Card>
        <SectionTitle>Skills · 标准操作流程（SOP）— 调查/处置时给可照做的步骤（ADR-0013）</SectionTitle>
        <div className="text-dim text-[12px] mb-3">
          SOP = "怎么做某类事"的步骤清单（按场景自动匹配进调查结论）；区别于 SOAR Playbook(自动处置)/Prompt(模型人设)/知识库(经验文档)。
        </div>
        <div className="grid grid-cols-2 gap-4">
          {d?.skills.map((s) => (
            <div key={s.id} className={`border border-line rounded-lg p-3 ${!s.enabled ? 'opacity-50' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium">{s.name}</span>
                <Pill tone={CAT_TONE[s.category] || 'dim'}>{s.category}</Pill>
                {s.scenario && <Pill tone="dim">场景:{s.scenario}</Pill>}
              </div>
              <ol className="list-decimal ml-5 text-[13px] text-dim space-y-0.5">
                {s.steps.map((st, i) => <li key={i}>{st}</li>)}
              </ol>
              <div className="flex gap-3 mt-2 text-[12px]">
                <button onClick={() => edit(s)} className="text-dim hover:text-sage">编辑</button>
                <button onClick={() => toggle(s)} className="text-dim hover:text-clay">{s.enabled ? '停用' : '启用'}</button>
                <button onClick={() => remove(s)} className="text-dim hover:text-terra">删除</button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button className={btnPrimary} onClick={() => setDlg({ form: { ...blank, category: d?.categories[0] || '调查SOP' } })}>+ 新建 SOP</button>
          {msg && <span className="text-sage text-[13px]">{msg}</span>}
        </div>
      </Card>

      <Modal open={!!dlg} title={dlg?.id ? `编辑 ${dlg.id}` : '新建 SOP'} onClose={() => setDlg(null)}>
        {dlg && d && (
          <div className="flex flex-col gap-3">
            <input value={dlg.form.name} onChange={(e) => f('name', e.target.value)} placeholder="SOP 名称"
              className="bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            <div className="flex gap-2">
              <select value={dlg.form.category} onChange={(e) => f('category', e.target.value)}
                className="flex-1 bg-paper2 border border-line rounded-lg px-2 py-2 text-[13px]">
                {d.categories.map((c) => <option key={c}>{c}</option>)}
              </select>
              <input value={dlg.form.scenario} onChange={(e) => f('scenario', e.target.value)} placeholder="适用场景关键词，如 勒索 / 横向移动"
                className="flex-1 bg-paper2 border border-line rounded-lg px-3 py-2 text-[13px]" />
            </div>
            <textarea value={dlg.form.stepsText} onChange={(e) => f('stepsText', e.target.value)} rows={6}
              placeholder="操作步骤，每行一步"
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
