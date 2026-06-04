import type { ReactNode } from 'react'

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean
  title: string
  children: ReactNode
  onClose: () => void
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-paper border border-line rounded-[10px] p-6 w-[440px] fade-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="font-serif text-lg mb-4">{title}</div>
        {children}
      </div>
    </div>
  )
}
