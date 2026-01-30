<template>
  <div class="drug-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>药品管理</span>
          <el-button type="warning" @click="showWarnings">
            <el-icon><Warning /></el-icon>
            查看预警
          </el-button>
        </div>
      </template>
      
      <!-- 搜索和操作栏 -->
      <div class="toolbar">
        <el-input
          v-model="searchName"
          placeholder="搜索药品名称"
          style="width: 300px"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>
          添加药品
        </el-button>
      </div>
      
      <!-- 药品表格 -->
      <div class="table-wrapper">
        <el-table
          :data="drugList"
          v-loading="loading"
          style="width: 100%"
          stripe
          :row-class-name="getRowClassName"
        >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="stock" label="库存" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStockTagType(row.stock)" size="small">
              {{ row.stock }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="有效期" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.expiry_date" :class="{ 'warning-text': row.is_expiring_soon }">
              {{ formatDateOnly(row.expiry_date) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="预警状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_expiring_soon" type="danger" size="small">即将过期</el-tag>
            <el-tag v-else-if="row.is_low_stock" type="warning" size="small">库存不足</el-tag>
            <el-tag v-else type="success" size="small">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button
              type="success"
              size="small"
              @click="handleStockIn(row)"
            >
              入库
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>
      
      <!-- 分页 -->
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
    
    <!-- 添加/编辑对话框 -->
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
        <el-form-item label="药品名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入药品名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number
            v-model="formData.stock"
            :min="0"
            placeholder="请输入库存数量"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="有效期" prop="expiry_date">
          <el-date-picker
            v-model="formData.expiry_date"
            type="date"
            placeholder="选择有效期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 入库对话框 -->
    <el-dialog
      v-model="stockInDialogVisible"
      title="药品入库"
      :width="dialogWidth"
    >
      <el-form
        ref="stockInFormRef"
        :model="stockInForm"
        :rules="stockInRules"
        label-width="100px"
      >
        <el-form-item label="药品名称">
          <el-input v-model="stockInForm.drugName" disabled />
        </el-form-item>
        <el-form-item label="当前库存">
          <el-input v-model="stockInForm.currentStock" disabled />
        </el-form-item>
        <el-form-item label="入库数量" prop="quantity">
          <el-input-number
            v-model="stockInForm.quantity"
            :min="1"
            placeholder="请输入入库数量"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="stockInDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleStockInSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 预警对话框 -->
    <el-dialog
      v-model="warningsDialogVisible"
      title="药品预警"
      :width="warningDialogWidth"
    >
      <el-table :data="warningDrugs" stripe>
        <el-table-column prop="name" label="药品名称" />
        <el-table-column prop="stock" label="库存" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStockTagType(row.stock)" size="small">
              {{ row.stock }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="有效期" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.expiry_date" :class="{ 'warning-text': row.is_expiring_soon }">
              {{ formatDateOnly(row.expiry_date) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="预警原因" width="200">
          <template #default="{ row }">
            <el-tag v-if="row.is_expiring_soon" type="danger" size="small">即将过期</el-tag>
            <el-tag v-if="row.is_low_stock" type="warning" size="small">库存不足</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Warning } from '@element-plus/icons-vue'
import { drugApi } from '../api/drugs.js'

// 数据
const drugList = ref([])
const loading = ref(false)
const searchName = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const warningDrugs = ref([])

// 响应式对话框宽度
const dialogWidth = computed(() => {
  if (window.innerWidth <= 768) {
    return '90%'
  } else if (window.innerWidth <= 1200) {
    return '70%'
  }
  return '500px'
})

// 预警对话框宽度（需要更宽）
const warningDialogWidth = computed(() => {
  if (window.innerWidth <= 768) {
    return '95%'
  } else if (window.innerWidth <= 1200) {
    return '85%'
  }
  return '900px'
})

// 对话框
const dialogVisible = ref(false)
const stockInDialogVisible = ref(false)
const warningsDialogVisible = ref(false)
const dialogTitle = ref('添加药品')
const formRef = ref(null)
const stockInFormRef = ref(null)
const formData = reactive({
  id: null,
  name: '',
  stock: 0,
  expiry_date: null
})

const stockInForm = reactive({
  drugId: null,
  drugName: '',
  currentStock: 0,
  quantity: 1
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入药品名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  stock: [
    { required: true, message: '请输入库存数量', trigger: 'blur' },
    { type: 'number', min: 0, message: '库存不能为负数', trigger: 'blur' }
  ]
}

const stockInRules = {
  quantity: [
    { required: true, message: '请输入入库数量', trigger: 'blur' },
    { type: 'number', min: 1, message: '入库数量必须大于0', trigger: 'blur' }
  ]
}

// 获取药品列表
const fetchDrugs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (searchName.value) {
      params.name = searchName.value
    }
    
    const response = await drugApi.getDrugs(params)
    drugList.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取药品列表失败:', error)
    ElMessage.error('获取药品列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 获取预警药品
const fetchWarnings = async () => {
  try {
    const response = await drugApi.getWarnings()
    warningDrugs.value = response.data.results || []
  } catch (error) {
    console.error('获取预警药品失败:', error)
    ElMessage.error('获取预警药品失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchDrugs()
}

// 分页大小改变
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchDrugs()
}

// 页码改变
const handlePageChange = (page) => {
  currentPage.value = page
  fetchDrugs()
}

// 添加药品
const handleAdd = () => {
  dialogTitle.value = '添加药品'
  formData.id = null
  formData.name = ''
  formData.stock = 0
  formData.expiry_date = null
  dialogVisible.value = true
}

// 编辑药品
const handleEdit = (row) => {
  dialogTitle.value = '编辑药品'
  formData.id = row.id
  formData.name = row.name
  formData.stock = row.stock
  formData.expiry_date = row.expiry_date
  dialogVisible.value = true
}

// 删除药品
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除药品 "${row.name}" 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await drugApi.deleteDrug(row.id)
      ElMessage.success('删除成功')
      fetchDrugs()
    } catch (error) {
      console.error('删除药品失败:', error)
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 药品入库
const handleStockIn = (row) => {
  stockInForm.drugId = row.id
  stockInForm.drugName = row.name
  stockInForm.currentStock = row.stock
  stockInForm.quantity = 1
  stockInDialogVisible.value = true
}

// 提交入库
const handleStockInSubmit = async () => {
  if (!stockInFormRef.value) return
  
  await stockInFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await drugApi.stockIn(stockInForm.drugId, stockInForm.quantity)
        ElMessage.success('入库成功')
        stockInDialogVisible.value = false
        fetchDrugs()
      } catch (error) {
        console.error('入库失败:', error)
        ElMessage.error('入库失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  })
}

// 显示预警
const showWarnings = async () => {
  await fetchWarnings()
  warningsDialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const data = {
          name: formData.name,
          stock: formData.stock,
          expiry_date: formData.expiry_date
        }
        
        if (formData.id) {
          await drugApi.patchDrug(formData.id, data)
          ElMessage.success('更新成功')
        } else {
          await drugApi.createDrug(data)
          ElMessage.success('添加成功')
        }
        dialogVisible.value = false
        fetchDrugs()
      } catch (error) {
        console.error('操作失败:', error)
        ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  formData.id = null
  formData.name = ''
  formData.stock = 0
  formData.expiry_date = null
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化日期（仅日期）
const formatDateOnly = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

// 获取库存标签类型
const getStockTagType = (stock) => {
  if (stock < 50) return 'danger'
  if (stock < 100) return 'warning'
  return 'success'
}

// 获取行样式类名（用于预警高亮）
const getRowClassName = ({ row }) => {
  if (row.is_expiring_soon || row.is_low_stock) {
    return 'warning-row'
  }
  return ''
}

// 窗口大小改变处理
const handleResize = () => {
  // 触发响应式更新
}

// 组件挂载时获取数据
onMounted(() => {
  fetchDrugs()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.drug-list-container {
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }
  
  .toolbar .el-input {
    width: 100% !important;
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

.warning-text {
  color: #f56c6c;
  font-weight: bold;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .pagination {
    justify-content: center;
  }
  
  :deep(.el-pagination) {
    flex-wrap: wrap;
  }
}
</style>

<style>
/* 全局样式：预警行高亮 */
.el-table .warning-row {
  background-color: #fef0f0 !important;
}

.el-table .warning-row:hover {
  background-color: #fde2e2 !important;
}
</style>
