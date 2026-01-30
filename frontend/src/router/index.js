import { createRouter, createWebHistory } from 'vue-router'
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
        meta: { title: '药品管理', icon: 'Goods' }
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
        meta: { title: '智能预警', icon: 'Warning' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User' }
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

  if (requiresAuth && !token) {
    // 需要登录但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录但访问登录页，跳转到首页
    next('/layout')
  } else {
    next()
  }
})

export default router
