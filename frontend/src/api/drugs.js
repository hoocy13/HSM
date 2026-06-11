import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 药品 API
export const drugApi = {
  // 获取药品列表
  getDrugs(params = {}) {
    return api.get('/drugs/', { params })
  },
  
  // 获取单个药品
  getDrug(id) {
    return api.get(`/drugs/${id}/`)
  },
  
  // 创建药品
  createDrug(data) {
    return api.post('/drugs/', data)
  },
  
  // 更新药品（完整更新）
  updateDrug(id, data) {
    return api.put(`/drugs/${id}/`, data)
  },
  
  // 更新药品（部分更新）
  patchDrug(id, data) {
    return api.patch(`/drugs/${id}/`, data)
  },
  
  // 删除药品
  deleteDrug(id) {
    return api.delete(`/drugs/${id}/`)
  },
  
  // 药品入库
  stockIn(id, quantity) {
    return api.post(`/drugs/${id}/stock-in/`, { quantity })
  },
  
  // 获取预警药品列表
  getWarnings() {
    return api.get('/drugs/warnings/')
  },

  getStockTrend(id) {
    return api.get(`/drugs/${id}/stock-trend/`)
  }
}

// 库存盘点 / 损溢
export const inventoryApi = {
  list(params = {}) {
    return api.get('/inventory-adjustments/', { params })
  },
  create(data) {
    return api.post('/inventory-adjustments/', data)
  }
}

// 用药记录 API
export const medicationApi = {
  // 获取用药记录列表
  getRecords(params = {}) {
    return api.get('/medication-records/', { params })
  },
  
  // 创建用药记录
  createRecord(data) {
    return api.post('/medication-records/', data)
  },
  
  // 删除用药记录
  deleteRecord(id) {
    return api.delete(`/medication-records/${id}/`)
  },

  cancelPrescription(id) {
    return api.post(`/medication-records/${id}/cancel/`)
  },

  departmentUsers() {
    return api.get('/medication-records/department-users/')
  },

  dispense(id, data = {}) {
    return api.post(`/medication-records/${id}/dispense/`, data)
  },

  undoDispense(id) {
    return api.post(`/medication-records/${id}/undo-dispense/`)
  },

  rejectPending(id) {
    return api.post(`/medication-records/${id}/reject-pending/`)
  }
}

// 认证 API
export const authApi = {
  // 登录
  login(username, password) {
    return api.post('/auth/login/', { username, password })
  },
  
  // 登出
  logout() {
    return api.post('/auth/logout/')
  }
}

// 用户 API
export const userApi = {
  createUser(data) {
    return api.post('/users/', data)
  },

  // 获取用户列表
  getUsers(params = {}) {
    return api.get('/users/', { params })
  },
  
  // 获取单个用户
  getUser(id) {
    return api.get(`/users/${id}/`)
  },
  
  // 更新用户
  updateUser(id, data) {
    return api.put(`/users/${id}/`, data)
  },
  
  // 部分更新用户
  patchUser(id, data) {
    return api.patch(`/users/${id}/`, data)
  },

  // 删除用户
  deleteUser(id) {
    return api.delete(`/users/${id}/`)
  },

  deactivateUser(id) {
    return api.post(`/users/${id}/deactivate/`)
  },

  activateUser(id) {
    return api.post(`/users/${id}/activate/`)
  }
}

// Dashboard API
export const dashboardApi = {
  // 首页聚合（公告、政策、角色提醒）
  getHome() {
    return api.get('/dashboard/')
  },

  // 获取今日核心指标
  getStats(params = {}) {
    return api.get('/dashboard/stats/', { params })
  },

  getTrends(params = {}) {
    return api.get('/dashboard/trends/', { params })
  },
  
  // 获取消耗趋势预测
  getConsumptionTrend() {
    return api.get('/dashboard/consumption-trend/')
  },
  
  // 获取药品关联矩阵
  getDrugCorrelation() {
    return api.get('/dashboard/drug-correlation/')
  },
  
  // 获取库存紧缺Top10
  getLowStockTop10() {
    return api.get('/dashboard/low-stock-top10/')
  },
  
  // 获取过期预警分布
  getExpiryDistribution() {
    return api.get('/dashboard/expiry-distribution/')
  },
  
  // 获取月度消耗趋势
  getMonthlyConsumption() {
    return api.get('/dashboard/monthly-consumption/')
  },
  
  // 获取经常一起被开出的药品Top5
  getTop5Correlated() {
    return api.get('/dashboard/top5-correlated/')
  },

  getRecommendations() {
    return api.get('/dashboard/recommendations/')
  }
}

export const operationLogApi = {
  list(params = {}) {
    return api.get('/operation-logs/', { params })
  }
}

/** 系统公告（管理员） */
export const announcementApi = {
  list(params = {}) {
    return api.get('/announcements/', { params })
  },
  create(data) {
    return api.post('/announcements/', data)
  },
  patch(id, data) {
    return api.patch(`/announcements/${id}/`, data)
  },
  delete(id) {
    return api.delete(`/announcements/${id}/`)
  }
}

export default api
