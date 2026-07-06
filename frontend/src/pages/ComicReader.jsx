import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'

// Full-screen page-by-page viewer for comic archives (CBZ/CBR/ZIP). Unlike the EPUB
// reader, there's no client-side library doing the parsing: the backend extracts one
// image per request, so this just fetches pages one at a time as the user navigates.
export default function ComicReader() {
  const { magazineId } = useParams()
  const navigate = useNavigate()
  const { state } = useLocation()

  const [pageCount, setPageCount] = useState(0)
  const [pageIndex, setPageIndex] = useState(0)
  const [src, setSrc] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  // Fetching the page count is also what stamps last_read server-side (see
  // main.py get_magazine_pages) - it only needs to happen once per magazine, not
  // once per page turn, which is why it's split out from the page-image effect below.
  useEffect(() => {
    let cancelled = false
    api
      .comicPages(magazineId)
      .then(({ pageCount }) => {
        if (cancelled) return
        setPageCount(pageCount)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Could not open this comic archive')
      })
    return () => {
      cancelled = true
    }
  }, [magazineId])

  // Re-fetches the current page's image whenever pageIndex changes (or pageCount
  // arrives). Each page is its own request/object URL - no client-side caching of
  // pages the user has already seen.
  useEffect(() => {
    if (pageCount === 0) return
    let cancelled = false
    let objectUrl
    setLoading(true)

    api
      .fetchBlob(`/magazines/${magazineId}/pages/${pageIndex}`)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
        setLoading(false)
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || 'Could not load this page')
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [magazineId, pageIndex, pageCount])

  function goPrev() {
    setPageIndex((i) => Math.max(0, i - 1))
  }

  function goNext() {
    setPageIndex((i) => Math.min(pageCount - 1, i + 1))
  }

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'ArrowLeft') goPrev()
      if (e.key === 'ArrowRight') goNext()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [pageCount])

  return (
    <div className="reader-shell">
      <header className="reader-topbar">
        <button className="button-secondary reader-back" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <div className="reader-title">{state?.title || 'Reader'}</div>
        <div className="reader-progress">
          {pageCount > 0 ? `${pageIndex + 1} / ${pageCount}` : ''}
        </div>
      </header>

      <div className="reader-body">
        {error && <div className="form-error reader-error">{error}</div>}
        {loading && !error && <div className="page-loading">Loading…</div>}
        {src && !error && <img src={src} alt={`Page ${pageIndex + 1}`} className="comic-page-img" />}
        {!loading && !error && (
          <>
            <button
              className="reader-nav reader-nav-prev"
              aria-label="Previous page"
              onClick={goPrev}
              disabled={pageIndex === 0}
            >
              ‹
            </button>
            <button
              className="reader-nav reader-nav-next"
              aria-label="Next page"
              onClick={goNext}
              disabled={pageIndex === pageCount - 1}
            >
              ›
            </button>
          </>
        )}
      </div>
    </div>
  )
}
