import { useEffect, useRef, useState } from 'react'
import AppShell from '../../components/AppShell'
import { api } from '../../api/client'

export default function AdminScanner() {
  const [collections, setCollections] = useState(null)
  const [error, setError] = useState('')
  const [scanning, setScanning] = useState(false)
  const [rescanning, setRescanning] = useState(false)
  const [progress, setProgress] = useState(null)
  const [lastResult, setLastResult] = useState(null)
  const [editingName, setEditingName] = useState(null)
  const [groupValue, setGroupValue] = useState('')
  const pollRef = useRef(null)

  function load() {
    api
      .adminListCollections()
      .then(setCollections)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [])

  // Picks up a rescan already in progress (e.g. kicked off from another tab) so the
  // progress indicator shows up on load instead of only after clicking the button here.
  useEffect(() => {
    api
      .adminRescanCoversStatus()
      .then((status) => {
        if (status.running) {
          setRescanning(true)
          setProgress(status)
          pollRescanStatus()
        }
      })
      .catch(() => {})
    return () => clearTimeout(pollRef.current)
  }, [])

  function pollRescanStatus() {
    pollRef.current = setTimeout(async () => {
      try {
        const status = await api.adminRescanCoversStatus()
        setProgress(status)
        if (status.running) {
          pollRescanStatus()
          return
        }
        if (status.error) {
          setError(status.error)
        } else if (status.result) {
          setLastResult(status.result)
        }
        setRescanning(false)
        setProgress(null)
        load()
      } catch (e) {
        setError(e.message)
        setRescanning(false)
        setProgress(null)
      }
    }, 500)
  }

  // The same scan the backend also runs automatically on startup; exposed here so
  // admins can pick up filesystem changes (new issues copied in, etc.) without restarting.
  async function handleScan() {
    setScanning(true)
    setError('')
    try {
      const result = await api.adminScan()
      setLastResult(result)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setScanning(false)
    }
  }

  async function handleRescanCovers() {
    if (!window.confirm('This wipes and re-renders every thumbnail, and removes collections/files no longer on disk. It can take a while for large libraries. Continue?')) {
      return
    }
    setRescanning(true)
    setProgress({ running: true, current: 0, total: 0, currentFile: null })
    setError('')
    try {
      await api.adminRescanCovers()
      pollRescanStatus()
    } catch (e) {
      setError(e.message)
      setRescanning(false)
      setProgress(null)
    }
  }

  async function handleRescanCollectionCovers(name) {
    if (!window.confirm(`Wipe and re-render every thumbnail in "${name}"? This can take a while for large collections.`)) {
      return
    }
    setRescanning(true)
    setProgress({ running: true, current: 0, total: 0, currentFile: null, collection: name })
    setError('')
    try {
      await api.adminRescanCollectionCovers(name)
      pollRescanStatus()
    } catch (e) {
      setError(e.message)
      setRescanning(false)
      setProgress(null)
    }
  }

  function startEditGroup(c) {
    setEditingName(c.name)
    setGroupValue(c.groupID)
  }

  async function saveGroup(name) {
    setError('')
    try {
      await api.adminUpdateCollection(name, { groupID: groupValue })
      setEditingName(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <AppShell title="Collection Scanner">
      {error && <div className="form-error">{error}</div>}

      <section className="admin-section">
        <p>
          Scan the <code>collections/</code> directory on disk and sync new, updated, or removed magazine files
          into the database. New collections default to the <span className="badge-pill">public</span> group.
        </p>
        <button className="button-primary" onClick={handleScan} disabled={scanning || rescanning}>
          {scanning ? 'Scanning…' : 'Scan now'}
        </button>{' '}
        <button className="button-secondary" onClick={handleRescanCovers} disabled={scanning || rescanning}>
          {rescanning ? 'Rescanning covers…' : 'Rescan covers'}
        </button>
        <p className="muted">
          "Rescan covers" also removes collections/files that are no longer on disk and regenerates
          every thumbnail from scratch — use it after bulk-removing files or if covers look stale.
        </p>
        {progress && (
          <div className="scan-progress">
            <div className="scan-progress-bar">
              <div
                className="scan-progress-bar-fill"
                style={{ width: progress.total ? `${(100 * progress.current) / progress.total}%` : '2%' }}
              />
            </div>
            <div className="scan-progress-label">
              {progress.total
                ? `Regenerating thumbnails${progress.collection ? ` for "${progress.collection}"` : ''}: ${progress.current} / ${progress.total}`
                : 'Syncing collections…'}
              {progress.currentFile && <span className="scan-progress-file"> — {progress.currentFile}</span>}
            </div>
          </div>
        )}
        {lastResult && (
          <div className="scan-result">
            Added {lastResult.added}, updated {lastResult.updated}, removed {lastResult.removed}
            {typeof lastResult.removedCollections === 'number' && lastResult.removedCollections > 0 &&
              `, removed ${lastResult.removedCollections} collection(s)`}
            {typeof lastResult.thumbnailsRegenerated === 'number' &&
              `, regenerated ${lastResult.thumbnailsRegenerated} thumbnail(s)`}
            {typeof lastResult.thumbnailsFailed === 'number' && lastResult.thumbnailsFailed > 0 &&
              ` (${lastResult.thumbnailsFailed} failed)`}
            {' '}— {lastResult.collections} collection(s) total.
          </div>
        )}
      </section>

      <section className="admin-section">
        <h2>Collections &amp; default access group</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Collection</th>
                <th>Issues</th>
                <th>Default group</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {collections?.map((c) => (
                <tr key={c.name}>
                  <td>{c.name}</td>
                  <td>{c.magazineCount}</td>
                  <td>
                    {editingName === c.name ? (
                      <input
                        className="text-input text-input-compact"
                        value={groupValue}
                        onChange={(e) => setGroupValue(e.target.value)}
                      />
                    ) : (
                      <span className="badge-pill">{c.groupID}</span>
                    )}
                  </td>
                  <td className="actions-cell">
                    {editingName === c.name ? (
                      <>
                        <button className="button-secondary" onClick={() => saveGroup(c.name)}>
                          Save
                        </button>
                        <button className="button-text-link" onClick={() => setEditingName(null)}>
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button className="button-text-link" onClick={() => startEditGroup(c)}>
                          Edit
                        </button>{' '}
                        <button
                          className="button-text-link"
                          onClick={() => handleRescanCollectionCovers(c.name)}
                          disabled={scanning || rescanning}
                        >
                          {rescanning && progress?.collection === c.name ? 'Rescanning…' : 'Rescan covers'}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  )
}
