import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          SipMate
        </NavLink>
        <nav className="nav-links" aria-label="Main">
          <NavLink to="/drinks">Drinks</NavLink>
          <NavLink to="/rewards">Rewards</NavLink>
          {user ? (
            <>
              <NavLink to="/profile">Me</NavLink>
              {user.role === 'admin' ? <NavLink to="/admin">Admin</NavLink> : null}
              <button type="button" className="linkish" onClick={() => void logout()}>
                Logout
              </button>
            </>
          ) : (
            <NavLink to="/login">Login</NavLink>
          )}
        </nav>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  )
}
