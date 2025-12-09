<template>
  <div class="study-container">
    <n-layout>
      <n-layout-header class="header">
        <div class="header-content">
          <h1>Smart Vocab</h1>
          <n-space>
            <n-button v-if="authStore.isAdmin" text @click="goToAdmin">
              管理后台
            </n-button>
            <n-button text @click="handleLogout">
              退出登录
            </n-button>
          </n-space>
        </div>
      </n-layout-header>

      <n-layout-content class="content">
        <div v-if="studyStore.loading" class="loading-container">
          <n-spin size="large" />
          <p>加载中...</p>
        </div>

        <div v-else-if="!studyStore.session" class="empty-container">
          <n-empty description="还没有开始学习">
            <template #extra>
              <n-button type="primary" @click="startStudy">
                开始学习
              </n-button>
            </template>
          </n-empty>
        </div>

        <div v-else-if="studyStore.currentWord" class="study-content">
          <div class="progress-info">
            <n-progress
              type="line"
              :percentage="progressPercentage"
              :show-indicator="false"
            />
            <n-text depth="3">
              进度: {{ studyStore.currentIndex + 1 }} / {{ studyStore.session.total }}
            </n-text>
          </div>

          <word-card :word="studyStore.currentWord.word!" />

          <div class="rating-buttons">
            <n-space justify="center" :size="16">
              <n-button
                type="error"
                size="large"
                @click="submitRating(0)"
              >
                忘记了 (0)
              </n-button>
              <n-button
                type="warning"
                size="large"
                @click="submitRating(3)"
              >
                模糊 (3)
              </n-button>
              <n-button
                type="info"
                size="large"
                @click="submitRating(4)"
              >
                想起来了 (4)
              </n-button>
              <n-button
                type="success"
                size="large"
                @click="submitRating(5)"
              >
                很容易 (5)
              </n-button>
            </n-space>
          </div>
        </div>

        <div v-else class="complete-container">
          <n-result
            status="success"
            title="今日学习完成！"
            description="恭喜你完成了今天的学习任务"
          >
            <template #footer>
              <n-button type="primary" @click="startStudy">
                再来一轮
              </n-button>
            </template>
          </n-result>
        </div>
      </n-layout-content>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NButton,
  NSpace,
  NSpin,
  NEmpty,
  NProgress,
  NText,
  NResult,
  useMessage
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useStudyStore } from '@/stores/study'
import WordCard from '@/components/WordCard.vue'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const studyStore = useStudyStore()

const progressPercentage = computed(() => {
  if (!studyStore.session) return 0
  return Math.round(((studyStore.currentIndex + 1) / studyStore.session.total) * 100)
})

async function startStudy() {
  try {
    await studyStore.loadSession()
    if (!studyStore.session || studyStore.session.words.length === 0) {
      message.info('暂时没有需要学习的单词')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载学习会话失败')
  }
}

async function submitRating(quality: 0 | 3 | 4 | 5) {
  try {
    await studyStore.submitReview(quality)
    if (!studyStore.currentWord) {
      message.success('今日学习完成！')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交失败')
  }
}

function goToAdmin() {
  router.push('/admin')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  startStudy()
})
</script>

<style scoped>
.study-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  background: white;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  height: 64px;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.content {
  padding: 40px 24px;
}

.loading-container,
.empty-container,
.complete-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.loading-container p {
  margin-top: 16px;
  color: #666;
}

.study-content {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.progress-info {
  width: 100%;
  max-width: 600px;
}

.progress-info .n-text {
  display: block;
  text-align: center;
  margin-top: 8px;
}

.rating-buttons {
  width: 100%;
  max-width: 600px;
}
</style>
