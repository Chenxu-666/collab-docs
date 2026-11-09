import axios, { AxiosInstance } from 'axios'
import router from '@/router'
import { clearSession } from '@/utils/session'

const apiBaseURL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

function createClient(timeout: number): AxiosInstance {
  return axios.create({ baseURL: `${apiBaseURL}/api/v1`, timeout })
}

// 管理端/受保护请求：自动附带登录态，处理 401 会话过期。
const api = createClient(30000)

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cd_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const status = err.response?.status
    const isLogin = (err.config?.url || '').endsWith('/auth/login')
    let msg = err.response?.data?.detail || err.message || '请求失败'
    if (!err.response) {
      msg = err.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '网络连接失败，请检查网络'
    } else if (status === 401 && !isLogin) {
      clearSession()
      try {
        const { useUserStore } = await import('@/stores/user')
        useUserStore().$patch({ token: '', user: null })
      } catch { /* store 尚未初始化时忽略 */ }
      const path = router.currentRoute.value.path || ''
      const onAdmin = path.startsWith('/admin') || path === '/login'
      if (onAdmin) router.push({ name: 'login', query: { redirect: path } })
      msg = '登录已过期，请重新登录'
    }
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  }
)

// 公开只读请求：不附带 Authorization，避免管理员身份让公开页看到草稿。
const publicApi = createClient(15000)

export { api as default, publicApi }
