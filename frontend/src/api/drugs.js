import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
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
  }
}

// 认证 API
export const authApi = {
  // 登录
  login(username, password) {
    return api.post('/auth/login/', { username, password })
  },
  
  // 注册
  register(data) {
    return api.post('/auth/register/', data)
  },
  
  // 登出
  logout() {
    return api.post('/auth/logout/')
  }
}

// 用户 API
export const userApi = {
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
  }
}

// Dashboard API
export const dashboardApi = {
  // 获取今日核心指标
  getStats() {
    return api.get('/dashboard/stats/')
  },
  
  // 获取消耗趋势预测
  getConsumptionTrend() {
    return api.get('/dashboard/consumption-trend/')
  },
  
  // 获取药品关联矩阵
  getDrugCorrelation() {
    return api.get('/dashboard/drug-correlation/')
  }
}

export default api
