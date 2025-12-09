import apiClient from './axios'
import type { LoginRequest, RegisterRequest, AuthResponse } from '@/types'

export const authApi = {
  login(data: LoginRequest) {
    return apiClient.post<AuthResponse>('/auth/login', data)
  },

  register(data: RegisterRequest) {
    return apiClient.post<AuthResponse>('/auth/register', data)
  },

  getCurrentUser() {
    return apiClient.get('/auth/me')
  }
}
