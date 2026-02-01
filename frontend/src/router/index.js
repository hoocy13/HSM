import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api/drugs.js'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/layout'
  },
  {
    path: '/layout',
    component: () => import('../layout/index.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/layout/dashboard'
      },
      {
        path: 'drugs',
        name: 'Drugs',
        component: () => import('../views/DrugList.vue'),
        meta: { title: '药品管理', icon: 'Goods', roleRequired: ['admin', 'doctor'] }
      },
      {
        path: 'medication-records',
        name: 'MedicationRecords',
        component: () => import('../views/MedicationRecords.vue'),
        meta: { title: '用药记录', icon: 'Document' }
      },
      {
        path: 'warnings',
        name: 'Warnings',
        component: () => import('../views/Warnings.vue'),
        meta: { title: '智能预警', icon: 'Warning', roleRequired: ['admin'] }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User', roleRequired: ['admin'] }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '数据看板', icon: 'DataAnalysis' }
      },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false
  
  // 获取用户角色
  let userRole = 'patient'
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      userRole = user.role || 'patient'
    }
  } catch (e) {
    console.error('解析用户信息失败:', e)
  }

  if (requiresAuth && !token) {
    // 需要登录但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录但访问登录页，根据角色跳转
    if (userRole === 'admin') {
      next('/layout/dashboard')
    } else if (userRole === 'doctor') {
      next('/layout/drugs')
    } else {
      next('/layout/medication-records')
    }
  } else if (requiresAuth && token) {
    // 权限检查：某些页面需要特定角色
    const roleRequired = to.meta.roleRequired
    if (roleRequired && !roleRequired.includes(userRole)) {
      // 权限不足，跳转到对应角色的默认页面
      ElMessage.warning('您没有权限访问此页面')
      if (userRole === 'admin') {
        next('/layout/dashboard')
      } else if (userRole === 'doctor') {
        next('/layout/drugs')
      } else {
        next('/layout/medication-records')
      }
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
