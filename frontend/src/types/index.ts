export interface User {
  id: number
  email: string
  username: string
  role: 'user' | 'admin'
  subscription_tier: 'free' | 'premium' | 'enterprise'
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Definition {
  pos: string
  cn: string
  en: string
}

export interface Sentence {
  en: string
  cn: string
}

export interface Word {
  id: number
  word: string
  phonetic?: string
  definitions: Definition[]
  sentences: Sentence[]
  mnemonic?: string
  tags?: string[]
}

export interface UserProgress {
  id: number
  word_id: number
  user_id: number
  status: 0 | 1 | 2 | 3
  next_review_at: string
  ease_factor: number
  interval: number
  repetitions: number
  history: ReviewHistory[]
  word?: Word
}

export interface ReviewHistory {
  timestamp: string
  quality: number
  interval: number
}

export interface StudySession {
  words: UserProgress[]
  total: number
  new_count: number
  review_count: number
}

export interface SubmitReviewRequest {
  word_id: number
  quality: 0 | 3 | 4 | 5
}

export interface Book {
  id: number
  title: string
  file_url: string
  status: 'processing' | 'ready' | 'failed'
  total_pages?: number
  total_words?: number
  created_at: string
  updated_at: string
}

export interface UploadTaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  message?: string
  book_id?: number
}
