import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api } from '../api/client'

export default function Collections() {
  const [collections, setCollections] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .collections()
      .then(setCollections)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <AppShell title="Collections">
      {error && <div className="form-error">{error}</div>}
      {!collections && !error && <div className="page-loading">Loading collections…</div>}

      {collections && collections.length === 0 && (
        <div className="empty-state">No collections are available to your account yet.</div>
      )}

      <div className="grid grid-collections">
        {collections?.map((c) => (
          <Link to={`/collections/${encodeURIComponent(c.name)}`} key={c.name} className="collection-card">
            {/* The API also returns c.icon (settable via the admin collections editor),
                but there's no icon picker UI yet, so this always shows the initial letter. */}
            <div className="collection-icon">{c.name.charAt(0).toUpperCase()}</div>
            <div className="collection-name">{c.name}</div>
            <div className="collection-count">
              {c.magazineCount} {c.magazineCount === 1 ? 'issue' : 'issues'}
            </div>
          </Link>
        ))}
      </div>
    </AppShell>
  )
}
