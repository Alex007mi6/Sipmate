import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { api } from '../api/client'
import type { Product, Reward } from '../api/types'
import { useAuth } from '../context/AuthContext'

type ModelStatus = {
  loaded: boolean
  n_products?: number | null
  active_version_id?: number | null
  active_version_status?: string | null
  stale?: boolean
  product_count?: number | null
  created_at?: string | null
  activated_at?: string | null
}

type ModelRebuild = {
  ok: boolean
  version_id: number
  product_count: number
  message?: string | null
}

function AdminHome() {
  return (
    <div className="panel">
      <p>Manage products, rewards, redemptions, and the recommendation model.</p>
    </div>
  )
}

function AdminProducts() {
  const [items, setItems] = useState<Product[]>([])
  const [q, setQ] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const params = new URLSearchParams({ limit: '50' })
    if (q.trim()) params.set('q', q.trim())
    const data = await api<{ items: Product[] }>(`/api/admin/products?${params}`)
    setItems(data.items)
  }

  useEffect(() => {
    void load().catch((err: Error) => setError(err.message))
  }, [])

  async function deactivate(id: number) {
    setError(null)
    try {
      await api(`/api/admin/products/${id}`, { method: 'DELETE' })
      setMessage(`Product ${id} deactivated`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  async function saveAbv(id: number, abv: number) {
    setError(null)
    try {
      await api(`/api/admin/products/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ abv }),
      })
      setMessage(`Updated ABV for product ${id}`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  return (
    <div className="stack">
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault()
          void load().catch((err: Error) => setError(err.message))
        }}
      >
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" />
        <button className="btn btn-secondary" type="submit">
          Search
        </button>
      </form>
      {message ? <div className="success">{message}</div> : null}
      {error ? <div className="error">{error}</div> : null}
      <div className="table-like">
        {items.map((p) => (
          <div key={p.id} className="panel stack">
            <strong>
              #{p.id} {p.full_name}
            </strong>
            <p className="meta">
              {p.abv}% ABV · serving {p.serving_ml ?? '—'} ml · active={String(p.is_active)}
            </p>
            <div className="cta-row">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  const next = window.prompt('New ABV', String(p.abv))
                  if (next) void saveAbv(p.id, Number(next))
                }}
              >
                Edit ABV
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => void deactivate(p.id)}>
                Deactivate
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AdminRewards() {
  const [items, setItems] = useState<Reward[]>([])
  const [name, setName] = useState('')
  const [cost, setCost] = useState(40)
  const [stock, setStock] = useState(10)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setItems(await api<Reward[]>('/api/admin/rewards'))
  }

  useEffect(() => {
    void load().catch((err: Error) => setError(err.message))
  }, [])

  async function create(e: FormEvent) {
    e.preventDefault()
    try {
      await api('/api/admin/rewards', {
        method: 'POST',
        body: JSON.stringify({
          name,
          description: name,
          points_cost: cost,
          stock,
          active: true,
        }),
      })
      setName('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    }
  }

  return (
    <div className="stack">
      {error ? <div className="error">{error}</div> : null}
      <form className="form panel" onSubmit={create}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Points cost
          <input
            type="number"
            value={cost}
            onChange={(e) => setCost(Number(e.target.value))}
            min={1}
          />
        </label>
        <label>
          Stock
          <input
            type="number"
            value={stock}
            onChange={(e) => setStock(Number(e.target.value))}
            min={0}
          />
        </label>
        <button className="btn btn-primary" type="submit">
          Add reward
        </button>
      </form>
      <div className="table-like">
        {items.map((r) => (
          <div key={r.id} className="panel">
            <strong>
              #{r.id} {r.name}
            </strong>
            <p className="meta">
              {r.points_cost} pts · stock {r.stock} · active={String(r.active)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function AdminRedemptions() {
  const [code, setCode] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function confirm(e: FormEvent) {
    e.preventDefault()
    setMessage(null)
    setError(null)
    try {
      const result = await api<{ redemption_code: string; status: string }>(
        `/api/admin/redemptions/${encodeURIComponent(code.trim())}/confirm`,
        { method: 'POST' },
      )
      setMessage(`Code ${result.redemption_code} → ${result.status}`)
      setCode('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Confirm failed')
    }
  }

  return (
    <form className="form panel" onSubmit={confirm}>
      <label>
        Redemption code
        <input value={code} onChange={(e) => setCode(e.target.value)} required />
      </label>
      <button className="btn btn-primary" type="submit">
        Mark redeemed
      </button>
      {message ? <div className="success">{message}</div> : null}
      {error ? <div className="error">{error}</div> : null}
    </form>
  )
}

function AdminModel() {
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    setStatus(await api<ModelStatus>('/api/admin/model/status'))
  }

  useEffect(() => {
    void load().catch((err: Error) => setError(err.message))
  }, [])

  async function rebuild() {
    setBusy(true)
    setError(null)
    try {
      const result = await api<ModelRebuild>('/api/admin/model/rebuild', { method: 'POST' })
      setMessage(result.message || `Model rebuilt (version ${result.version_id})`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rebuild failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      {status ? (
        <div className="panel">
          <p>
            Status:{' '}
            <strong>
              {status.active_version_status || (status.loaded ? 'loaded' : 'missing')}
              {status.stale ? ' (stale)' : ''}
            </strong>
          </p>
          <p className="meta">
            Model products: {status.n_products ?? status.product_count ?? '—'}
          </p>
          <p className="meta">Active version id: {status.active_version_id ?? '—'}</p>
        </div>
      ) : null}
      <button className="btn btn-primary" type="button" disabled={busy} onClick={() => void rebuild()}>
        {busy ? 'Rebuilding…' : 'Rebuild Recommendation Model'}
      </button>
      {message ? <div className="success">{message}</div> : null}
      {error ? <div className="error">{error}</div> : null}
    </div>
  )
}

export function AdminPage() {
  const { user, loading } = useAuth()
  if (loading) return <p className="muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') {
    return <div className="error">Admin access required.</div>
  }

  return (
    <section className="stack">
      <h1 className="section-title">Admin</h1>
      <nav className="admin-nav">
        <NavLink className="btn btn-secondary" to="/admin" end>
          Overview
        </NavLink>
        <NavLink className="btn btn-secondary" to="/admin/products">
          Products
        </NavLink>
        <NavLink className="btn btn-secondary" to="/admin/rewards">
          Rewards
        </NavLink>
        <NavLink className="btn btn-secondary" to="/admin/redemptions">
          Redemptions
        </NavLink>
        <NavLink className="btn btn-secondary" to="/admin/model">
          Model
        </NavLink>
      </nav>
      <Routes>
        <Route index element={<AdminHome />} />
        <Route path="products" element={<AdminProducts />} />
        <Route path="rewards" element={<AdminRewards />} />
        <Route path="redemptions" element={<AdminRedemptions />} />
        <Route path="model" element={<AdminModel />} />
      </Routes>
      <Link className="btn btn-secondary" to="/">
        Back to app
      </Link>
    </section>
  )
}
