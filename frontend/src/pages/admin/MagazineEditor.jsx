import { useEffect, useMemo, useState } from 'react'
import AppShell from '../../components/AppShell'
import { api } from '../../api/client'

export default function AdminMagazineEditor() {
  const [magazines, setMagazines] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})

  function load() {
    api
      .adminListMagazines()
      .then(setMagazines)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [])

  const filtered = useMemo(() => {
    if (!magazines) return null
    const q = filter.trim().toLowerCase()
    if (!q) return magazines
    return magazines.filter(
      (m) => m.title.toLowerCase().includes(q) || m.collection.toLowerCase().includes(q)
    )
  }, [magazines, filter])

  function startEdit(m) {
    setEditingId(m.id)
    setEditForm({ title: m.title, groupID: m.groupID, userID: m.userID || '' })
  }

  async function saveEdit(id) {
    setError('')
    try {
      const payload = { ...editForm, userID: editForm.userID || null }
      await api.adminUpdateMagazine(id, payload)
      setEditingId(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <AppShell title="Magazine Properties">
      {error && <div className="form-error">{error}</div>}

      <input
        className="text-input search-input"
        placeholder="Filter by title or collection…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Collection</th>
              <th>Title</th>
              <th>Group</th>
              <th>Owner override (userID)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered?.map((m) => (
              <tr key={m.id}>
                <td>{m.collection}</td>
                {editingId === m.id ? (
                  <>
                    <td>
                      <input
                        className="text-input text-input-compact"
                        value={editForm.title}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="text-input text-input-compact"
                        value={editForm.groupID}
                        onChange={(e) => setEditForm({ ...editForm, groupID: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="text-input text-input-compact"
                        placeholder="(none)"
                        value={editForm.userID}
                        onChange={(e) => setEditForm({ ...editForm, userID: e.target.value })}
                      />
                    </td>
                    <td className="actions-cell">
                      <button className="button-secondary" onClick={() => saveEdit(m.id)}>
                        Save
                      </button>
                      <button className="button-text-link" onClick={() => setEditingId(null)}>
                        Cancel
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{m.title}</td>
                    <td>
                      <span className="badge-pill">{m.groupID}</span>
                    </td>
                    <td>{m.userID || <span className="muted">—</span>}</td>
                    <td className="actions-cell">
                      <button className="button-text-link" onClick={() => startEdit(m)}>
                        Edit
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
