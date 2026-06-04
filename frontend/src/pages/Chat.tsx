import { useState } from 'react'
import { btnPrimary } from '../components/ui'

type Msg = { role: 'u' | 'a'; text: string; cite?: string }

const INIT: Msg[] = [
  { role: 'a', text: '你好，我是安全运营助手。可以问我告警、资产、情报相关问题。' },
  { role: 'u', text: '今天有几个真威胁待处置？' },
  {
    role: 'a',
    text: '当前有 3 个真威胁待处置：WIN-APP-07 横移(0.94)、DEV-12 C2 外连(0.88)，以及一条等你研判。',
    cite: '数据来源：告警库 09:45 快照',
  },
]

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>(INIT)
  const [text, setText] = useState('')

  function send() {
    if (!text.trim()) return
    setMsgs((m) => [
      ...m,
      { role: 'u', text },
      { role: 'a', text: '（接 L02 Investigation Agent，当前为示意回复）', cite: '示意' },
    ])
    setText('')
  }

  return (
    <div className="max-w-[760px]">
      <div className="flex flex-col gap-3.5 mb-4">
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`px-4 py-3 rounded-xl text-[14px] max-w-[75%] ${
              m.role === 'u'
                ? 'self-end bg-[#e7dcc6]'
                : 'self-start bg-paper border border-line'
            }`}
          >
            {m.text}
            {m.cite && <div className="text-dim text-[12px] mt-1.5">{m.cite}</div>}
          </div>
        ))}
      </div>
      <div className="flex gap-2.5">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="输入问题…"
          className="flex-1 border border-line rounded-lg bg-bg px-3.5 py-3 outline-none focus:border-clay"
        />
        <button onClick={send} className={btnPrimary}>
          发送
        </button>
      </div>
    </div>
  )
}
