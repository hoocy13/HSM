<template>
  <div class="register-container">
    <!-- 背景图片层 -->
    <div class="background-layer"></div>
    
    <!-- 主内容区域 -->
    <div class="content-wrapper">
      <!-- 左侧注册表单 -->
      <div class="register-card">
        <div class="register-header">
          <h1>Sign Up</h1>
          <p class="subtitle">创建新账号</p>
        </div>
        
        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="register-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              size="large"
              :prefix-icon="Message"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少6位）"
              size="large"
              :prefix-icon="Lock"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="password_confirm">
            <el-input
              v-model="registerForm.password_confirm"
              type="password"
              placeholder="请确认密码"
              size="large"
              :prefix-icon="Lock"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="first_name">
            <el-input
              v-model="registerForm.first_name"
              placeholder="请输入名（可选）"
              size="large"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="last_name">
            <el-input
              v-model="registerForm.last_name"
              placeholder="请输入姓（可选）"
              size="large"
              class="glass-input"
            />
          </el-form-item>
          
          <el-form-item prop="role">
            <el-select
              v-model="registerForm.role"
              placeholder="请选择角色"
              size="large"
              class="glass-select"
              style="width: 100%"
            >
              <el-option label="患者" value="patient" />
              <el-option label="医生" value="doctor" />
              <el-option label="药剂师" value="pharmacist" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleRegister"
              class="register-button"
            >
              {{ loading ? '注册中...' : 'Sign Up' }}
            </el-button>
          </el-form-item>
          
          <el-form-item>
            <div class="login-link">
              <span>已有账号？</span>
              <el-link type="primary" @click="goToLogin" class="link-text">立即登录</el-link>
            </div>
          </el-form-item>
          
          <el-divider>
            <span class="divider-text">Or</span>
          </el-divider>
          
          <el-form-item>
            <el-button
              size="large"
              class="social-button qq-button"
              @click="handleSocialLogin('qq')"
            >
              <span class="social-icon">QQ</span>
              Sign Up with QQ
            </el-button>
          </el-form-item>
          
          <el-form-item>
            <el-button
              size="large"
              class="social-button wechat-button"
              @click="handleSocialLogin('wechat')"
            >
              <span class="social-icon">微信</span>
              Sign Up with WeChat
            </el-button>
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
import { User, Lock, Message } from '@element-plus/icons-vue'
import { authApi } from '../api/drugs.js'

const router = useRouter()
const registerFormRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
  role: 'patient'
})

const validatePasswordConfirm = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 150, message: '用户名长度在 3 到 150 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' }
  ]
}


const handleRegister = async () => {
  if (!registerFormRef.value) return

  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authApi.register(registerForm)
        ElMessage.success('注册成功，请登录')
        router.push('/login')
      } catch (error) {
        console.error('注册失败:', error)
        const errorMsg = error.response?.data
        if (typeof errorMsg === 'object') {
          const firstError = Object.values(errorMsg)[0]
          ElMessage.error(Array.isArray(firstError) ? firstError[0] : firstError)
        } else {
          ElMessage.error(errorMsg || '注册失败，请检查输入信息')
        }
      } finally {
        loading.value = false
      }
    }
  })
}

const handleSocialLogin = (type) => {
  ElMessage.info(`${type === 'qq' ? 'QQ' : '微信'}登录功能开发中...`)
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
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

/* 注册卡片 - 增强的玻璃态效果 */
.register-card {
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
  max-height: 90vh;
  overflow-y: auto;
}

.register-header {
  margin-bottom: 40px;
}

.register-header h1 {
  color: #fff;
  font-size: 42px;
  font-weight: 700;
  margin: 0 0 10px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  margin: 0;
}

.register-form {
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

/* 现代风格的玻璃态选择框 */
:deep(.glass-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: none !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  transition: all 0.3s ease;
}

:deep(.glass-select .el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.5) !important;
}

:deep(.glass-select .el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.5) !important;
  box-shadow: none !important;
}

:deep(.glass-select .el-input__wrapper.is-filled) {
  background: rgba(255, 255, 255, 0.4) !important;
}

:deep(.glass-select input) {
  color: #333 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

:deep(.glass-select input::placeholder) {
  color: #999 !important;
}

:deep(.glass-select .el-input__suffix) {
  color: #666 !important;
}

/* 注册按钮 */
.register-button {
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

.register-button:hover {
  background: #333;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.register-button:active {
  transform: translateY(0);
}

/* 登录链接 */
.login-link {
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

/* 分隔线 */
:deep(.el-divider) {
  border-color: rgba(30, 60, 114, 0.2);
  margin: 30px 0;
}

/* 修复 Element Plus 分隔线文字背景色问题 */
:deep(.el-divider__text) {
  background-color: transparent !important;
  background: transparent !important;
}

:deep(.el-divider__text.is-left),
:deep(.el-divider__text.is-center),
:deep(.el-divider__text.is-right) {
  background-color: transparent !important;
  background: transparent !important;
}

.divider-text {
  color: #526d82;
  font-size: 14px;
  padding: 0 20px;
  background: transparent !important;
  background-color: transparent !important;
  position: relative;
  top: -4px;
  display: inline-block;
}

/* 社交登录按钮 */
.social-button {
  width: 100%;
  height: 50px;
  font-size: 15px;
  font-weight: 500;
  border-radius: 12px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.qq-button {
  background: #12b7f5;
  color: #fff;
}

.qq-button:hover {
  background: #0ea5d4;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(18, 183, 245, 0.3);
}

.wechat-button {
  background: #07c160;
  color: #fff;
  margin-top: 12px;
}

.wechat-button:hover {
  background: #06ad56;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(7, 193, 96, 0.3);
}

.social-icon {
  font-size: 18px;
  font-weight: 600;
}

/* 滚动条样式 */
.register-card::-webkit-scrollbar {
  width: 6px;
}

.register-card::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.register-card::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.register-card::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* 响应式设计 */

@media (max-width: 768px) {
  .register-container {
    padding: 20px;
  }
  
  .register-card,
  .announcement-panel {
    padding: 30px 25px;
  }
  
  .register-header h1 {
    font-size: 32px;
  }
}
</style>