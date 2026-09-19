import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { API_BASE, fetchSamples, predict } from './api.js'
import { DEFAULT_POSTINGS, DEFAULT_VALUES, FIELDS, parsePostings, postingsToText, toPayload } from './signals.js'
import SignalForm from './components/SignalForm.jsx'
import BandHero from './components/BandHero.jsx'
import PipelineStages from './components/PipelineStages.jsx'
import StageBreakdown from './components/StageBreakdown.jsx'
import Actions from './components/Actions.jsx'

// Recharts is the bulk of the bundle; load the chart components (and it) as a separate chunk.
const ImpactChart = lazy(() => import('./components/ImpactChart.jsx'))
const PostingsChart = lazy(() => import('./components/PostingsChart.jsx'))

const DEBOUNCE_MS = 350

const formFromSample = (s) => ({
  name: s.name || '',
  // Two decimals keeps the inputs readable; the app analyzes exactly what the form shows.
  values: Object.fromEntries(FIELDS.map((f) => [f.key, Math.round(s[f.key] * 100) / 100])),
  postingsText: postingsToText(s.weekly_job_postings),
})

const initialForm = { name: '', values: DEFAULT_VALUES, postingsText: postingsToText(DEFAULT_POSTINGS) }

// Theme precedence: ?theme=light|dark in the URL, then the viewer's saved choice, then the OS setting.
function readTheme() {
  const fromUrl = new URLSearchParams(window.location.search).get('theme')
  if (fromUrl === 'light' || fromUrl === 'dark') return fromUrl
  try {
    return localStorage.getItem('collapsecast-theme')
  } catch {
    return null
  }
}

export default function App() {
  const [samples, setSamples] = useState([])
  const [selected, setSelected] = useState('')
  const [form, setForm] = useState(initialForm)
  const [analyzed, setAnalyzed] = useState(null) // { result, postings } for the request that produced it
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [apiUp, setApiUp] = useState(null)
  const [theme, setTheme] = useState(readTheme)
  const [retry, setRetry] = useState(0)

  const parsed = useMemo(() => parsePostings(form.postingsText), [form.postingsText])

  // Theme: follow the OS unless the viewer picked one.
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme
    else delete document.documentElement.dataset.theme
  }, [theme])
  const toggleTheme = () => {
    const isDark = theme ? theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
    const next = isDark ? 'light' : 'dark'
    setTheme(next)
    try {
      localStorage.setItem('collapsecast-theme', next)
    } catch {
      /* storage unavailable: the choice just won't persist */
    }
  }

  // Load sample companies once (and again on retry) and start from a mid-risk one.
  useEffect(() => {
    let cancelled = false
    fetchSamples()
      .then((list) => {
        if (cancelled) return
        setSamples(list)
        setApiUp(true)
        setError(null)
        const start = list[Math.min(4, list.length - 1)]
        if (start) {
          setForm(formFromSample(start))
          setSelected(start.name)
        }
      })
      .catch((e) => {
        if (cancelled) return
        setApiUp(false)
        setError(e.message)
      })
    return () => {
      cancelled = true
    }
  }, [retry])

  // Live analysis: re-run shortly after the inputs settle. The previous result stays on screen
  // (dimmed) meanwhile, so the layout never jumps.
  useEffect(() => {
    if (parsed.error) return undefined
    const controller = new AbortController()
    const postings = parsed.values
    const timer = setTimeout(() => {
      setLoading(true)
      predict(toPayload(form, postings), controller.signal)
        .then((result) => {
          setAnalyzed({ result, postings })
          setApiUp(true)
          setError(null)
        })
        .catch((e) => {
          if (e.name === 'AbortError') return
          setError(e.message)
          if (e.message.startsWith('Cannot reach')) setApiUp(false)
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false)
        })
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [form, parsed])

  const pick = useCallback(
    (name) => {
      const sample = samples.find((s) => s.name === name)
      if (!sample) return
      setForm(formFromSample(sample))
      setSelected(name)
    },
    [samples],
  )

  const edit = (patch) => {
    setForm((prev) => ({ ...prev, ...patch }))
    setSelected('')
  }
  const onValue = (field, raw) => {
    const n = parseFloat(raw)
    if (Number.isNaN(n)) return
    const clamped = Math.min(field.max, Math.max(field.min, n))
    setForm((prev) => ({ ...prev, values: { ...prev.values, [field.key]: clamped } }))
    setSelected('')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 32 32">
              <path d="M7 10h4v14H7zM14 10h4v10h-4zM21 10h4v6h-4z" fill="#fff" />
            </svg>
          </div>
          <div>
            <h1>CollapseCast</h1>
            <p>Early warning for company collapse, 3 to 6 months ahead</p>
          </div>
        </div>
        <div className="topbar-actions">
          <span className="pill" title={API_BASE}>
            <span className={`dot ${apiUp === true ? 'ok' : apiUp === false ? 'bad' : ''}`} />
            {apiUp === true ? 'API connected' : apiUp === false ? 'API unreachable' : 'Connecting'}
          </span>
          <button type="button" className="btn" onClick={toggleTheme}>
            Theme
          </button>
        </div>
      </header>

      {error && (
        <div className="banner" role="alert">
          <span style={{ flex: 1 }}>{error}</span>
          {apiUp === false && (
            <button type="button" className="btn" onClick={() => setRetry((n) => n + 1)}>
              Retry
            </button>
          )}
        </div>
      )}

      <div className="layout">
        <SignalForm
          samples={samples}
          selected={selected}
          form={form}
          postings={parsed.values}
          postingsError={parsed.error}
          onPick={pick}
          onName={(name) => edit({ name })}
          onValue={onValue}
          onPostings={(postingsText) => edit({ postingsText })}
        />

        <main className="stack">
          {analyzed ? (
            <div className={`stack results${loading ? ' stale' : ''}`} aria-busy={loading}>
              <BandHero result={analyzed.result} />
              <PipelineStages result={analyzed.result} />
              <Suspense fallback={<section className="card"><p className="secondary">Loading charts…</p></section>}>
                <div className="charts">
                  <ImpactChart result={analyzed.result} />
                  <PostingsChart result={analyzed.result} postings={analyzed.postings} />
                </div>
              </Suspense>
              <Actions result={analyzed.result} />
              <StageBreakdown result={analyzed.result} />
            </div>
          ) : (
            <section className="card">
              <p className="secondary">{apiUp === false ? 'Start the backend to see results.' : 'Analyzing…'}</p>
            </section>
          )}
          <p className="disclaimer">
            Demo data: the models are trained on a synthetic dataset, so scores show how the cascade works, not real-world accuracy.
          </p>
        </main>
      </div>
    </div>
  )
}
