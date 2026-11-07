import { useEffect, useState } from 'react'
import { requestJson } from '../api/client'

interface Resource<T> {
  path: string | null
  data: T | null
  loading: boolean
  error: string | null
}

/** A small effect replaces a server-rendered page's initial data-loading step. */
export function useApiRead<T>(path: string | null) {
  const [resource, setResource] = useState<Resource<T>>({ path: null, data: null, loading: true, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!path) {
      setResource({ path, data: null, loading: false, error: null })
      return
    }
    const controller = new AbortController()
    let active = true
    setResource({ path, data: null, loading: true, error: null })
    requestJson<T>(path, { signal: controller.signal }).then(
      (data) => { if (active) setResource({ path, data, loading: false, error: null }) },
      (error: unknown) => {
        if (active) setResource({ path, data: null, loading: false, error: error instanceof Error ? error.message : 'Request failed.' })
      },
    )
    // Cleanup runs before changed filters trigger a new request, and on unmount.
    // Abort saves work; active also protects us if a transport ignores cancellation.
    return () => { active = false; controller.abort() }
  }, [path, attempt])

  // Effects run after rendering. Hide the old window even in the first render
  // after filters change, before the new effect has had a chance to clear it.
  const current = resource.path === path ? resource : { data: null, loading: !!path, error: null }
  return { ...current, retry: () => setAttempt((value) => value + 1) }
}
