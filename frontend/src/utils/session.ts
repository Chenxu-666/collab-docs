export interface StoredUser {
  id: number
  username: string
  display_name: string
  role: string
  status: string
  must_change_pwd: boolean
  rejected_reason?: string
}

export function readStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem('cd_user')
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') return parsed as StoredUser
    return null
  } catch {
    return null
  }
}

export function clearSession(): void {
  localStorage.removeItem('cd_token')
  localStorage.removeItem('cd_user')
}
