import BandChip from './BandChip.jsx'
import { BAND_META, BAND_SEGMENTS, points } from '../format.js'

export default function BandHero({ result }) {
  const { scores, band, breakdown, current_stage: stage, name } = result
  const score = points(scores.failure_raw)

  return (
    <section className="card" aria-label="Failure score and priority band">
      <div className="hero">
        <div>
          <p className="hero-label">{name ? `${name} · failure score` : 'Failure score'}</p>
          <div className="hero-score">
            <span className="hero-number">{score}</span>
            <span className="hero-unit">/ 100</span>
          </div>
        </div>
        <div className="hero-body">
          <BandChip band={band} />
          <p className="summary">{breakdown.summary}</p>
          <p className="secondary" style={{ fontSize: 13 }}>
            Current stage:{' '}
            <b>{stage.number ? `${stage.number} · ${stage.name}` : 'none active'}</b>
            <span className="muted"> ({stage.description})</span>
          </p>
        </div>

        <div className="bandscale">
          <div
            className="bandscale-track"
            role="img"
            aria-label={`Failure score ${score} of 100 on the band scale: green below 30, yellow 30 to 49, orange 50 to 79, red 80 and above`}
          >
            {BAND_SEGMENTS.map((s) => (
              <div key={s.band} className="bandscale-seg" style={{ width: `${s.to - s.from}%`, background: BAND_META[s.band].color }} />
            ))}
            <div className="bandscale-marker" style={{ left: `${Math.min(100, Math.max(0, score))}%` }} />
          </div>
          <div className="bandscale-labels" aria-hidden="true">
            <span style={{ left: '0%' }}>0</span>
            <span style={{ left: '30%' }}>30 yellow</span>
            <span style={{ left: '50%' }}>50 orange</span>
            <span style={{ left: '80%' }}>80 red</span>
          </div>
        </div>
      </div>
    </section>
  )
}
