import { useState, type ReactNode } from 'react'

export function Fold({
  title,
  meta,
  children,
  forceOpen = false,
}: {
  title: string
  meta?: string
  children: ReactNode
  forceOpen?: boolean
}) {
  const [open, setOpen] = useState(false)
  const shown = forceOpen || open

  return (
    <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left"
        onClick={() => setOpen(!open)}
        aria-expanded={shown}
      >
        <span className="font-semibold text-[#0B3D73]">{title}</span>
        <span className="shrink-0 text-sm text-[#5B6B7C]">
          {meta} {shown ? '▾' : '▸'}
        </span>
      </button>
      {shown ? <div className="border-t border-[#E6EEF8]">{children}</div> : null}
    </section>
  )
}
