export default function Placeholder({ label, tag }: { label: string; tag?: string }) {
  return (
    <div className="text-center py-24 text-dim">
      <div className="text-[40px] font-serif opacity-50 mb-4">◇</div>
      <div className="text-lg text-ink mb-2">
        {label}
        {tag && <span className="ml-2 text-[12px] border border-line px-1.5 rounded-full">{tag}</span>}
      </div>
      <div>模块开发中 —— 框架已就位，按设计语言逐步填充。</div>
    </div>
  )
}
