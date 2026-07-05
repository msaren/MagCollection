import { Fragment, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import AuthImage from '../components/AuthImage'
import { api } from '../api/client'
import { openMagazineFile } from '../utils/openMagazine'

function encodePath(path) {
  return path
    .split('/')
    .map(encodeURIComponent)
    .join('/')
}

export default function CollectionView() {
  const { name, '*': splat } = useParams()
  const path = (splat || '').replace(/\/$/, '')
  const segments = path ? path.split('/') : []

  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [openingId, setOpeningId] = useState(null)

  useEffect(() => {
    setData(null)
    setError('')
    api
      .collectionBrowse(name, path)
      .then(setData)
      .catch((e) => setError(e.message))
  }, [name, path])

  async function handleOpen(magazineId) {
    setOpeningId(magazineId)
    try {
      await openMagazineFile(magazineId)
    } catch (e) {
      setError(e.message)
    } finally {
      setOpeningId(null)
    }
  }

  const folders = data?.folders ?? []
  const magazines = data?.magazines ?? []
  const isEmpty = data && folders.length === 0 && magazines.length === 0

  return (
    <AppShell title={name}>
      <nav className="breadcrumbs">
        <Link to="/" className="breadcrumb-link">
          All collections
        </Link>
        <span className="breadcrumb-sep">/</span>
        {segments.length === 0 ? (
          <span className="breadcrumb-current">{name}</span>
        ) : (
          <Link to={`/collections/${encodeURIComponent(name)}`} className="breadcrumb-link">
            {name}
          </Link>
        )}
        {segments.map((seg, i) => {
          const isLast = i === segments.length - 1
          const href = `/collections/${encodeURIComponent(name)}/${encodePath(segments.slice(0, i + 1).join('/'))}`
          return (
            <Fragment key={href}>
              <span className="breadcrumb-sep">/</span>
              {isLast ? (
                <span className="breadcrumb-current">{seg}</span>
              ) : (
                <Link to={href} className="breadcrumb-link">
                  {seg}
                </Link>
              )}
            </Fragment>
          )
        })}
      </nav>

      {error && <div className="form-error">{error}</div>}
      {!data && !error && <div className="page-loading">Loading…</div>}
      {isEmpty && <div className="empty-state">This folder is empty.</div>}

      {folders.length > 0 && (
        <div className="grid grid-folders">
          {folders.map((f) => (
            <Link
              key={f.path}
              to={`/collections/${encodeURIComponent(name)}/${encodePath(f.path)}`}
              className="folder-card"
            >
              <div className="folder-icon">📁</div>
              <div className="folder-name">{f.name}</div>
              <div className="folder-count">
                {f.magazineCount} {f.magazineCount === 1 ? 'issue' : 'issues'}
              </div>
            </Link>
          ))}
        </div>
      )}

      {magazines.length > 0 && (
        <div className="grid grid-magazines">
          {magazines.map((m) => (
            <button
              key={m.id}
              className="magazine-card"
              onClick={() => handleOpen(m.id)}
              disabled={openingId === m.id}
            >
              <AuthImage path={`/magazines/${m.id}/thumbnail`} alt={m.title} className="magazine-thumb" />
              <div className="magazine-title">{openingId === m.id ? 'Opening…' : m.title}</div>
            </button>
          ))}
        </div>
      )}
    </AppShell>
  )
}
