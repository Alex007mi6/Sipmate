import type { ApiError } from './types'

const API_BASE = ''

function sessionId(): string {
  const key = 'sipmate_session_id'
  let id = sessionStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem(key, id)
  }
  return id
}

export function getSessionId(): string {
  return sessionId()
}

export class ApiRequestError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (!res.ok) {
    let code = 'HTTP_ERROR'
    let message = res.statusText || 'Request failed'
    try {
      const data = (await res.json()) as ApiError
      if (data?.error?.message) {
        message = data.error.message
        code = data.error.code || code
      }
    } catch {
      /* ignore */
    }
    throw new ApiRequestError(res.status, code, message)
  }

  if (res.status === 204) {
    return undefined as T
  }
  return (await res.json()) as T
}
