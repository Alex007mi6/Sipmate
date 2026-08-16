import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Badge, Redemption } from '../api/types'
import { BackChevron } from '../components/BackChevron'
import { useAuth } from '../context/AuthContext'

type Profile = {
  user: { display_name: string; email: string }
  points_balance: number
  badges: Badge[]
}

export function ProfilePage() {
  const { user, loading } = useAuth()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [badges, setBadges] = useState<Badge[]>([])
  const [redemptions, setRedemptions] = useState<Redemption[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    void Promise.all([
      api<Profile>('/api/profile'),
      api<Badge[]>('/api/profile/badges'),
      api<Redemption[]>('/api/redemptions'),
    ])
      .then(([p, b, r]) => {
        setProfile(p)
        setBadges(b.length ? b : p.badges)
        setRedemptions(r.slice(0, 5))
      })
      .catch((err: Error) => setError(err.message))
  }, [user])

  if (loading) return <p className="muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />

  return (
    <section className="stack">
      <div className="page-head">
        <Link className="back-link" to="/drinks" aria-label="Back to drinks">
          <BackChevron />
        </Link>
        <h1 className="section-title">{profile?.user.display_name || user.display_name}</h1>
      </div>
      {error ? <div className="error">{error}</div> : null}

      <div className="panel" style={{ textAlign: 'center' }}>
        <p
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '3rem',
            margin: 0,
            lineHeight: 1,
            fontWeight: 700,
          }}
        >
          {profile?.points_balance ?? '—'}
        </p>
        <p className="count-line">points</p>
      </div>

      <h2 style={{ margin: '0.25rem 0 0', fontSize: '1.1rem' }}>Badges</h2>
      {badges.length === 0 ? (
        <p className="empty">None yet.</p>
      ) : (
        <div className="badge-grid">
          {badges.map((b) => (
            <div key={b.id} className="panel">
              <strong>{b.name}</strong>
            </div>
          ))}
        </div>
      )}

      {redemptions.length > 0 ? (
        <>
          <h2 style={{ margin: '0.25rem 0 0', fontSize: '1.1rem' }}>Codes</h2>
          <div className="table-like">
            {redemptions.map((r) => (
              <div key={r.id} className="panel">
                <strong>{r.redemption_code}</strong>
                <p className="meta">
                  {r.status} · {r.points_spent} pts
                </p>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="cta-row">
        <Link className="btn btn-primary" to="/drinks">
          Start
        </Link>
        <Link className="btn btn-secondary" to="/rewards">
          Rewards
        </Link>
      </div>
    </section>
  )
}
