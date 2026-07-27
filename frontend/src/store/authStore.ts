import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import apiClient from '../api/client'

interface User {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, fullName: string, password: string) => Promise<void>
  logout: () => void
  setToken: (token: string, user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const res = await apiClient.post('/auth/login', { email, password })
        const { access_token, user } = res.data
        set({ token: access_token, user, isAuthenticated: true })
      },

      register: async (email, fullName, password) => {
        await apiClient.post('/auth/register', {
          email,
          full_name: fullName,
          password,
        })
      },

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false })
      },

      setToken: (token, user) => {
        set({ token, user, isAuthenticated: true })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)
