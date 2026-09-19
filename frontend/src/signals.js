// Input definitions. Ranges mirror the backend's validation (backend/app/schemas.py).
export const FIELDS = [
  { key: 'hiring_freeze_score', label: 'Hiring freeze', min: 0, max: 1, hint: '0 hiring normally, 1 complete freeze' },
  { key: 'exec_departure_rate', label: 'Executive departures', min: 0, max: 1, hint: 'Share of senior execs who left in 12 months' },
  { key: 'news_negativity', label: 'Negative news', min: 0, max: 1, hint: '0 neutral or positive, 1 uniformly negative' },
  { key: 'review_sentiment', label: 'Employee review sentiment', min: -1, max: 1, hint: '-1 very negative, +1 very positive' },
  { key: 'engagement_signals', label: 'Engagement', min: 0, max: 1, hint: '1 healthy, 0 disengaged' },
  { key: 'client_churn', label: 'Client churn', min: 0, max: 1, hint: 'Share of clients lost in the last 6 months' },
  { key: 'delays', label: 'Delivery / payment delays', min: 0, max: 1, hint: '0 none, 1 severe' },
]

export const MIN_WEEKS = 12
export const MAX_WEEKS = 104

export const DEFAULT_VALUES = Object.fromEntries(FIELDS.map((f) => [f.key, f.key === 'review_sentiment' ? 0.3 : 0.2]))
export const DEFAULT_POSTINGS = [40, 42, 39, 41, 43, 40, 42, 41, 40, 39, 41, 40, 42, 41, 40, 41]

export const postingsToText = (series) => series.join(', ')

/** Parse "40, 42 39\n41" into whole numbers; returns { values, error }. */
export function parsePostings(text) {
  const tokens = text.split(/[\s,;]+/).filter(Boolean)
  const values = tokens.map(Number)
  if (values.some((v) => !Number.isFinite(v) || v < 0 || !Number.isInteger(v))) {
    return { values: [], error: 'Use whole, non-negative numbers separated by commas.' }
  }
  if (values.length < MIN_WEEKS || values.length > MAX_WEEKS) {
    return { values, error: `Enter ${MIN_WEEKS}-${MAX_WEEKS} weekly counts (you have ${values.length}).` }
  }
  return { values, error: null }
}

export const toPayload = (form, postings) => ({
  name: form.name || null,
  ...form.values,
  weekly_job_postings: postings,
})
