import { defineStore } from 'pinia'
import { ref } from 'vue'
import { studyApi } from '@/api/study'
import type { StudySession, UserProgress, SubmitReviewRequest } from '@/types'

export const useStudyStore = defineStore('study', () => {
  const session = ref<StudySession | null>(null)
  const currentIndex = ref(0)
  const loading = ref(false)

  const currentWord = ref<UserProgress | null>(null)

  async function loadSession() {
    loading.value = true
    try {
      const response = await studyApi.getSession()
      session.value = response.data
      currentIndex.value = 0
      if (session.value.words.length > 0) {
        currentWord.value = session.value.words[0]
      }
    } finally {
      loading.value = false
    }
  }

  async function submitReview(quality: 0 | 3 | 4 | 5) {
    if (!currentWord.value) return

    const data: SubmitReviewRequest = {
      word_id: currentWord.value.word_id,
      quality
    }

    await studyApi.submitReview(data)

    currentIndex.value++
    if (session.value && currentIndex.value < session.value.words.length) {
      currentWord.value = session.value.words[currentIndex.value]
    } else {
      currentWord.value = null
    }
  }

  function reset() {
    session.value = null
    currentIndex.value = 0
    currentWord.value = null
  }

  return {
    session,
    currentIndex,
    currentWord,
    loading,
    loadSession,
    submitReview,
    reset
  }
})
