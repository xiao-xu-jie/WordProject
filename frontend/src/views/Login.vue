<template>
  <div class="login-container">
    <n-card class="login-card" title="登录 Smart Vocab">
      <n-form ref="formRef" :model="formValue" :rules="rules" size="large">
        <n-form-item path="email" label="邮箱">
          <n-input
            v-model:value="formValue.email"
            placeholder="请输入邮箱"
            @keydown.enter="handleLogin"
          />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="formValue.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
            @keydown.enter="handleLogin"
          />
        </n-form-item>
        <n-space vertical :size="16">
          <n-button
            type="primary"
            block
            size="large"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </n-button>
          <n-button text block @click="goToRegister">
            还没有账号？立即注册
          </n-button>
        </n-space>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NCard, NForm, NFormItem, NInput, NButton, NSpace } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import type { FormInst, FormRules } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formValue = ref({
  email: '',
  password: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  try {
    await formRef.value?.validate()
    loading.value = true

    await authStore.login(formValue.value)
    message.success('登录成功')
    router.push('/study')
  } catch (error: any) {
    if (error?.response?.data?.detail) {
      message.error(error.response.data.detail)
    } else {
      message.error('登录失败，请检查邮箱和密码')
    }
  } finally {
    loading.value = false
  }
}

function goToRegister() {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  margin: 20px;
}
</style>
