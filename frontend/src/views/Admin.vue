<template>
  <div class="admin-container">
    <n-layout>
      <n-layout-header class="header">
        <div class="header-content">
          <h1>管理后台</h1>
          <n-space>
            <n-button text @click="goToStudy">
              返回学习
            </n-button>
            <n-button text @click="handleLogout">
              退出登录
            </n-button>
          </n-space>
        </div>
      </n-layout-header>

      <n-layout-content class="content">
        <n-space vertical :size="24">
          <n-card title="上传 PDF 文档">
            <n-space vertical :size="16">
              <n-upload
                :custom-request="handleUpload"
                :max="1"
                accept=".pdf"
                :show-file-list="false"
              >
                <n-button :loading="uploading">
                  选择 PDF 文件
                </n-button>
              </n-upload>

              <div v-if="currentTask" class="task-status">
                <n-alert
                  :type="taskStatusType"
                  :title="taskStatusTitle"
                >
                  <template v-if="currentTask.status === 'processing'">
                    <n-progress
                      type="line"
                      :percentage="currentTask.progress || 0"
                      :show-indicator="true"
                    />
                    <p style="margin-top: 8px">{{ currentTask.message || '处理中...' }}</p>
                  </template>
                  <template v-else>
                    <p>{{ currentTask.message || getDefaultMessage(currentTask.status) }}</p>
                  </template>
                </n-alert>
              </div>
            </n-space>
          </n-card>

          <n-card title="已上传的书籍">
            <n-data-table
              :columns="columns"
              :data="books"
              :loading="loadingBooks"
              :pagination="pagination"
            />
          </n-card>
        </n-space>
      </n-layout-content>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NButton,
  NSpace,
  NCard,
  NUpload,
  NAlert,
  NProgress,
  NDataTable,
  NTag,
  useMessage,
  type UploadCustomRequestOptions,
  type DataTableColumns
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { adminApi } from '@/api/admin'
import type { Book, UploadTaskStatus } from '@/types'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const uploading = ref(false)
const currentTask = ref<UploadTaskStatus | null>(null)
const books = ref<Book[]>([])
const loadingBooks = ref(false)
let pollInterval: number | null = null

const pagination = {
  pageSize: 10
}

const taskStatusType = computed(() => {
  if (!currentTask.value) return 'default'
  switch (currentTask.value.status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'processing':
      return 'info'
    default:
      return 'default'
  }
})

const taskStatusTitle = computed(() => {
  if (!currentTask.value) return ''
  switch (currentTask.value.status) {
    case 'completed':
      return '处理完成'
    case 'failed':
      return '处理失败'
    case 'processing':
      return '正在处理'
    default:
      return '等待处理'
  }
})

const columns: DataTableColumns<Book> = [
  {
    title: 'ID',
    key: 'id',
    width: 80
  },
  {
    title: '书名',
    key: 'title'
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render(row) {
      const statusMap = {
        processing: { type: 'info', text: '处理中' },
        ready: { type: 'success', text: '就绪' },
        failed: { type: 'error', text: '失败' }
      }
      const status = statusMap[row.status] || { type: 'default', text: row.status }
      return h(NTag, { type: status.type as any }, { default: () => status.text })
    }
  },
  {
    title: '总页数',
    key: 'total_pages',
    width: 100
  },
  {
    title: '总词数',
    key: 'total_words',
    width: 100
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString('zh-CN')
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render(row) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'error',
          onClick: () => handleDelete(row.id)
        },
        { default: () => '删除' }
      )
    }
  }
]

async function handleUpload({ file }: UploadCustomRequestOptions) {
  if (!file.file) return

  uploading.value = true
  try {
    const response = await adminApi.uploadPDF(file.file as File)
    const taskId = response.data.task_id

    message.success('文件上传成功，开始处理')
    currentTask.value = {
      task_id: taskId,
      status: 'processing',
      progress: 0
    }

    startPolling(taskId)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

function startPolling(taskId: string) {
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  pollInterval = window.setInterval(async () => {
    try {
      const response = await adminApi.getTaskStatus(taskId)
      currentTask.value = response.data

      if (response.data.status === 'completed' || response.data.status === 'failed') {
        stopPolling()
        if (response.data.status === 'completed') {
          message.success('PDF 处理完成')
          loadBooks()
        } else {
          message.error('PDF 处理失败')
        }
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error)
    }
  }, 2000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

async function loadBooks() {
  loadingBooks.value = true
  try {
    const response = await adminApi.getBooks()
    books.value = response.data
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载书籍列表失败')
  } finally {
    loadingBooks.value = false
  }
}

async function handleDelete(bookId: number) {
  try {
    await adminApi.deleteBook(bookId)
    message.success('删除成功')
    loadBooks()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除失败')
  }
}

function getDefaultMessage(status: string): string {
  const messages: Record<string, string> = {
    pending: '任务等待处理中',
    processing: '正在处理 PDF 文件',
    completed: 'PDF 处理完成，词汇已导入数据库',
    failed: 'PDF 处理失败，请检查文件格式或重试'
  }
  return messages[status] || '未知状态'
}

function goToStudy() {
  router.push('/study')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  loadBooks()
})
</script>

<style scoped>
.admin-container {
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
  max-width: 1200px;
  margin: 0 auto;
}

.task-status {
  margin-top: 16px;
}
</style>
