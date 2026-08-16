import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Product } from '../api/types'
import { BackChevron } from '../components/BackChevron'
import { clearLadderStack } from '../lib/ladderStack'

type ListResponse = {
  items: Product[]
  total: number
  limit: number
  offset: number
}

export function DrinksPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [categories, setCategories] = useState<string[]>([])
  const [items, setItems] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void api<string[]>('/api/products/categories')
      .then(setCategories)
      .catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      const params = new URLSearchParams({
        limit: '30',
        recommendable_only: 'true',
      })
      if (q.trim()) params.set('q', q.trim())
      if (category) params.set('category', category)
      void api<ListResponse>(`/api/products?${params}`)
        .then((data) => {
          setItems(data.items)
          setTotal(data.total)
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [q, category])

  return (
    <section className="stack">
      <div className="page-head">
        <Link className="back-link" to="/" aria-label="Back to home">
          <BackChevron />
        </Link>
        <h1 className="section-title">Pick a drink</h1>
      </div>

      <div className="search-bar">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search"
          aria-label="Search drinks"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All styles</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {error ? <div className="error" role="alert">{error}</div> : null}
      {loading ? <p className="muted">Loading…</p> : null}

      {!loading && items.length === 0 ? (
        <p className="empty">No matches.</p>
      ) : (
        <div className="drink-list" role="list">
          {items.map((p) => (
            <button
              key={p.id}
              type="button"
              className="drink-row"
              role="listitem"
              onClick={() => {
                clearLadderStack()
                navigate(`/recommend/${p.id}`)
              }}
            >
              <strong>{p.name}</strong>
              <span className="meta">{p.brand}</span>
              <span className="abv-pill" aria-label={`${p.abv.toFixed(1)} percent ABV`}>
                {p.abv.toFixed(1)}
                <small>ABV</small>
              </span>
            </button>
          ))}
        </div>
      )}

      {!loading ? <p className="count-line">{total} drinks</p> : null}
    </section>
  )
}
