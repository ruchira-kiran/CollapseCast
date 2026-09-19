// Bands come from the API (thresholds 0.30 / 0.50 / 0.80). Colors are the fixed status palette.
export const BAND_META = {
  GREEN: { label: 'Low risk', color: 'var(--status-good)' },
  YELLOW: { label: 'Watch', color: 'var(--status-warning)' },
  ORANGE: { label: 'Elevated', color: 'var(--status-serious)' },
  RED: { label: 'Critical', color: 'var(--status-critical)' },
}

// Segments of the 0-100 failure-score scale, in order.
export const BAND_SEGMENTS = [
  { band: 'GREEN', from: 0, to: 30 },
  { band: 'YELLOW', from: 30, to: 50 },
  { band: 'ORANGE', from: 50, to: 80 },
  { band: 'RED', from: 80, to: 100 },
]

export const points = (score) => Math.round(score * 100)

export function signed(value, digits = 1) {
  const rounded = Number(value.toFixed(digits))
  if (rounded === 0) return (0).toFixed(digits)
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded).toFixed(digits)}`
}
