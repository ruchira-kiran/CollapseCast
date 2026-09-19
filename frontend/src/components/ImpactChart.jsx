import { Bar, BarChart, CartesianGrid, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard from './ChartCard.jsx'
import { points, signed } from '../format.js'

const ROW = 30
const AXIS_BAND = 34

// Short axis labels so a row never wraps; the tooltip and table carry the full names.
const SHORT_LABELS = {
  hiring_freeze_score: 'Hiring freeze',
  exec_departure_rate: 'Exec departures',
  news_negativity: 'Negative news',
  review_sentiment: 'Review sentiment',
  engagement_signals: 'Engagement',
  client_churn: 'Client churn',
  delays: 'Delays',
  weekly_job_postings: 'Job postings',
}

// Value at the bar tip: right of a positive bar, left of a negative one.
function TipLabel({ x, y, width, height, value }) {
  const tip = value >= 0 ? Math.max(x, x + width) : Math.min(x, x + width)
  return (
    <text
      x={value >= 0 ? tip + 6 : tip - 6}
      y={y + height / 2}
      dy="0.35em"
      textAnchor={value >= 0 ? 'start' : 'end'}
      fill="var(--text-secondary)"
      fontSize={12}
    >
      {signed(value)}
    </text>
  )
}

function ImpactTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="tooltip">
      <b>{row.label}</b>
      <div className="secondary">{row.detail}</div>
      <div>
        Contribution: <b>{signed(row.value)}</b> points
      </div>
    </div>
  )
}

export default function ImpactChart({ result }) {
  const { signal_impact: impacts, baseline_failure_score: baseline } = result.breakdown
  const rows = impacts.map((i) => ({
    label: i.label,
    short: SHORT_LABELS[i.signal] ?? i.label,
    detail: i.detail,
    value: i.impact * 100,
  }))
  const failure = points(result.scores.failure_raw)

  return (
    <ChartCard
      title="What drove the score"
      subtitle="Each signal's share of the failure score, in points"
      note={`A healthy company scores about ${points(baseline)}. The contributions below add up from there to this company's ${failure}.`}
      chart={
        <div role="img" aria-label="Bar chart of each signal's contribution to the failure score. The table view has the same values.">
          <ResponsiveContainer width="100%" height={rows.length * ROW + AXIS_BAND}>
            <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 44, bottom: 4, left: 4 }} barCategoryGap={6}>
              <CartesianGrid horizontal={false} stroke="var(--grid)" />
              <XAxis
                type="number"
                // Leave room left of zero for a negative bar's value label, and right of the longest bar.
                domain={[(min) => (min < 0 ? min - 3.5 : 0), (max) => Math.max(5, max) * 1.15]}
                tickLine={false}
                axisLine={{ stroke: 'var(--axis)' }}
                tick={{ fill: 'var(--text-muted)', fontSize: 11.5 }}
                tickFormatter={(v) => Math.round(v)}
              />
              <YAxis
                type="category"
                dataKey="short"
                width={112}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--text-secondary)', fontSize: 12.5 }}
              />
              <ReferenceLine x={0} stroke="var(--axis)" />
              <Tooltip content={<ImpactTooltip />} cursor={{ fill: 'var(--grid)', opacity: 0.5 }} />
              {/* minPointSize keeps a zero-valued row visible so its "0.0" label still renders. */}
              <Bar dataKey="value" fill="var(--series-1)" radius={[0, 4, 4, 0]} barSize={16} minPointSize={2} isAnimationActive={false}>
                <LabelList dataKey="value" content={<TipLabel />} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      }
      table={
        <table className="data">
          <thead>
            <tr>
              <th>Signal</th>
              <th>State</th>
              <th className="n">Points</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <td>{r.label}</td>
                <td className="secondary">{r.detail}</td>
                <td className="n">{signed(r.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    />
  )
}
