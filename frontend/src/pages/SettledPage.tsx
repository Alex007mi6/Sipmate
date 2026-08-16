import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Product } from '../api/types'
import { clearLadderStack } from '../lib/ladderStack'

type SettledState = {
  originProductId?: number
  pointsEarned?: number
}

function alcoholReductionPct(origin: Product, current: Product): number | null {
  const a = origin.alcohol_grams ?? origin.alcohol_ml
  const b = current.alcohol_grams ?? current.alcohol_ml
  if (a == null || b == null || a <= 0) return null
  return ((a - b) / a) * 100
}

export function SettledPage() {
  const { productId } = useParams()
  const location = useLocation()
  const state = (location.state as SettledState | null) ?? null
  const [product, setProduct] = useState<Product | null>(null)
  const [origin, setOrigin] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const pointsEarned = state?.pointsEarned ?? 0
  const originId = state?.originProductId ?? Number(productId)

  useEffect(() => {
    if (!productId) return
    const id = Number(productId)
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const current = await api<Product>(`/api/products/${id}`)
        setProduct(current)
        if (originId && originId !== id) {
          const orig = await api<Product>(`/api/products/${originId}`)
          setOrigin(orig)
        } else {
          setOrigin(current)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed')
      } finally {
        setLoading(false)
      }
    })()
  }, [productId, originId])

  if (loading) return <p className="muted">Loading…</p>
  if (error) return <div className="error" role="alert">{error}</div>
  if (!product) return null

  const baseline = origin ?? product
  const reduction = alcoholReductionPct(baseline, product)

  return (
    <section className="stack">
      <h1 className="section-title">Your pick</h1>

      <div className="panel settle-card">
        <p className="settle-eyebrow">Settled</p>
        <h2 className="settle-name">{product.name}</h2>
        <p className="meta">
          {product.brand} · {product.abv.toFixed(1)}% ·{' '}
          {product.alcohol_grams != null ? `${product.alcohol_grams.toFixed(0)} g / glass` : '—'}
        </p>

        <div className="metric-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <div className="metric">
            <strong>
              {reduction == null ? '—' : reduction > 0 ? `↓${reduction.toFixed(0)}%` : '0%'}
            </strong>
            <span>Less alcohol</span>
          </div>
          <div className="metric">
            <strong>{pointsEarned > 0 ? `+${pointsEarned}` : '0'}</strong>
            <span>Points</span>
          </div>
        </div>

        <div className="cta-row" style={{ flexDirection: 'column' }}>
          <Link className="btn btn-primary btn-block" to="/rewards">
            Rewards
          </Link>
          <Link
            className="btn btn-secondary btn-block"
            to="/drinks"
            onClick={() => clearLadderStack()}
          >
            New drink
          </Link>
        </div>
      </div>
    </section>
  )
}
