import apiClient from './axios'
import type { Book, UploadTaskStatus } from '@/types'

export const adminApi = {
  uploadPDF(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<{ task_id: string }>('/admin/upload-pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  getTaskStatus(taskId: string) {
    return apiClient.get<UploadTaskStatus>(`/admin/task/${taskId}/status`)
  },

  getBooks() {
    return apiClient.get<Book[]>('/admin/books')
  },

  deleteBook(bookId: number) {
    return apiClient.delete(`/admin/books/${bookId}`)
  }
}
