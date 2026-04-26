import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
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
      { path: '', redirect: '/layout/dashboard' },
      {
        path: 'dashboard',
        name: 'DashboardHome',
        component: () => import('../views/DashboardHome.vue'),
        meta: { title: '工作台' }
      },
      {
        path: 'data-overview',
        name: 'DataOverview',
        component: () => import('../views/DataOverview.vue'),
        meta: { title: '数据概览', roleRequired: ['admin', 'doctor', 'pharmacist'] }
      },
      {
        path: 'data-trends',
        name: 'DataTrends',
        component: () => import('../views/DataTrends.vue'),
        meta: { title: '数据趋势', roleRequired: ['admin', 'doctor', 'pharmacist'] }
      },
      {
        path: 'data-relations',
        name: 'DataRelations',
        component: () => import('../views/DataRelations.vue'),
        meta: { title: '关联关系图', roleRequired: ['admin', 'doctor', 'pharmacist'] }
      },
      {
        path: 'drugs',
        name: 'Drugs',
        component: () => import('../views/DrugList.vue'),
        meta: { title: '药品列表', roleRequired: ['pharmacist'] }
      },
      {
        path: 'drugs/stock-in',
        name: 'StockInHistory',
        component: () => import('../views/StockInHistory.vue'),
        meta: { title: '入库记录', roleRequired: ['pharmacist'] }
      },
      {
        path: 'drugs/inventory',
        name: 'InventoryAdjust',
        component: () => import('../views/InventoryAdjust.vue'),
        meta: { title: '库存盘点', roleRequired: ['pharmacist'] }
      },
      {
        path: 'medication-records',
        name: 'MedicationRecords',
        component: () => import('../views/MedicationRecords.vue'),
        meta: { title: '用药记录', roleRequired: ['doctor'] }
      },
      {
        path: 'dispense-approve',
        name: 'DispenseApprove',
        component: () => import('../views/DispenseApprove.vue'),
        meta: { title: '审批发药', roleRequired: ['pharmacist'] }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/UserManagement.vue'),
        meta: { title: '员工列表', roleRequired: ['admin'] }
      },
      {
        path: 'users/permissions',
        name: 'UserPermissions',
        component: () => import('../views/UserPermissions.vue'),
        meta: { title: '权限设置', roleRequired: ['admin'] }
      },
      {
        path: 'users/announcements',
        name: 'AnnouncementManage',
        component: () => import('../views/AnnouncementManage.vue'),
        meta: { title: '系统公告', roleRequired: ['admin'] }
      },
      {
        path: 'operation-logs',
        name: 'OperationLogs',
        component: () => import('../views/OperationLogs.vue'),
        meta: { title: '操作审计', roleRequired: ['admin'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

function defaultPathForRole(role) {
  if (role === 'admin') return '/layout/dashboard'
  if (role === 'doctor') return '/layout/dashboard'
  if (role === 'pharmacist') return '/layout/dashboard'
  return '/layout/dashboard'
}

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false

  let userRole = 'doctor'
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      userRole = user.role || 'doctor'
    }
  } catch (e) {
    console.error('解析用户信息失败:', e)
  }

  if (requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next(defaultPathForRole(userRole))
  } else if (requiresAuth && token) {
    const roleRequired = to.meta.roleRequired
    if (roleRequired && !roleRequired.includes(userRole)) {
      ElMessage.warning('您没有权限访问此页面')
      next(defaultPathForRole(userRole))
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
