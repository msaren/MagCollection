import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ePub from 'epubjs'
import { api } from '../api/client'

// Full-screen EPUB viewer using epub.js, since browsers have no native EPUB
// renderer the way they do for PDF (which just opens in a plain browser tab).
export default function EpubReader() {
  const { magazineId } = useParams()
  const navigate = useNavigate()
  const { state } = useLocation()

  const viewerRef = useRef(null)
  const bookRef = useRef(null)
  const renditionRef = useRef(null)

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    let cancelled = false

    // Also stamps last_read server-side (see main.py get_magazine_file).
    api
      .fetchBlob(`/magazines/${magazineId}/file`)
      .then((blob) => blob.arrayBuffer())
      .then((buffer) => {
        if (cancelled) return
        const book = ePub(buffer)
        bookRef.current = book
        const rendition = book.renderTo(viewerRef.current, {
          width: '100%',
          height: '100%',
          spread: 'auto',
        })
        renditionRef.current = rendition

        // location.start.percentage is epub.js's fraction through the whole book,
        // independent of how many "pages" the current viewport happens to fit.
        rendition.on('relocated', (location) => {
          setProgress(location.start.percentage)
        })

        return rendition.display().then(() => {
          if (!cancelled) setLoading(false)
        })
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || 'Could not open this EPUB file')
          setLoading(false)
        }
      })

    return () => {
      // Guards the async chain above against setting state after unmount (e.g. the
      // user hits Back before the file finishes downloading), and tears down epub.js's
      // own DOM/iframe resources so they don't leak across magazineId changes.
      cancelled = true
      renditionRef.current?.destroy()
      bookRef.current?.destroy()
    }
  }, [magazineId])

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'ArrowLeft') renditionRef.current?.prev()
      if (e.key === 'ArrowRight') renditionRef.current?.next()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  return (
    <div className="reader-shell">
      <header className="reader-topbar">
        <button className="button-secondary reader-back" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <div className="reader-title">{state?.title || 'Reader'}</div>
        <div className="reader-progress">{Math.round(progress * 100)}%</div>
      </header>

      <div className="reader-body">
        {error && <div className="form-error reader-error">{error}</div>}
        {loading && !error && <div className="page-loading">Loading…</div>}
        <div ref={viewerRef} className="reader-viewer" />
        {!loading && !error && (
          <>
            <button
              className="reader-nav reader-nav-prev"
              aria-label="Previous page"
              onClick={() => renditionRef.current?.prev()}
            >
              ‹
            </button>
            <button
              className="reader-nav reader-nav-next"
              aria-label="Next page"
              onClick={() => renditionRef.current?.next()}
            >
              ›
            </button>
          </>
        )}
      </div>
    </div>
  )
}
