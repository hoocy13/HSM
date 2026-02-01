<template>
  <div class="user-management-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
        </div>
      </template>
      
      <div class="toolbar">
        <el-input
          v-model="searchName"
          placeholder="搜索用户名"
          style="width: 300px"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      
      <div class="table-wrapper">
        <el-table
          :data="userList"
          v-loading="loading"
          style="width: 100%"
          stripe
        >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="first_name" label="名" />
        <el-table-column prop="last_name" label="姓" />
        <el-table-column prop="role" label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'doctor' ? 'warning' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : row.role === 'doctor' ? '医生' : '患者' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      :width="dialogWidth"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="formData.email"
            placeholder="请输入邮箱"
            type="email"
          />
        </el-form-item>
        <el-form-item label="名" prop="first_name">
          <el-input
            v-model="formData.first_name"
            placeholder="请输入名"
          />
        </el-form-item>
        <el-form-item label="姓" prop="last_name">
          <el-input
            v-model="formData.last_name"
            placeholder="请输入姓"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select
            v-model="formData.role"
            placeholder="请选择角色"
            style="width: 100%"
          >
            <el-option label="管理员" value="admin" />
            <el-option label="医生" value="doctor" />
            <el-option label="患者" value="patient" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { userApi } from '../api/drugs.js'

const userList = ref([])
const loading = ref(false)
const searchName = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const formRef = ref(null)
const isEdit = ref(false)
const editingUserId = ref(null)
const formData = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  role: 'patient'
})

// 响应式对话框宽度
const dialogWidth = computed(() => {
  if (window.innerWidth <= 768) {
    return '90%'
  }
  return '500px'
})

const dialogTitle = computed(() => {
  return isEdit.value ? '编辑用户' : '添加用户'
})

// 表单验证规则
const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度在 3 到 30 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (searchName.value) {
      params.username = searchName.value
    }
    
    const response = await userApi.getUsers(params)
    // 使用新数组确保Vue响应式更新
    userList.value = [...(response.data.results || [])]
    total.value = response.data.count || 0
    console.log('获取用户列表:', userList.value.map(u => ({ id: u.id, username: u.username, role: u.role })))
  } catch (error) {
    console.error('获取用户列表失败:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchUsers()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchUsers()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchUsers()
}

const handleEdit = (row) => {
  isEdit.value = true
  editingUserId.value = row.id
  formData.username = row.username
  formData.email = row.email || ''
  formData.first_name = row.first_name || ''
  formData.last_name = row.last_name || ''
  formData.role = row.role || 'patient'
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          // 更新用户
          const response = await userApi.updateUser(editingUserId.value, {
            username: formData.username,
            email: formData.email,
            first_name: formData.first_name,
            last_name: formData.last_name,
            role: formData.role
          })
          console.log('更新响应数据:', response.data)
          ElMessage.success('更新成功')
          
          // 立即更新列表中的用户数据
          const updatedUser = response.data
          console.log('更新后的用户角色:', updatedUser.role)
          const index = userList.value.findIndex(u => u.id === updatedUser.id)
          if (index !== -1) {
            // 使用 Vue 3 的响应式更新方式，创建新对象
            userList.value[index] = { ...userList.value[index], ...updatedUser }
            console.log('列表更新后的用户数据:', userList.value[index])
          }
        }
        dialogVisible.value = false
        // 强制重新获取用户列表以确保数据同步
        await fetchUsers()
      } catch (error) {
        console.error('操作失败:', error)
        const errorMsg = error.response?.data
        if (typeof errorMsg === 'object') {
          const firstError = Object.values(errorMsg)[0]
          ElMessage.error(Array.isArray(firstError) ? firstError[0] : firstError)
        } else {
          ElMessage.error(errorMsg || '操作失败')
        }
      }
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  isEdit.value = false
  editingUserId.value = null
  formData.username = ''
  formData.email = ''
  formData.first_name = ''
  formData.last_name = ''
  formData.role = 'patient'
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management-container {
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.toolbar {
  margin-bottom: 20px;
  width: 100%;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .pagination {
    justify-content: center;
  }
  
  :deep(.el-pagination) {
    flex-wrap: wrap;
  }
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 768px) {
  .dialog-footer {
    flex-direction: column;
  }
  
  .dialog-footer .el-button {
    width: 100%;
  }
}
</style>
