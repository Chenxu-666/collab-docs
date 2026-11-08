import axios from 'axios'
import router from '@/router'

const apiBaseURL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const api = axios.create({ baseURL: `${apiBaseURL}/api/v1`, timeout: 30000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cd_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    let msg = err.response?.data?.detail || err.message || '请求失败'
    if (!err.response) {
      msg = err.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '网络连接失败，请检查网络'
    } else if (status === 401) {
      localStorage.removeItem('cd_token')
      localStorage.removeItem('cd_user')
      const onAdmin = (router.currentRoute.value.path || '').startsWith('/admin')
      if (onAdmin) router.push('/login')
      msg = '登录已过期，请重新登录'
    }
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  }
)

export default api
