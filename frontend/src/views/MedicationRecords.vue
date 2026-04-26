<template>
  <div class="medication-records-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用药记录</span>
        </div>
      </template>
      
      <div class="toolbar">
        <div class="toolbar-filters">
          <el-select
            v-model="filterPatientId"
            placeholder="患者（全部）"
            clearable
            filterable
            style="width: 220px"
            @clear="applyFilters"
            @change="applyFilters"
          >
            <el-option
              v-for="u in departmentUsers"
              :key="u.id"
              :label="`${u.username}（ID:${u.id}）`"
              :value="u.id"
            />
          </el-select>
          <el-date-picker
            v-model="recordDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="记录开始日期"
            end-placeholder="记录结束日期"
            value-format="YYYY-MM-DD"
            unlink-panels
            clearable
            style="width: 280px"
            @change="applyFilters"
          />
          <el-input
            v-model="searchDrug"
            placeholder="搜索药品名称"
            style="width: 220px"
            clearable
            @input="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
        <div class="toolbar-actions">
          <el-button
            v-if="userRole === 'doctor'"
            type="primary"
            :icon="Document"
            @click="handleAddPrescription"
          >
            开具处方
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
        <el-table-column prop="drug_name" label="药品名称" />
        <el-table-column prop="disease_name" label="疾病/诊断" width="120">
          <template #default="{ row }">
            {{ row.disease_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="患者" width="160">
          <template #default="{ row }">
            <span>{{ row.user?.username || '-' }}</span>
            <span class="uid-hint"> (ID:{{ row.user?.id ?? '-' }})</span>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="100" align="center" />
        <el-table-column prop="record_time" label="记录时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.record_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" show-overflow-tooltip />
        <el-table-column label="发药" width="100" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'CANCELLED'">—</template>
            <el-tag v-else-if="row.dispense_status === 'pending'" type="warning" size="small">待发药</el-tag>
            <el-tag v-else type="success" size="small">已发药</el-tag>
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
          <el-form-item label="患者" required>
            <el-select
              v-model="prescriptionFormData.patient_user_id"
              placeholder="选择患者（本科室用户）"
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="u in departmentUsers"
                :key="u.id"
                :label="`${u.username}（ID:${u.id}）`"
                :value="u.id"
              />
            </el-select>
            <div class="stock-info">请核对患者系统用户 ID，药剂师发药时将再次核对。</div>
          </el-form-item>
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
import { Search, Document } from '@element-plus/icons-vue'
import { medicationApi, drugApi } from '../api/drugs.js'

const recordList = ref([])
const drugList = ref([])
const loading = ref(false)
const searchDrug = ref('')
const filterPatientId = ref(null)
const recordDateRange = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const userRole = ref('doctor')
const currentUserId = ref(null)

// 处方对话框
const prescriptionDialogVisible = ref(false)
const prescriptionFormRef = ref(null)
const prescriptionSubmitting = ref(false)
const departmentUsers = ref([])
const prescriptionFormData = reactive({
  patient_user_id: null,
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

const prescriptionDialogWidth = ref('700px')

const updateDialogWidth = () => {
  if (window.innerWidth <= 768) {
    prescriptionDialogWidth.value = '90%'
  } else {
    prescriptionDialogWidth.value = '700px'
  }
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
    if (filterPatientId.value != null && filterPatientId.value !== '') {
      params.user = filterPatientId.value
    }
    if (recordDateRange.value && recordDateRange.value.length === 2) {
      params.date_from = recordDateRange.value[0]
      params.date_to = recordDateRange.value[1]
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

const loadDepartmentUsers = async () => {
  try {
    const { data } = await medicationApi.departmentUsers()
    departmentUsers.value = data.results || []
  } catch (e) {
    console.error(e)
    departmentUsers.value = []
    ElMessage.warning('加载本科室用户列表失败')
  }
}

const handleAddPrescription = () => {
  prescriptionFormData.patient_user_id = null
  prescriptionFormData.drug = null
  prescriptionFormData.quantity = 1
  prescriptionFormData.disease_name = ''
  prescriptionFormData.notes = ''

  loadDepartmentUsers()
  if (drugList.value.length === 0) {
    fetchDrugs().catch((error) => {
      console.error('加载药品列表失败:', error)
      ElMessage.warning('药品列表加载失败，请刷新页面重试')
    })
  }

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
  if (!prescriptionFormData.patient_user_id) {
    ElMessage.warning('请选择患者')
    return
  }
  if (!prescriptionFormData.drug || prescriptionFormData.quantity < 1) {
    ElMessage.warning('请选择药品并填写数量')
    return
  }
  const stock = getDrugStock(prescriptionFormData.drug)
  if (prescriptionFormData.quantity > stock) {
    const drug = drugList.value.find((d) => d.id === prescriptionFormData.drug)
    ElMessage.error(`${drug?.name || '药品'}库存不足，当前库存：${stock}件`)
    return
  }

  prescriptionSubmitting.value = true

  try {
    const prescriptionId = `RX${Date.now()}${Math.floor(Math.random() * 1000)}`
    const dn = (prescriptionFormData.disease_name || '').trim() || null
    await medicationApi.createRecord({
      patient_user_id: prescriptionFormData.patient_user_id,
      drug: prescriptionFormData.drug,
      quantity: prescriptionFormData.quantity,
      prescription_id: prescriptionId,
      disease_name: dn,
      notes: prescriptionFormData.notes || null
    })

    ElMessage.success('处方已开具（待发药，库存将在药剂师发药后扣减）')
    prescriptionDialogVisible.value = false
    currentPage.value = 1
    fetchRecords()
    fetchDrugs()
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
  prescriptionFormData.patient_user_id = null
  prescriptionFormData.drug = null
  prescriptionFormData.quantity = 1
  prescriptionFormData.disease_name = ''
  prescriptionFormData.notes = ''
}

const handleSearch = () => {
  currentPage.value = 1
  fetchRecords()
}

const applyFilters = () => {
  currentPage.value = 1
  fetchRecords()
}

const resetFilters = () => {
  filterPatientId.value = null
  recordDateRange.value = null
  searchDrug.value = ''
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
  const stockHint =
    row.dispense_status === 'pending'
      ? '该处方尚未发药，撤销不涉及库存。'
      : '已发药记录将回滚药品库存。'
  ElMessageBox.confirm(`确认撤销该处方？${stockHint}`, '撤销处方', {
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
  if (userRole.value === 'doctor') {
    loadDepartmentUsers()
  }
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
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-filters .el-select,
  .toolbar-filters .el-date-editor,
  .toolbar-filters .el-input {
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

.uid-hint {
  font-size: 12px;
  color: #909399;
}
</style>
