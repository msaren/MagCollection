import { useEffect, useState } from 'react'
import AppShell from '../../components/AppShell'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

const emptyForm = { username: '', password: '', email: '', groupID: '', role: 'user' }

export default function AdminUsers() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})

  function load() {
    api
      .adminListUsers()
      .then(setUsers)
      .catch((e) => setError(e.message))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    try {
      await api.adminCreateUser(form)
      setForm(emptyForm)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  function startEdit(u) {
    setEditingId(u.id)
    setEditForm({ username: u.username, email: u.email, groupID: u.groupID, role: u.role, password: '' })
  }

  async function handleSaveEdit(id) {
    setError('')
    try {
      // Leave password out of the payload entirely when the field was left blank,
      // so the backend's partial-update semantics keep the existing password.
      const payload = { ...editForm }
      if (!payload.password) delete payload.password
      await api.adminUpdateUser(id, payload)
      setEditingId(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this user?')) return
    setError('')
    try {
      await api.adminDeleteUser(id)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <AppShell title="User Management">
      {error && <div className="form-error">{error}</div>}

      <section className="admin-section">
        <h2>Existing users</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Group</th>
                <th>Role</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {/* Rows toggle between a read-only view and an inline edit form for the one
                  row being edited, rather than routing to a separate edit page. */}
              {users?.map((u) => (
                <tr key={u.id}>
                  {editingId === u.id ? (
                    <>
                      <td>
                        <input
                          className="text-input text-input-compact"
                          value={editForm.username}
                          onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                        />
                      </td>
                      <td>
                        <input
                          className="text-input text-input-compact"
                          value={editForm.email}
                          onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
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
                        <select
                          className="text-input text-input-compact"
                          value={editForm.role}
                          onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                        >
                          <option value="user">user</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td className="actions-cell">
                        <input
                          className="text-input text-input-compact"
                          placeholder="New password (optional)"
                          type="password"
                          value={editForm.password}
                          onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                        />
                        <button className="button-secondary" onClick={() => handleSaveEdit(u.id)}>
                          Save
                        </button>
                        <button className="button-text-link" onClick={() => setEditingId(null)}>
                          Cancel
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{u.username}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className="badge-pill">{u.groupID}</span>
                      </td>
                      <td>{u.role}</td>
                      <td className="actions-cell">
                        <button className="button-text-link" onClick={() => startEdit(u)}>
                          Edit
                        </button>
                        {/* Mirrors the backend's own guard against self-deletion, which
                            would otherwise lock the signed-in admin out. */}
                        <button
                          className="button-text-link button-danger"
                          onClick={() => handleDelete(u.id)}
                          disabled={u.id === currentUser?.id}
                        >
                          Delete
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-section">
        <h2>Add user</h2>
        <form className="inline-form" onSubmit={handleCreate}>
          <input
            className="text-input"
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <input
            className="text-input"
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          <input
            className="text-input"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <input
            className="text-input"
            placeholder="Group ID"
            value={form.groupID}
            onChange={(e) => setForm({ ...form, groupID: e.target.value })}
            required
          />
          <select
            className="text-input"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button type="submit" className="button-primary">
            Add user
          </button>
        </form>
      </section>
    </AppShell>
  )
}
