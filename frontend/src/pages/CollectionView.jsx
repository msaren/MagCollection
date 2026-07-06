import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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

// last_read is stored as a Unix epoch (seconds) or null if never opened.
// Rendered in the viewer's local time zone, format DD-MM-YYYY HH:MM.
function formatLastRead(epochSeconds) {
  if (!epochSeconds) return 'Never'
  const d = new Date(epochSeconds * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function CollectionView() {
  const { name, '*': splat } = useParams()
  const navigate = useNavigate()
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

  // Only PDFs use the browser's native tab-open path; EPUB and comic archives need
  // an in-app reader since browsers can't render those formats on their own.
  async function handleOpen(magazine) {
    if (magazine.filetype === 'epub') {
      navigate(`/reader/${magazine.id}`, { state: { title: magazine.title } })
      return
    }
    if (['cbz', 'cbr', 'zip'].includes(magazine.filetype)) {
      navigate(`/comic/${magazine.id}`, { state: { title: magazine.title } })
      return
    }
    setOpeningId(magazine.id)
    try {
      await openMagazineFile(magazine.id)
      // The reader routes remount this page on "back" and pick up the new last-read
      // time automatically; opening a PDF stays on this page, so refetch explicitly.
      const fresh = await api.collectionBrowse(name, path)
      setData(fresh)
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
        {/* One breadcrumb link per path segment, each linking to that ancestor subdirectory. */}
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
              onClick={() => handleOpen(m)}
              disabled={openingId === m.id}
            >
              <AuthImage path={`/magazines/${m.id}/thumbnail`} alt={m.title} className="magazine-thumb" />
              <div className="magazine-title">{openingId === m.id ? 'Opening…' : m.title}</div>
              <div className="magazine-last-read">Last read: {formatLastRead(m.lastRead)}</div>
            </button>
          ))}
        </div>
      )}
    </AppShell>
  )
}
