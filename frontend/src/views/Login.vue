<template>
  <div class="login-container">
    <!-- 背景图片层 -->
    <div class="background-layer"></div>
    
    <!-- 主内容区域 -->
    <div class="content-wrapper">
      <!-- 左侧登录表单 -->
      <div class="login-card">
        <div class="login-header">
          <h1>Log In</h1>
          <p class="subtitle">医院药品管理系统</p>
        </div>
        
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              class="glass-input"
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              class="login-button"
            >
              {{ loading ? '登录中...' : 'Log In' }}
            </el-button>
          </el-form-item>
          
          <el-form-item>
            <div class="register-link">
              <span>还没有账号？</span>
              <el-link type="primary" @click="goToRegister" class="link-text">立即注册</el-link>
            </div>
          </el-form-item>
          
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api/drugs.js'

const router = useRouter()

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}



const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await authApi.login(loginForm.username, loginForm.password)
        
        if (response.data.token) {
          localStorage.setItem('token', response.data.token)
          localStorage.setItem('user', JSON.stringify(response.data.user))
          
          ElMessage.success('登录成功')
          
          const userRole = response.data.user.role || 'patient'
          if (userRole === 'admin' || userRole === 'pharmacist') {
            router.push('/layout/dashboard')
          } else if (userRole === 'doctor') {
            router.push('/layout/drugs')
          } else {
            router.push('/layout/medication-records')
          }
        } else {
          ElMessage.error('登录失败：未收到 token')
        }
      } catch (error) {
        console.error('登录失败:', error)
        ElMessage.error(error.response?.data?.error || '登录失败，请检查用户名和密码')
      } finally {
        loading.value = false
      }
    }
  })
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  width: 100%;
  min-height: 100vh;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  box-sizing: border-box;
  overflow: hidden;
}

/* 背景层 - 优化的渐变配色 */
.background-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #1e3c72, #2a5298, #526d82);
  background-size: 400% 400%;
  animation: gradientMove 20s ease infinite;
  z-index: 0;
}

@keyframes gradientMove {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* 主内容包装器 */
.content-wrapper {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  max-width: 500px;
}

/* 登录卡片 - 增强的玻璃态效果 */
.login-card {
  width: 100%;
  max-width: 500px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  padding: 50px 40px;
  box-sizing: border-box;
}

.login-header {
  margin-bottom: 40px;
}

.login-header h1 {
  color: #1e3c72;
  font-size: 42px;
  font-weight: 700;
  margin: 0 0 10px 0;
  text-shadow: 0 2px 10px rgba(255, 255, 255, 0.3);
}

.subtitle {
  color: #526d82;
  font-size: 16px;
  margin: 0;
}

.login-form {
  margin-top: 30px;
}

/* 现代风格的玻璃态输入框 */
:deep(.glass-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: none !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  transition: all 0.3s ease;
  padding: 0;
}

:deep(.glass-input .el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.5) !important;
}

:deep(.glass-input .el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.5) !important;
  box-shadow: none !important;
}

:deep(.glass-input .el-input__wrapper.is-focus:hover) {
  background: rgba(255, 255, 255, 0.6) !important;
}

/* 确保输入框在所有状态下都保持玻璃态效果 */
:deep(.glass-input .el-input__wrapper.is-filled) {
  background: rgba(255, 255, 255, 0.4) !important;
}

:deep(.glass-input .el-input__wrapper.is-filled:hover) {
  background: rgba(255, 255, 255, 0.5) !important;
}

:deep(.glass-input input) {
  color: #333 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

:deep(.glass-input input::placeholder) {
  color: #999 !important;
}

:deep(.glass-input .el-input__prefix) {
  color: #666 !important;
}

/* 移除Element Plus默认的白色背景和边框 */
:deep(.glass-input .el-input__inner) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* 登录按钮 */
.login-button {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  background: #000;
  border: none;
  border-radius: 12px;
  color: #fff;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.login-button:hover {
  background: #333;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.login-button:active {
  transform: translateY(0);
}

/* 注册链接 */
.register-link {
  width: 100%;
  text-align: center;
  color: #526d82;
  font-size: 14px;
}

.link-text {
  color: #1e3c72;
  font-weight: 600;
  text-decoration: underline;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-container {
    padding: 20px;
  }
  
  .login-card {
    padding: 30px 25px;
  }
  
  .login-header h1 {
    font-size: 32px;
  }
}

@media (max-width: 768px) {
  .login-container {
    padding: 20px;
  }
  
  .login-card,
  .announcement-panel {
    padding: 30px 25px;
  }
  
  .login-header h1 {
    font-size: 32px;
  }
}
</style>