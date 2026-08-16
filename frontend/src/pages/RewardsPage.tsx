import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Redemption, Reward } from '../api/types'
import { BackChevron } from '../components/BackChevron'
import { useAuth } from '../context/AuthContext'

export function RewardsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [rewards, setRewards] = useState<Reward[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  useEffect(() => {
    void api<{ items: Reward[] }>('/api/rewards')
      .then((data) => setRewards(data.items))
      .catch((err: Error) => setError(err.message))
  }, [])

  async function redeem(id: number) {
    if (!user) {
      navigate('/login')
      return
    }
    setBusyId(id)
    setError(null)
    setMessage(null)
    try {
      const result = await api<{ redemption: Redemption; points_balance: number }>(
        `/api/rewards/${id}/redeem`,
        { method: 'POST' },
      )
      setMessage(`${result.redemption.redemption_code} · ${result.points_balance} pts left`)
      setRewards((prev) =>
        prev.map((r) => (r.id === id ? { ...r, stock: Math.max(0, r.stock - 1) } : r)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="stack">
      <div className="page-head">
        <Link className="back-link" to="/drinks" aria-label="Back to drinks">
          <BackChevron />
        </Link>
        <h1 className="section-title">Rewards</h1>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {message ? <div className="success">{message}</div> : null}

      <div className="reward-grid">
        {rewards.map((r) => (
          <article key={r.id} className="panel stack">
            <strong>{r.name}</strong>
            <p className="meta">
              {r.points_cost} pts · x{r.stock}
            </p>
            <button
              type="button"
              className="btn btn-primary btn-block"
              disabled={r.stock <= 0 || busyId === r.id}
              onClick={() => void redeem(r.id)}
            >
              {!user ? 'Sign in' : busyId === r.id ? '…' : 'Redeem'}
            </button>
          </article>
        ))}
      </div>

      {user ? (
        <Link className="btn btn-secondary btn-block" to="/redemptions">
          Codes
        </Link>
      ) : null}
    </section>
  )
}
