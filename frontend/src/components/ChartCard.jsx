import { useState } from 'react'

/** Card with a Chart / Table toggle: every chart has a table twin, so no value is tooltip-only. */
export default function ChartCard({ title, subtitle, chart, table, note }) {
  const [view, setView] = useState('chart')
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2 className="card-title" style={{ marginBottom: 2 }}>{title}</h2>
          {subtitle && <div className="card-sub">{subtitle}</div>}
        </div>
        <div className="seg" role="group" aria-label={`${title} view`}>
          <button type="button" aria-pressed={view === 'chart'} onClick={() => setView('chart')}>Chart</button>
          <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}>Table</button>
        </div>
      </div>
      {view === 'chart' ? chart : <div className="table-scroll">{table}</div>}
      {note && <p className="chart-note">{note}</p>}
    </section>
  )
}
