import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest, RegisterRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(credentials: LoginRequest) {
    const response = await authApi.login(credentials)
    token.value = response.data.access_token
    user.value = response.data.user
    localStorage.setItem('token', response.data.access_token)
  }

  async function register(data: RegisterRequest) {
    const response = await authApi.register(data)
    token.value = response.data.access_token
    user.value = response.data.user
    localStorage.setItem('token', response.data.access_token)
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const response = await authApi.getCurrentUser()
      user.value = response.data
    } catch (error) {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    login,
    register,
    fetchUser,
    logout
  }
})
