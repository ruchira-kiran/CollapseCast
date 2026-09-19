import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard from './ChartCard.jsx'

function PostingsTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { week, postings } = payload[0].payload
  return (
    <div className="tooltip">
      <b>Week {week}</b>
      <div>
        <b>{postings}</b> open postings
      </div>
    </div>
  )
}

export default function PostingsChart({ result, postings }) {
  const demand = result.breakdown.stages[1]
  const detail = demand.detail
  const data = postings.map((count, i) => ({ week: i + 1, postings: count }))
  const last = data.length - 1
  // Round the top up to a multiple of 20 so the four intervals are clean numbers (e.g. 0/15/30/45/60).
  const top = Math.max(20, Math.ceil((Math.max(...postings) * 1.1) / 20) * 20)
  const yTicks = [0, top / 4, top / 2, (3 * top) / 4, top]

  // Only the final point gets a marker (value at the end of the line), ringed in the surface color.
  const endDot = ({ cx, cy, index }) =>
    index === last ? (
      <circle key="end" cx={cx} cy={cy} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
    ) : (
      <g key={index} />
    )

  const note = detail.change_detected
    ? `CUSUM flags a sustained decline from week ${detail.change_week}: postings fell ${Math.round(detail.drop_fraction * 100)}% from a baseline of ${detail.baseline_weekly_postings}/week to ${detail.recent_weekly_postings}/week.`
    : `No statistically supported decline against the first-8-week baseline of ${detail.baseline_weekly_postings}/week.`

  return (
    <ChartCard
      title="Job-posting demand"
      subtitle="Open postings per week, with the change-point test"
      note={note}
      chart={
        <div role="img" aria-label={`Line chart of weekly job postings. ${note}`}>
          <ResponsiveContainer width="100%" height={242}>
            <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--grid)" />
              <XAxis
                dataKey="week"
                tickLine={false}
                axisLine={{ stroke: 'var(--axis)' }}
                tick={{ fill: 'var(--text-muted)', fontSize: 11.5 }}
                tickFormatter={(w) => `w${w}`}
                minTickGap={16}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={36}
                domain={[0, top]}
                ticks={yTicks}
                tick={{ fill: 'var(--text-muted)', fontSize: 11.5 }}
              />
              <ReferenceLine
                y={detail.baseline_weekly_postings}
                stroke="var(--axis)"
                label={{ value: `Baseline ${detail.baseline_weekly_postings}`, position: 'insideTopRight', fill: 'var(--text-secondary)', fontSize: 11.5 }}
              />
              {detail.change_detected && (
                <ReferenceLine
                  x={detail.change_week}
                  stroke="var(--text-muted)"
                  label={{ value: `Decline starts w${detail.change_week}`, position: 'insideTopRight', fill: 'var(--text-secondary)', fontSize: 11.5 }}
                />
              )}
              <Tooltip content={<PostingsTooltip />} cursor={{ stroke: 'var(--text-muted)' }} />
              <Line
                type="linear"
                dataKey="postings"
                stroke="var(--series-1)"
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                dot={endDot}
                activeDot={{ r: 5, fill: 'var(--series-1)', stroke: 'var(--surface)', strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      }
      table={
        <table className="data">
          <thead>
            <tr>
              <th>Week</th>
              <th className="n">Open postings</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.week}>
                <td>{d.week}</td>
                <td className="n">{d.postings}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    />
  )
}
