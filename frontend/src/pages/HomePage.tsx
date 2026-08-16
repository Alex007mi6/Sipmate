import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <section className="hero">
      <p className="hero-brand">SipMate</p>
      <h2>Lighter drinks. Same taste vibe.</h2>
      <div className="cta-row">
        <Link className="btn btn-primary" to="/drinks">
          Start
        </Link>
      </div>
    </section>
  )
}
