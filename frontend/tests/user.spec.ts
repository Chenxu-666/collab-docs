import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import api from '@/api'

describe('user store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('初始未登录状态：无 token、未登录', () => {
    const store = useUserStore()
    expect(store.isLoggedIn).toBe(false)
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
  })

  it('从 localStorage 恢复登录态', () => {
    localStorage.setItem('cd_token', 'persisted-token')
    localStorage.setItem('cd_user', JSON.stringify({ id: 1, username: '001', role: 'super_admin', display_name: '陈总', status: 'active', must_change_pwd: false }))
    setActivePinia(createPinia())
    const store = useUserStore()
    expect(store.isLoggedIn).toBe(true)
    expect(store.token).toBe('persisted-token')
    expect(store.isSuperAdmin).toBe(true)
  })

  it('isAdmin 识别 admin 与 super_admin；普通用户不是', () => {
    localStorage.setItem('cd_user', JSON.stringify({ id: 2, username: '002', role: 'admin', display_name: '管理员', status: 'active', must_change_pwd: false }))
    setActivePinia(createPinia())
    const store = useUserStore()
    expect(store.isAdmin).toBe(true)
    expect(store.isSuperAdmin).toBe(false)
  })

  it('login 成功后保存 token 与用户信息', async () => {
    const store = useUserStore()
    const spy = vi.spyOn(api, 'post').mockResolvedValue({
      data: { access_token: 'tok-123', user: { id: 1, username: '001', role: 'super_admin', display_name: '陈总', status: 'active', must_change_pwd: false } }
    })
    const data = await store.login('001', 'pw')
    expect(data.access_token).toBe('tok-123')
    expect(store.token).toBe('tok-123')
    expect(store.isSuperAdmin).toBe(true)
    expect(localStorage.getItem('cd_token')).toBe('tok-123')
    spy.mockRestore()
  })

  it('logout 清空 token、用户与本地存储', () => {
    localStorage.setItem('cd_token', 'tok')
    localStorage.setItem('cd_user', JSON.stringify({ id: 1, username: '001', role: 'super_admin', display_name: '陈总', status: 'active', must_change_pwd: false }))
    setActivePinia(createPinia())
    const store = useUserStore()
    store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(localStorage.getItem('cd_token')).toBeNull()
    expect(localStorage.getItem('cd_user')).toBeNull()
  })

  it('视图切换：管理员视角与用户视角', () => {
    localStorage.setItem('cd_user', JSON.stringify({ id: 2, username: '002', role: 'admin', display_name: '管理员', status: 'active', must_change_pwd: false }))
    setActivePinia(createPinia())
    const store = useUserStore()
    expect(store.isUserView).toBe(false)
    store.switchToUserView()
    expect(store.viewMode).toBe('user')
    expect(store.isUserView).toBe(true)
    store.backToAdmin()
    expect(store.isUserView).toBe(false)
  })
})
