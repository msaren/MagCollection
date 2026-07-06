import { useState } from 'react'
import AppShell from '../../components/AppShell'
import { useAuth } from '../../auth/AuthContext'

export default function UISettings() {
  const { user, setTheme } = useAuth()
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const isDark = user?.theme === 'dark'

  // Persisted via the user record (see AuthContext.setTheme), not localStorage,
  // so the choice follows the account across devices/browsers.
  async function handleToggle() {
    setError('')
    setSaving(true)
    try {
      await setTheme(isDark ? 'light' : 'dark')
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppShell title="UI Settings">
      {error && <div className="form-error">{error}</div>}

      <section className="admin-section">
        <h2>Appearance</h2>
        <div className="setting-row">
          <div>
            <div className="setting-label">Light mode / Dark mode</div>
            <div className="setting-description">
              Switches the interface theme. Saved to your account and applied on every device.
            </div>
          </div>
          <button
            className={`toggle-switch${isDark ? ' toggle-switch-on' : ''}`}
            role="switch"
            aria-checked={isDark}
            aria-label="Toggle dark mode"
            onClick={handleToggle}
            disabled={saving}
          >
            <span className="toggle-knob" />
          </button>
        </div>
      </section>
    </AppShell>
  )
}
