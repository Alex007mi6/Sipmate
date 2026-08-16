import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await register(email.trim(), password, displayName.trim())
      navigate('/profile')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="stack" style={{ maxWidth: 420 }}>
      <h1 className="section-title">Join</h1>
      <form className="form panel" onSubmit={onSubmit}>
        <label>
          Name
          <input
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="nickname"
          />
        </label>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? '…' : 'Create'}
        </button>
      </form>
      <p className="count-line">
        <Link to="/login">Sign in</Link>
      </p>
    </section>
  )
}
