import BandChip from './BandChip.jsx'
import { points } from '../format.js'

export default function PipelineStages({ result }) {
  const current = result.current_stage.number
  const stages = result.breakdown.stages

  return (
    <section className="card" aria-label="The five-stage cascade">
      <div className="card-head">
        <h2 className="card-title">Cascade: where this company is</h2>
        <span className="card-sub">Each stage feeds the next. A stage is active at 50 or above.</span>
      </div>
      <ol className="pipeline" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {stages.map((s) => {
          const isCurrent = s.stage === current
          const cls = ['stage', s.active ? 'active' : '', isCurrent ? 'current' : ''].join(' ')
          return (
            <li key={s.stage} className={cls} aria-current={isCurrent ? 'step' : undefined}>
              <div className="stage-top">
                <span className="stage-num">{s.stage}</span>
                {isCurrent && <span className="stage-tag">Current</span>}
                {!isCurrent && s.active && <span className="stage-tag muted">Active</span>}
              </div>
              <div className="stage-name">{s.name}</div>
              <div className="stage-desc">{s.description}</div>
              {s.stage === 5 ? (
                <>
                  <BandChip band={result.band} compact />
                  <div className="hint" style={{ marginTop: 8 }}>
                    Riskier than {points(result.scores.priority_percentile)}% of the reference companies
                  </div>
                </>
              ) : (
                <>
                  <div className="stage-value">
                    {points(s.score)}
                    <small>/ 100</small>
                  </div>
                  <div className="meter" aria-hidden="true">
                    <i style={{ width: `${points(s.score)}%` }} />
                  </div>
                </>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
