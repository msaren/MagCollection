import { api } from '../api/client'

export async function openMagazineFile(magazineId) {
  const blob = await api.fetchBlob(`/magazines/${magazineId}/file`)
  const url = URL.createObjectURL(blob)
  // No noopener/noreferrer: blob: URLs are scoped to the renderer process
  // that created them, so the new tab must stay in the same browsing
  // context group or it won't be able to resolve the blob.
  window.open(url, '_blank')
  // Revoke after a delay long enough for the new tab to load the blob.
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
