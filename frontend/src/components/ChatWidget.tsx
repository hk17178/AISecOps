import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { apiPost } from '../lib/api'

type Msg = {
  role: 'u' | 'a'
  text: string
  meta?: { provider: string; model: string; cost: number; stub: boolean }
}

type ChatResp = { content: string; provider: string; model: string; cost_cny: number; stub: boolean }

const GREETING: Msg = {
  role: 'a',
  text: '你好，我是 AISECOPS 安全运营助手。可以问我告警、资产、情报、处置相关的问题。',
}

// 全局常驻 Chat 挂件（右下角）。每页可用，经 /api/chat 真实调网关（L01/chat 场景路由 + C-20 沙箱）。
export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([GREETING])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const loc = useLocation()
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, open])

  async function send() {
    const q = text.trim()
    if (!q || busy) return
    setText('')
    setMsgs((m) => [...m, { role: 'u', text: q }])
    setBusy(true)
    try {
      const r = await apiPost<ChatResp>('/api/chat', { message: q, page: loc.pathname })
      setMsgs((m) => [
        ...m,
        { role: 'a', text: r.content, meta: { provider: r.provider, model: r.model, cost: r.cost_cny, stub: r.stub } },
      ])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'a', text: `调用失败：${(e as Error).message}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* 浮动按钮 */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-terra text-paper text-[22px] shadow-lg
          hover:bg-[#9a4527] transition-transform hover:scale-105 flex items-center justify-center"
        title="安全运营助手"
      >
        {open ? '×' : '💬'}
      </button>

      {/* 对话面板 */}
      {open && (
        <div className="fixed bottom-24 right-6 z-40 w-[380px] max-h-[560px] flex flex-col bg-bg border border-line
          rounded-2xl shadow-2xl overflow-hidden view-enter">
          <div className="px-4 py-3 border-b border-line bg-side flex items-center gap-2">
            <span className="font-serif font-semibold text-[15px]">安全运营助手</span>
            <span className="text-dim text-[12px]">L01/chat · 经网关</span>
          </div>

          <div className="flex-1 overflow-auto p-3.5 flex flex-col gap-3">
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`px-3.5 py-2.5 rounded-xl text-[13.5px] max-w-[85%] whitespace-pre-wrap ${
                  m.role === 'u' ? 'self-end bg-[#e7dcc6]' : 'self-start bg-paper border border-line'
                }`}
              >
                {m.text}
                {m.meta && (
                  <div className="text-dim text-[11px] mt-1.5 flex gap-1.5 items-center">
                    {m.meta.stub && <span className="border border-ochre text-ochre rounded-full px-1.5">stub</span>}
                    <span>{m.meta.provider} · {m.meta.model}</span>
                    {m.meta.cost > 0 && <span>· ¥{m.meta.cost}</span>}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="self-start text-dim text-[13px] px-1">思考中…</div>}
            <div ref={endRef} />
          </div>

          <div className="p-3 border-t border-line flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder="输入问题…"
              className="flex-1 border border-line rounded-lg bg-paper2 px-3 py-2 text-[13.5px] outline-none focus:border-clay"
            />
            <button
              onClick={send}
              disabled={busy}
              className="bg-terra text-paper rounded-lg px-3.5 text-[13.5px] hover:bg-[#9a4527] disabled:opacity-50"
            >
              发送
            </button>
          </div>
        </div>
      )}
    </>
  )
}
