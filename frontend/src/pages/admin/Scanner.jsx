import { useEffect, useState } from 'react'
import AppShell from '../../components/AppShell'
import { api } from '../../api/client'

export default function AdminScanner() {
  const [collections, setCollections] = useState(null)
  const [error, setError] = useState('')
  const [scanning, setScanning] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [editingName, setEditingName] = useState(null)
  const [groupValue, setGroupValue] = useState('')

  function load() {
    api
      .adminListCollections()
      .then(setCollections)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [])

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
        <button className="button-primary" onClick={handleScan} disabled={scanning}>
          {scanning ? 'Scanning…' : 'Scan now'}
        </button>
        {lastResult && (
          <div className="scan-result">
            Added {lastResult.added}, updated {lastResult.updated}, removed {lastResult.removed} — {' '}
            {lastResult.collections} collection(s) total.
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
                      <button className="button-text-link" onClick={() => startEditGroup(c)}>
                        Edit
                      </button>
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
