import { useEffect, useState } from 'react'

// 把 "1,284" / "¥312" / "78%" 这类文本里的数字从 0 缓动到目标
export function useCountUp(text: string, duration = 900): string {
  const [display, setDisplay] = useState(text)

  useEffect(() => {
    const m = text.match(/^([^\d]*)([\d,]+)(.*)$/)
    if (!m) {
      setDisplay(text)
      return
    }
    const pre = m[1]
    const suf = m[3]
    const target = parseInt(m[2].replace(/,/g, ''), 10)
    if (Number.isNaN(target)) {
      setDisplay(text)
      return
    }

    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      let p = Math.min(1, (t - t0) / duration)
      p = 1 - Math.pow(1 - p, 3) // easeOutCubic
      setDisplay(pre + Math.round(target * p).toLocaleString('en-US') + suf)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [text, duration])

  return display
}
