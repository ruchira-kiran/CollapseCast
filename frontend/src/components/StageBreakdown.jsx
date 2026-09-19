import { points, signed } from '../format.js'

function ContributionTable({ stage }) {
  const logOdds = stage.stage === 4
  return (
    <table className="data">
      <thead>
        <tr>
          <th>Input</th>
          <th className="n">Value</th>
          <th className="n">{logOdds ? 'Log-odds' : 'Points'}</th>
        </tr>
      </thead>
      <tbody>
        {stage.contributions.map((c) => (
          <tr key={c.signal}>
            <td>{c.label}</td>
            <td className="n">{c.value.toFixed(2)}</td>
            <td className="n">{logOdds ? signed(c.impact, 2) : signed(c.impact * 100)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function StageBreakdown({ result }) {
  const [risk, demand, behavior, failure] = result.breakdown.stages
  const d = demand.detail
  return (
    <section className="card">
      <details className="breakdown">
        <summary>Stage-by-stage breakdown: which inputs moved each score</summary>
        <div className="breakdown-grid">
          <div>
            <h3>1 · {risk.name} ({points(risk.score)})</h3>
            <p className="unit">Random Forest, {risk.unit}</p>
            <ContributionTable stage={risk} />
          </div>
          <div>
            <h3>2 · {demand.name} ({points(demand.score)})</h3>
            <p className="unit">{d.method}</p>
            <p className="secondary" style={{ fontSize: 13.5 }}>
              {d.change_detected
                ? `Decline detected from week ${d.change_week}: ${d.baseline_weekly_postings} to ${d.recent_weekly_postings} postings a week, a ${Math.round(d.drop_fraction * 100)}% drop. The score is that drop.`
                : 'No sustained decline detected, so the score is 0.'}
            </p>
          </div>
          <div>
            <h3>3 · {behavior.name} ({points(behavior.score)})</h3>
            <p className="unit">Random Forest, {behavior.unit}. Demand score is an input.</p>
            <ContributionTable stage={behavior} />
          </div>
          <div>
            <h3>4 · {failure.name} ({points(failure.score)})</h3>
            <p className="unit">XGBoost, log-odds; they sum with a bias of {signed(failure.detail.bias, 2)} to the margin.</p>
            <ContributionTable stage={failure} />
          </div>
        </div>
      </details>
    </section>
  )
}
