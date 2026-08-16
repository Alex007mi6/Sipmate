import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Redemption } from '../api/types'
import { useAuth } from '../context/AuthContext'

export function RedemptionsPage() {
  const { user, loading } = useAuth()
  const [items, setItems] = useState<Redemption[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    void api<Redemption[]>('/api/redemptions')
      .then(setItems)
      .catch((err: Error) => setError(err.message))
  }, [user])

  if (loading) return <p className="muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />

  return (
    <section className="stack">
      <h1 className="section-title">Your redemption codes</h1>
      <p className="muted">Show a pending code to staff for prototype verification.</p>
      {error ? <div className="error">{error}</div> : null}
      {items.length === 0 ? (
        <p className="empty">No redemptions yet.</p>
      ) : (
        <div className="table-like">
          {items.map((r) => (
            <div key={r.id} className="panel">
              <strong>{r.reward_name || `Reward #${r.reward_id}`}</strong>
              <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', margin: '0.4rem 0' }}>
                {r.redemption_code}
              </p>
              <p className="meta">
                {r.status} · {r.points_spent} points · {new Date(r.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
