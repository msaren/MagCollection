import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function AuthImage({ path, alt, className }) {
  const [src, setSrc] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl
    let cancelled = false
    setFailed(false)
    setSrc(null)

    api
      .fetchBlob(path)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [path])

  if (failed) {
    return <div className={`${className} thumb-placeholder`}>No preview</div>
  }
  if (!src) {
    return <div className={`${className} thumb-placeholder thumb-loading`} />
  }
  return <img src={src} alt={alt} className={className} />
}
