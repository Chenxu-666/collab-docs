import { defineStore } from 'pinia'
import api from '@/api'
import { readStoredUser } from '@/utils/session'

interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  status: string
  must_change_pwd: boolean
  rejected_reason?: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('cd_token') || '',
    user: readStoredUser(),
    viewMode: 'admin' as 'admin' | 'user'
  }),
  getters: {
    isSuperAdmin: (s) => s.user?.role === 'super_admin',
    isAdmin: (s) => s.user?.role === 'admin' || s.user?.role === 'super_admin',
    isLoggedIn: (s) => !!s.token,
    isUserView(): boolean {
      return this.isAdmin && this.viewMode === 'user'
    }
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await api.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = data.user
      this.viewMode = 'admin'
      localStorage.setItem('cd_token', data.access_token)
      localStorage.setItem('cd_user', JSON.stringify(data.user))
      return data
    },
    async register(username: string, password: string, displayName: string) {
      const { data } = await api.post('/auth/register', { username, password, display_name: displayName })
      return data
    },
    logout() {
      this.token = ''
      this.user = null
      this.viewMode = 'admin'
      localStorage.removeItem('cd_token')
      localStorage.removeItem('cd_user')
    },
    switchToUserView() { this.viewMode = 'user' },
    backToAdmin() { this.viewMode = 'admin' }
  }
})
