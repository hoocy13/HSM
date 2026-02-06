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
        <el-button
          v-if="userRole === 'admin' || userRole === 'pharmacist'"
          type="warning"
          @click="openInventoryDialog"
        >
          库存盘点
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
        <el-table-column label="操作" width="360" fixed="right" v-if="userRole !== 'patient'">
          <template #default="{ row }">
            <el-button type="info" size="small" @click="openStockTrend(row)">库存轨迹</el-button>
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
        <el-form-item label="成本价格" prop="cost_price">
          <el-input-number
            v-model="formData.cost_price"
            :min="0"
            :precision="2"
            placeholder="请输入成本价格（元）"
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
        <el-form-item label="安全库存下限" prop="min_stock">
          <el-input-number v-model="formData.min_stock" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="效期预警(天)" prop="expiry_warning_days">
          <el-input-number v-model="formData.expiry_warning_days" :min="1" :max="365" style="width: 100%" />
        </el-form-item>
        <el-form-item label="所属科室">
          <el-input v-model="formData.department" placeholder="空=全院共用" clearable />
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

    <!-- 库存盘点 / 损溢 -->
    <el-dialog
      v-model="inventoryDialogVisible"
      title="库存盘点 / 损溢录入"
      :width="dialogWidth"
      @open="ensureDrugOptions"
    >
      <el-form ref="invFormRef" :model="invForm" :rules="invRules" label-width="100px">
        <el-form-item label="药品" prop="drug">
          <el-select v-model="invForm.drug" placeholder="请选择药品" filterable style="width: 100%">
            <el-option
              v-for="d in allDrugs"
              :key="d.id"
              :label="`${d.name} (库存 ${d.stock})`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="调整数量" prop="quantity_change">
          <el-input-number v-model="invForm.quantity_change" style="width: 100%" />
          <div class="hint">正数增加库存，负数减少（如报损）。</div>
        </el-form-item>
        <el-form-item label="原因" prop="reason">
          <el-input v-model="invForm.reason" type="textarea" :rows="2" placeholder="必填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inventoryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="invSubmitting" @click="submitInventory">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="stockTrendVisible" title="库存变化轨迹" width="720px" @opened="renderTrendChart">
      <div ref="trendChartRef" style="width: 100%; height: 380px;"></div>
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
import * as echarts from 'echarts'
import { drugApi, inventoryApi } from '../api/drugs.js'

// 数据
const drugList = ref([])
const loading = ref(false)
const searchName = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const warningDrugs = ref([])
const userRole = ref('patient')

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
const inventoryDialogVisible = ref(false)
const invFormRef = ref(null)
const invSubmitting = ref(false)
const allDrugs = ref([])
const invForm = reactive({
  drug: null,
  quantity_change: 0,
  reason: ''
})
const invRules = {
  drug: [{ required: true, message: '请选择药品', trigger: 'change' }],
  quantity_change: [{ required: true, message: '请输入调整数量', trigger: 'blur' }],
  reason: [{ required: true, message: '请填写原因', trigger: 'blur' }]
}
const stockTrendVisible = ref(false)
const trendChartRef = ref(null)
const trendDrugId = ref(null)
let trendChart = null

const warningsDialogVisible = ref(false)
const dialogTitle = ref('添加药品')
const formRef = ref(null)
const stockInFormRef = ref(null)
const formData = reactive({
  id: null,
  name: '',
  stock: 0,
  cost_price: 0,
  expiry_date: null,
  min_stock: 10,
  expiry_warning_days: 30,
  department: ''
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
const openStockTrend = (row) => {
  trendDrugId.value = row.id
  stockTrendVisible.value = true
}

const renderTrendChart = async () => {
  if (!trendChartRef.value || !trendDrugId.value) return
  try {
    const { data } = await drugApi.getStockTrend(trendDrugId.value)
    const hist = data.history || []
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['在库数量', '本次变动'] },
      xAxis: { type: 'category', data: hist.map((h) => h.date), axisLabel: { rotate: 35 } },
      yAxis: { type: 'value', name: '数量' },
      series: [
        { name: '在库数量', type: 'line', smooth: true, data: hist.map((h) => h.stock) },
        { name: '本次变动', type: 'bar', data: hist.map((h) => h.change) }
      ]
    })
  } catch (e) {
    console.error(e)
    ElMessage.error('加载库存轨迹失败')
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加药品'
  formData.id = null
  formData.name = ''
  formData.stock = 0
  formData.cost_price = 0
  formData.expiry_date = null
  formData.min_stock = 10
  formData.expiry_warning_days = 30
  formData.department = ''
  dialogVisible.value = true
}

// 编辑药品
const handleEdit = (row) => {
  dialogTitle.value = '编辑药品'
  formData.id = row.id
  formData.name = row.name
  formData.stock = row.stock
  formData.cost_price = row.cost_price || 0
  formData.expiry_date = row.expiry_date
  formData.min_stock = row.min_stock ?? 10
  formData.expiry_warning_days = row.expiry_warning_days ?? 30
  formData.department = row.department || ''
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

const ensureDrugOptions = async () => {
  if (allDrugs.value.length) return
  try {
    const res = await drugApi.getDrugs({ page_size: 2000 })
    allDrugs.value = res.data.results || []
  } catch (e) {
    console.error(e)
  }
}

const openInventoryDialog = async () => {
  invForm.drug = null
  invForm.quantity_change = 0
  invForm.reason = ''
  await ensureDrugOptions()
  inventoryDialogVisible.value = true
}

const submitInventory = async () => {
  if (!invFormRef.value) return
  await invFormRef.value.validate(async (valid) => {
    if (!valid) return
    invSubmitting.value = true
    try {
      await inventoryApi.create({
        drug: invForm.drug,
        quantity_change: invForm.quantity_change,
        reason: invForm.reason
      })
      ElMessage.success('已提交')
      inventoryDialogVisible.value = false
      fetchDrugs()
    } catch (e) {
      const d = e.response?.data
      const msg = typeof d === 'object' ? Object.values(d).flat()[0] : d
      ElMessage.error(msg || '提交失败')
    } finally {
      invSubmitting.value = false
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
          cost_price: formData.cost_price,
          expiry_date: formData.expiry_date,
          min_stock: formData.min_stock,
          expiry_warning_days: formData.expiry_warning_days,
          department: formData.department || ''
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
  formData.cost_price = 0
  formData.expiry_date = null
  formData.min_stock = 10
  formData.expiry_warning_days = 30
  formData.department = ''
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
  // 获取当前用户信息
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      userRole.value = user.role || 'patient'
    }
  } catch (e) {
    console.error('解析用户信息失败:', e)
  }
  
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

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
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
