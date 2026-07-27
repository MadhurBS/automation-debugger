import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  // Do NOT set a global Content-Type — JSON requests set it explicitly,
  // multipart requests must let the browser add the boundary automatically.
})

// Inject JWT token + handle FormData Content-Type
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // If body is FormData, delete any Content-Type header so the browser
  // sets "multipart/form-data; boundary=..." automatically.
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  } else if (!config.headers['Content-Type']) {
    // Default to JSON for everything else
    config.headers['Content-Type'] = 'application/json'
  }

  return config
})

// Handle 401
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
