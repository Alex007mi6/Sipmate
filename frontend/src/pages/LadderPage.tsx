import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { LadderStep, Product } from '../api/types'
import { BackChevron } from '../components/BackChevron'

type LadderResponse = {
  selected: Product
  steps: LadderStep[]
}

export function LadderPage() {
  const { productId } = useParams()
  const [steps, setSteps] = useState<LadderStep[]>([])
  const [selected, setSelected] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!productId) return
    setLoading(true)
    void api<LadderResponse>('/api/recommendations/ladder', {
      method: 'POST',
      body: JSON.stringify({ product_id: Number(productId), max_steps: 5 }),
    })
      .then((data) => {
        setSelected(data.selected)
        setSteps(data.steps)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [productId])

  if (loading) return <p className="muted">Loading…</p>
  if (error) return <div className="error">{error}</div>

  return (
    <section className="stack">
      <div className="page-head">
        <Link
          className="back-link"
          to={selected ? `/recommend/${selected.id}` : '/drinks'}
          aria-label="Back"
        >
          <BackChevron />
        </Link>
        <h1 className="section-title">Ladder</h1>
      </div>

      <div className="ladder">
        {steps.map((step, idx) => (
          <div key={`${step.product_key}-${step.step}`}>
            <div
              className={`ladder-step ${step.step === 0 ? 'current' : ''}`}
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div>
                <span className="chip">{step.step === 0 ? 'Now' : `Step ${step.step}`}</span>
                <h2 style={{ margin: '0.3rem 0 0', fontSize: '1.05rem' }}>{step.name}</h2>
              </div>
              <span className="abv-pill" aria-label={`${step.abv.toFixed(1)} percent ABV`}>
                {step.abv.toFixed(1)}
                <small>ABV</small>
              </span>
            </div>
            {idx < steps.length - 1 ? (
              <div className="ladder-arrow" aria-hidden>
                ↓
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
