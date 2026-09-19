import { FIELDS } from '../signals.js'

function Sparkline({ values }) {
  if (values.length < 2) return null
  const max = Math.max(...values, 1)
  const step = 100 / (values.length - 1)
  const pts = values.map((v, i) => `${(i * step).toFixed(2)},${(30 - (v / max) * 28).toFixed(2)}`).join(' ')
  return (
    <svg className="sparkline" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={pts} fill="none" stroke="var(--series-1)" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

export default function SignalForm({ samples, selected, form, postings, postingsError, onPick, onName, onValue, onPostings }) {
  return (
    <section className="card form-card" aria-label="Company signals">
      <h2 className="card-title">Company signals</h2>

      <div className="field">
        <label htmlFor="sample">Start from a sample company</label>
        <select id="sample" value={selected} onChange={(e) => onPick(e.target.value)}>
          <option value="">Custom (edited)</option>
          {samples.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name}
              {s.sector ? ` · ${s.sector}` : ''}
            </option>
          ))}
        </select>
        <p className="hint">Samples are ordered healthiest to sickest and were not used to train the models.</p>
      </div>

      <div className="field">
        <label htmlFor="name">Company name (optional)</label>
        <input id="name" type="text" maxLength={120} value={form.name} onChange={(e) => onName(e.target.value)} />
      </div>

      {FIELDS.map((f) => {
        const value = form.values[f.key]
        return (
          <div className="field" key={f.key}>
            <div className="field-row">
              <label htmlFor={f.key}>{f.label}</label>
              <input
                className="num"
                type="number"
                aria-label={`${f.label} value`}
                min={f.min}
                max={f.max}
                step={0.01}
                value={value}
                onChange={(e) => onValue(f, e.target.value)}
              />
            </div>
            <input id={f.key} type="range" min={f.min} max={f.max} step={0.01} value={value} onChange={(e) => onValue(f, e.target.value)} />
            <p className="hint">{f.hint}</p>
          </div>
        )
      })}

      <div className="field">
        <label htmlFor="postings">Weekly job postings (oldest first)</label>
        <textarea id="postings" value={form.postingsText} onChange={(e) => onPostings(e.target.value)} aria-invalid={Boolean(postingsError)} />
        {postingsError ? <p className="field-error">{postingsError}</p> : <p className="hint">The first 8 weeks are the baseline the decline test compares against.</p>}
        <Sparkline values={postings} />
      </div>
    </section>
  )
}
