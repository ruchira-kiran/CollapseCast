import { BAND_META } from '../format.js'

// One glyph per band so the status never relies on color alone.
const GLYPHS = {
  GREEN: <path d="M5.5 10.5l3 3 6-6.5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  YELLOW: (
    <>
      <path d="M3.5 10s2.6-4.2 6.5-4.2S16.5 10 16.5 10s-2.6 4.2-6.5 4.2S3.5 10 3.5 10z" fill="none" stroke="#0b0b0b" strokeWidth="1.6" />
      <circle cx="10" cy="10" r="1.7" fill="#0b0b0b" />
    </>
  ),
  ORANGE: (
    <>
      <path d="M10 6v5" stroke="#0b0b0b" strokeWidth="2" strokeLinecap="round" />
      <circle cx="10" cy="14" r="1.1" fill="#0b0b0b" />
    </>
  ),
  RED: (
    <>
      <path d="M10 5.5v6" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="10" cy="14.2" r="1.2" fill="#fff" />
    </>
  ),
}
const SHAPES = {
  GREEN: <circle cx="10" cy="10" r="9" />,
  YELLOW: <circle cx="10" cy="10" r="9" />,
  ORANGE: <path d="M10 1.5l9 16H1z" strokeLinejoin="round" />,
  RED: <path d="M6.2 1h7.6L19 6.2v7.6L13.8 19H6.2L1 13.8V6.2z" strokeLinejoin="round" />,
}

export default function BandChip({ band, compact = false }) {
  const meta = BAND_META[band]
  return (
    <span className="chip" style={{ '--band': meta.color }}>
      <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
        <g fill={meta.color} stroke={meta.color}>{SHAPES[band]}</g>
        {GLYPHS[band]}
      </svg>
      {compact ? band : `${band} · ${meta.label}`}
    </span>
  )
}
