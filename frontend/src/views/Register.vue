<template>
  <div class="register-container">
    <n-card class="register-card" title="注册 Smart Vocab">
      <n-form ref="formRef" :model="formValue" :rules="rules" size="large">
        <n-form-item path="email" label="邮箱">
          <n-input
            v-model:value="formValue.email"
            placeholder="请输入邮箱"
          />
        </n-form-item>
        <n-form-item path="username" label="用户名">
          <n-input
            v-model:value="formValue.username"
            placeholder="请输入用户名"
          />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="formValue.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码（至少6个字符）"
          />
        </n-form-item>
        <n-form-item path="confirmPassword" label="确认密码">
          <n-input
            v-model:value="formValue.confirmPassword"
            type="password"
            show-password-on="click"
            placeholder="请再次输入密码"
            @keydown.enter="handleRegister"
          />
        </n-form-item>
        <n-space vertical :size="16">
          <n-button
            type="primary"
            block
            size="large"
            :loading="loading"
            @click="handleRegister"
          >
            注册
          </n-button>
          <n-button text block @click="goToLogin">
            已有账号？立即登录
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
import type { FormInst, FormRules, FormItemRule } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formValue = ref({
  email: '',
  username: '',
  password: '',
  confirmPassword: ''
})

const validatePasswordSame = (rule: FormItemRule, value: string): boolean => {
  return value === formValue.value.password
}

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePasswordSame, message: '两次输入的密码不一致', trigger: 'blur' }
  ]
}

async function handleRegister() {
  try {
    await formRef.value?.validate()
    loading.value = true

    await authStore.register({
      email: formValue.value.email,
      username: formValue.value.username,
      password: formValue.value.password
    })

    message.success('注册成功')
    router.push('/study')
  } catch (error: any) {
    if (error?.response?.data?.detail) {
      message.error(error.response.data.detail)
    } else {
      message.error('注册失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 100%;
  max-width: 400px;
  margin: 20px;
}
</style>
