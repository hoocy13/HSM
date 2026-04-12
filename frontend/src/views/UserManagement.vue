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
        <el-button type="primary" @click="handleAdd">添加用户</el-button>
      </div>
      
      <div class="table-wrapper">
        <el-table
          :data="userList"
          v-loading="loading"
          style="width: 100%"
          stripe
        >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="头像" width="72" align="center">
          <template #default="{ row }">
            <el-avatar v-if="row.avatar" :src="row.avatar" :size="36" />
            <el-avatar v-else :size="36">{{ (row.first_name || row.username || '?').slice(0, 1) }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column label="姓名" min-width="100">
          <template #default="{ row }">
            {{ [row.first_name, row.last_name].filter(Boolean).join(' ') || row.username }}
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="department" label="科室" width="120" />
        <el-table-column prop="role" label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.role === 'admin' ? 'danger' : row.role === 'doctor' ? 'warning' : row.role === 'pharmacist' ? 'success' : 'info'"
              size="small"
            >
              {{ roleLabel(row.role) }}
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
        <el-form-item v-if="!isEdit" label="初始密码" prop="password">
          <el-input v-model="formData.password" type="password" placeholder="至少 6 位" show-password />
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
        <el-form-item label="头像 URL" prop="avatar">
          <el-input v-model="formData.avatar" placeholder="可选，图片地址" />
        </el-form-item>
        <el-form-item label="科室" prop="department">
          <el-input v-model="formData.department" placeholder="科室" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select
            v-model="formData.role"
            placeholder="请选择角色"
            style="width: 100%"
          >
            <el-option label="管理员" value="admin" />
            <el-option label="医生" value="doctor" />
            <el-option label="药剂师" value="pharmacist" />
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
  password: '',
  email: '',
  first_name: '',
  last_name: '',
  avatar: '',
  department: '',
  role: 'doctor'
})

const roleLabel = (r) =>
  ({
    admin: '管理员',
    doctor: '医生',
    pharmacist: '药剂师'
  }[r] || r)

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
  password: [
    {
      validator: (_r, v, cb) => {
        if (!isEdit.value && (!v || String(v).length < 6)) {
          cb(new Error('新增用户时密码至少 6 位'))
        } else cb()
      },
      trigger: 'blur'
    }
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

const handleAdd = () => {
  isEdit.value = false
  editingUserId.value = null
  formData.username = ''
  formData.password = ''
  formData.email = ''
  formData.first_name = ''
  formData.last_name = ''
  formData.avatar = ''
  formData.department = ''
  formData.role = 'doctor'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingUserId.value = row.id
  formData.username = row.username
  formData.password = ''
  formData.email = row.email || ''
  formData.first_name = row.first_name || ''
  formData.last_name = row.last_name || ''
  formData.avatar = row.avatar || ''
  formData.department = row.department || ''
  formData.role = row.role || 'doctor'
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          const response = await userApi.updateUser(editingUserId.value, {
            username: formData.username,
            email: formData.email,
            first_name: formData.first_name,
            last_name: formData.last_name,
            role_write: formData.role,
            avatar_write: formData.avatar,
            department_write: formData.department
          })
          ElMessage.success('更新成功')
          const updatedUser = response.data
          const index = userList.value.findIndex(u => u.id === updatedUser.id)
          if (index !== -1) {
            userList.value[index] = { ...userList.value[index], ...updatedUser }
          }
        } else {
          await userApi.createUser({
            username: formData.username,
            password: formData.password,
            email: formData.email,
            first_name: formData.first_name,
            last_name: formData.last_name,
            role_write: formData.role,
            department_write: formData.department,
            avatar_write: formData.avatar
          })
          ElMessage.success('用户已创建')
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
  formData.password = ''
  formData.email = ''
  formData.first_name = ''
  formData.last_name = ''
  formData.avatar = ''
  formData.department = ''
  formData.role = 'doctor'
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
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
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
