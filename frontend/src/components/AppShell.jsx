import { useState } from 'react'
import Sidebar from './Sidebar'

// Common page chrome (sidebar + topbar) shared by every authenticated page except
// the full-screen EPUB/comic readers, which render outside this shell entirely.
export default function AppShell({ title, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-main">
        <header className="topbar">
          <button
            className="hamburger-button"
            aria-label="Toggle navigation"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>
          <h1 className="topbar-title">{title}</h1>
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  )
}
