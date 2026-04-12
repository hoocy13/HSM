<template>
  <div class="medication-records-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用药记录</span>
        </div>
      </template>
      
      <div class="toolbar">
        <el-input
          v-model="searchDrug"
          placeholder="搜索药品名称"
          style="width: 300px"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <div style="display: flex; gap: 10px;">
          <el-button 
            v-if="userRole === 'doctor'" 
            type="primary" 
            :icon="Document"
            @click="handleAddPrescription"
          >
            开具处方
          </el-button>
          <el-button 
            v-if="userRole === 'doctor'" 
            :icon="Plus"
            @click="handleAdd"
          >
            添加单条记录
          </el-button>
        </div>
      </div>
      
      <div class="table-wrapper">
        <el-table
          :data="recordList"
          v-loading="loading"
          style="width: 100%"
          stripe
        >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="prescription_id" label="处方号" width="150">
          <template #default="{ row }">
            {{ row.prescription_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="drug_name" label="药品名称" />
        <el-table-column prop="disease_name" label="疾病/诊断" width="120">
          <template #default="{ row }">
            {{ row.disease_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="user" label="用户" width="150">
          <template #default="{ row }">
            {{ row.user?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="100" align="center" />
        <el-table-column prop="record_time" label="记录时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.record_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'CANCELLED'" type="info" size="small">已作废</el-tag>
            <el-tag v-else type="success" size="small">有效</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="canCancel(row)"
              type="warning"
              size="small"
              @click="handleCancel(row)"
            >
              撤销处方
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
      
      <!-- 添加单条用药记录对话框 -->
      <el-dialog
        v-model="dialogVisible"
        title="添加用药记录"
        :width="dialogWidth"
        @close="resetForm"
        :close-on-click-modal="false"
      >
        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-width="100px"
        >
          <el-form-item label="药品" prop="drug">
            <el-select
              v-model="formData.drug"
              placeholder="请选择药品"
              filterable
              style="width: 100%"
              @change="handleDrugChange"
            >
              <el-option
                v-for="drug in drugList"
                :key="drug.id"
                :label="`${drug.name} (库存: ${drug.stock})`"
                :value="drug.id"
                :disabled="drug.stock === 0"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="数量" prop="quantity">
            <el-input-number
              v-model="formData.quantity"
              :min="minQuantity"
              :max="maxQuantity"
              placeholder="请先选择药品"
              style="width: 100%"
              :disabled="!selectedDrug || selectedDrug.stock === 0"
            />
            <div v-if="selectedDrug" class="stock-info">
              当前库存：{{ selectedDrug.stock }} 件
            </div>
            <div v-else class="stock-info" style="color: #909399;">
              请先选择药品
            </div>
          </el-form-item>
          <el-form-item label="疾病/诊断">
            <el-input
              v-model="formData.disease_name"
              placeholder="如：流感、高血压（可选，用于趋势统计）"
              clearable
            />
          </el-form-item>
          <el-form-item label="备注" prop="notes">
            <el-input
              v-model="formData.notes"
              type="textarea"
              :rows="3"
              placeholder="请输入备注（可选）"
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

      <!-- 开具处方（每张处方仅一种药品） -->
      <el-dialog
        v-model="prescriptionDialogVisible"
        title="开具处方"
        :width="prescriptionDialogWidth"
        @close="resetPrescriptionForm"
        :close-on-click-modal="false"
      >
        <el-form
          ref="prescriptionFormRef"
          :model="prescriptionFormData"
          label-width="100px"
        >
          <el-form-item label="药品" prop="drug">
            <el-select
              v-model="prescriptionFormData.drug"
              placeholder="请选择一种药品"
              filterable
              style="width: 100%"
              @change="handlePrescriptionDrugChange"
            >
              <el-option
                v-for="drug in drugList"
                :key="drug.id"
                :label="`${drug.name} (库存: ${drug.stock})`"
                :value="drug.id"
                :disabled="drug.stock === 0"
              />
            </el-select>
            <div v-if="prescriptionFormData.drug" class="stock-info">
              当前库存：{{ getDrugStock(prescriptionFormData.drug) }} 件
            </div>
          </el-form-item>
          <el-form-item label="数量" prop="quantity">
            <el-input-number
              v-model="prescriptionFormData.quantity"
              :min="rxMinQty"
              :max="rxMaxQty"
              style="width: 100%"
              :disabled="!prescriptionFormData.drug || getDrugStock(prescriptionFormData.drug) === 0"
            />
          </el-form-item>
          <el-form-item label="疾病/诊断">
            <el-input
              v-model="prescriptionFormData.disease_name"
              placeholder="如：流感（可选）"
              clearable
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input
              v-model="prescriptionFormData.notes"
              type="textarea"
              :rows="3"
              placeholder="请输入备注（可选）"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="prescriptionDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSubmitPrescription" :loading="prescriptionSubmitting">
              开具处方
            </el-button>
          </span>
        </template>
      </el-dialog>
      
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Document } from '@element-plus/icons-vue'
import { medicationApi, drugApi } from '../api/drugs.js'

const recordList = ref([])
const drugList = ref([])
const loading = ref(false)
const searchDrug = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const userRole = ref('doctor')
const currentUserId = ref(null)

// 单条记录对话框
const dialogVisible = ref(false)
const formRef = ref(null)
const formData = reactive({
  drug: null,
  quantity: 1,
  disease_name: '',
  notes: ''
})

// 处方对话框
const prescriptionDialogVisible = ref(false)
const prescriptionFormRef = ref(null)
const prescriptionSubmitting = ref(false)
const prescriptionFormData = reactive({
  drug: null,
  quantity: 1,
  disease_name: '',
  notes: ''
})

const rxMinQty = computed(() => {
  if (prescriptionFormData.drug && getDrugStock(prescriptionFormData.drug) > 0) return 1
  return 0
})
const rxMaxQty = computed(() => {
  const s = getDrugStock(prescriptionFormData.drug)
  return s > 0 ? s : 999999
})

// 选中的药品
const selectedDrug = computed(() => {
  return drugList.value.find(d => d.id === formData.drug)
})

// 最大可领数量
const maxQuantity = computed(() => {
  if (selectedDrug.value && selectedDrug.value.stock > 0) {
    return selectedDrug.value.stock
  }
  // 当药品未选择时，返回一个很大的值，避免 min > max 的错误
  return 999999
})

// 最小可领数量（动态调整，避免 min > max 错误）
const minQuantity = computed(() => {
  // 如果已选择药品且库存大于0，最小值为1；否则为0（允许用户先选择药品）
  if (selectedDrug.value && selectedDrug.value.stock > 0) {
    return 1
  }
  return 0
})

// 响应式对话框宽度
const dialogWidth = ref('500px')
const prescriptionDialogWidth = ref('700px')

// 更新对话框宽度
const updateDialogWidth = () => {
  if (window.innerWidth <= 768) {
    dialogWidth.value = '90%'
    prescriptionDialogWidth.value = '90%'
  } else {
    dialogWidth.value = '500px'
    prescriptionDialogWidth.value = '700px'
  }
}

// 表单验证规则
const formRules = {
  drug: [
    { required: true, message: '请选择药品', trigger: 'change' }
  ],
  quantity: [
    { required: true, message: '请输入数量', trigger: 'blur' },
    { 
      type: 'number', 
      min: 1, 
      message: '数量必须大于0', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (!selectedDrug.value) {
          callback(new Error('请先选择药品'))
        } else if (value < 1) {
          callback(new Error('数量必须大于0'))
        } else if (value > selectedDrug.value.stock) {
          callback(new Error(`数量不能超过库存（${selectedDrug.value.stock}件）`))
        } else {
          callback()
        }
      }
    }
  ]
}

const fetchRecords = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if ((searchDrug.value || '').trim()) {
      params.drug_name = searchDrug.value.trim()
    }
    
    const response = await medicationApi.getRecords(params)
    recordList.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    console.error('获取用药记录失败:', error)
    ElMessage.error('获取用药记录失败')
  } finally {
    loading.value = false
  }
}

const fetchDrugs = async () => {
  try {
    const response = await drugApi.getDrugs({ page_size: 1000 })
    drugList.value = response.data.results || []
  } catch (error) {
    console.error('获取药品列表失败:', error)
    ElMessage.warning('获取药品列表失败，请稍后重试')
  }
}

const handleAdd = () => {
  // 重置表单数据
  formData.drug = null
  formData.quantity = 0  // 初始化为0，避免 min > max 错误
  formData.disease_name = ''
  formData.notes = ''
  
  // 如果药品列表为空，尝试加载（但不阻塞对话框打开）
  if (drugList.value.length === 0) {
    fetchDrugs().catch(error => {
      console.error('加载药品列表失败:', error)
      ElMessage.warning('药品列表加载失败，请刷新页面重试')
    })
  }
  
  // 直接打开对话框
  dialogVisible.value = true
}

const handleAddPrescription = () => {
  prescriptionFormData.drug = null
  prescriptionFormData.quantity = 1
  prescriptionFormData.disease_name = ''
  prescriptionFormData.notes = ''
  
  // 如果药品列表为空，尝试加载
  if (drugList.value.length === 0) {
    fetchDrugs().catch(error => {
      console.error('加载药品列表失败:', error)
      ElMessage.warning('药品列表加载失败，请刷新页面重试')
    })
  }
  
  // 打开处方对话框
  prescriptionDialogVisible.value = true
}

const getDrugStock = (drugId) => {
  const drug = drugList.value.find(d => d.id === drugId)
  return drug ? drug.stock : 0
}

const handlePrescriptionDrugChange = () => {
  if (prescriptionFormData.drug) {
    const stock = getDrugStock(prescriptionFormData.drug)
    if (prescriptionFormData.quantity > stock) {
      prescriptionFormData.quantity = stock
    } else if (prescriptionFormData.quantity < 1) {
      prescriptionFormData.quantity = 1
    }
  }
}

const handleSubmitPrescription = async () => {
  if (!prescriptionFormData.drug || prescriptionFormData.quantity < 1) {
    ElMessage.warning('请选择药品并填写数量')
    return
  }
  const stock = getDrugStock(prescriptionFormData.drug)
  if (prescriptionFormData.quantity > stock) {
    const drug = drugList.value.find(d => d.id === prescriptionFormData.drug)
    ElMessage.error(`${drug?.name || '药品'}库存不足，当前库存：${stock}件`)
    return
  }

  prescriptionSubmitting.value = true

  try {
    const prescriptionId = `RX${Date.now()}${Math.floor(Math.random() * 1000)}`
    const dn = (prescriptionFormData.disease_name || '').trim() || null
    await medicationApi.createRecord({
      drug: prescriptionFormData.drug,
      quantity: prescriptionFormData.quantity,
      prescription_id: prescriptionId,
      disease_name: dn,
      notes: prescriptionFormData.notes || null
    })

    ElMessage.success('处方开具成功')
    prescriptionDialogVisible.value = false
    fetchRecords()
    fetchDrugs() // 刷新药品列表以更新库存
  } catch (error) {
    console.error('开具处方失败:', error)
    const errorMsg = error.response?.data
    if (typeof errorMsg === 'object') {
      const firstError = Object.values(errorMsg)[0]
      ElMessage.error(Array.isArray(firstError) ? firstError[0] : firstError)
    } else {
      ElMessage.error(errorMsg || '开具处方失败')
    }
  } finally {
    prescriptionSubmitting.value = false
  }
}

const resetPrescriptionForm = () => {
  if (prescriptionFormRef.value) {
    prescriptionFormRef.value.resetFields()
  }
  prescriptionFormData.drug = null
  prescriptionFormData.quantity = 1
  prescriptionFormData.disease_name = ''
  prescriptionFormData.notes = ''
}

const handleDrugChange = () => {
  if (selectedDrug.value) {
    // 如果选择的药品库存为0，重置数量为0
    if (selectedDrug.value.stock === 0) {
      formData.quantity = 0
    } else {
      // 如果当前数量超过库存，调整为库存值
      if (formData.quantity > selectedDrug.value.stock) {
        formData.quantity = selectedDrug.value.stock
      } else if (formData.quantity < 1) {
        // 如果数量小于1，设置为1
        formData.quantity = 1
      }
    }
  } else {
    // 如果取消选择药品，重置数量为0
    formData.quantity = 0
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await medicationApi.createRecord({
          drug: formData.drug,
          quantity: formData.quantity,
          disease_name: (formData.disease_name || '').trim() || null,
          notes: formData.notes || null
        })
        ElMessage.success('添加成功')
        dialogVisible.value = false
        fetchRecords()
        fetchDrugs() // 刷新药品列表以更新库存
      } catch (error) {
        console.error('添加失败:', error)
        const errorMsg = error.response?.data
        if (typeof errorMsg === 'object') {
          const firstError = Object.values(errorMsg)[0]
          ElMessage.error(Array.isArray(firstError) ? firstError[0] : firstError)
        } else {
          ElMessage.error(errorMsg || '添加失败')
        }
      }
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  formData.drug = null
  formData.quantity = 0  // 重置为0，避免 min > max 错误
  formData.disease_name = ''
  formData.notes = ''
}

const handleSearch = () => {
  currentPage.value = 1
  fetchRecords()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchRecords()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchRecords()
}

const canCancel = (row) => {
  if (row.status !== 'ACTIVE') return false
  if (!row.prescription_id) return false
  if (userRole.value === 'admin') return true
  if (userRole.value === 'doctor' && row.prescribed_by?.id === currentUserId.value) return true
  return false
}

const handleCancel = (row) => {
  ElMessageBox.confirm('确认撤销该处方关联的全部药品记录并回滚库存？', '撤销处方', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      try {
        await medicationApi.cancelPrescription(row.id)
        ElMessage.success('已撤销')
        fetchRecords()
        fetchDrugs()
      } catch (e) {
        const msg = e.response?.data?.error || '撤销失败'
        ElMessage.error(msg)
      }
    })
    .catch(() => {})
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除这条用药记录吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await medicationApi.deleteRecord(row.id)
      ElMessage.success('删除成功')
      fetchRecords()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const handleResize = () => {
  updateDialogWidth()
}

onMounted(() => {
  // 获取当前用户信息
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      userRole.value = user.role || 'doctor'
      currentUserId.value = user.id
    }
  } catch (e) {
    console.error('解析用户信息失败:', e)
  }
  
  updateDialogWidth()
  fetchRecords()
  fetchDrugs()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.medication-records-container {
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.card-header {
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

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }
  
  .toolbar .el-input {
    width: 100% !important;
  }
  
  .pagination {
    justify-content: center;
  }
  
  :deep(.el-pagination) {
    flex-wrap: wrap;
  }
}

.stock-info {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
