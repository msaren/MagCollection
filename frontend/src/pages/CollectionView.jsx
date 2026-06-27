import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import AuthImage from '../components/AuthImage'
import { api } from '../api/client'
import { openMagazineFile } from '../utils/openMagazine'

export default function CollectionView() {
  const { name } = useParams()
  const [magazines, setMagazines] = useState(null)
  const [error, setError] = useState('')
  const [openingId, setOpeningId] = useState(null)

  useEffect(() => {
    setMagazines(null)
    setError('')
    api
      .collectionMagazines(name)
      .then(setMagazines)
      .catch((e) => setError(e.message))
  }, [name])

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

  return (
    <AppShell title={name}>
      <Link to="/" className="back-link">
        &larr; All collections
      </Link>

      {error && <div className="form-error">{error}</div>}
      {!magazines && !error && <div className="page-loading">Loading magazines…</div>}
      {magazines && magazines.length === 0 && <div className="empty-state">No issues in this collection.</div>}

      <div className="grid grid-magazines">
        {magazines?.map((m) => (
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
    </AppShell>
  )
}
