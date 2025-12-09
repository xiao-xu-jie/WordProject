import apiClient from './axios'
import type { StudySession, SubmitReviewRequest } from '@/types'

export const studyApi = {
  getSession() {
    return apiClient.get<StudySession>('/study/session')
  },

  submitReview(data: SubmitReviewRequest) {
    return apiClient.post('/study/submit', data)
  },

  getProgress() {
    return apiClient.get('/study/progress')
  },

  getStatistics() {
    return apiClient.get('/study/statistics')
  }
}
