const AUDIENCES = ['Employees', 'Investors', 'HR']

export default function Actions({ result }) {
  return (
    <section className="card" aria-label="Recommended actions">
      <div className="card-head">
        <h2 className="card-title">Recommended actions</h2>
        <span className="card-sub">For the {result.band} band</span>
      </div>
      <div className="actions">
        {AUDIENCES.map((who) => (
          <div key={who}>
            <h3>{who}</h3>
            <ul>
              {(result.recommended_actions[who] || []).map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}
