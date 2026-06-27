import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Sidebar({ open, onClose }) {
  const { user, isAdmin, logout } = useAuth()

  const linkClass = ({ isActive }) => `sidebar-link${isActive ? ' sidebar-link-active' : ''}`

  return (
    <>
      {open && <div className="sidebar-scrim" onClick={onClose} />}
      <aside className={`sidebar${open ? ' sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">&#10022;</span>
          <span>MagCollector</span>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Browse</div>
          <NavLink to="/" className={linkClass} onClick={onClose} end>
            Collections
          </NavLink>

          <div className="sidebar-section-label">Settings</div>
          <NavLink to="/settings/ui" className={linkClass} onClick={onClose}>
            UI Settings
          </NavLink>

          {isAdmin && (
            <>
              <div className="sidebar-section-label">Administration</div>
              <NavLink to="/admin/users" className={linkClass} onClick={onClose}>
                User Management
              </NavLink>
              <NavLink to="/admin/scanner" className={linkClass} onClick={onClose}>
                Collection Scanner
              </NavLink>
              <NavLink to="/admin/magazines" className={linkClass} onClick={onClose}>
                Magazine Properties
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-user-name">{user?.username}</div>
            <div className="sidebar-user-group">{user?.groupID}</div>
          </div>
          <button className="button-text-link" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
    </>
  )
}
