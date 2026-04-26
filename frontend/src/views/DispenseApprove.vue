<template>
  <div class="dispense-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审批发药</span>
          <span class="sub">核对记录 ID、患者用户 ID 与系统一致后，同意发药将扣减库存。</span>
        </div>
      </template>

      <div class="toolbar">
        <el-button type="primary" :loading="loading" @click="load">刷新</el-button>
        <template v-if="activeTab === 'approved'">
          <el-input
            v-model="approvedFilters.userId"
            placeholder="患者用户ID"
            clearable
            style="width: 140px"
            @input="loadApproved"
          />
          <el-input
            v-model="approvedFilters.drugName"
            placeholder="药品名"
            clearable
            style="width: 180px"
            @input="loadApproved"
          />
          <el-input
            v-model="approvedFilters.approver"
            placeholder="审批人"
            clearable
            style="width: 160px"
            @input="loadApproved"
          />
          <el-date-picker
            v-model="approvedFilters.approvedRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="审批开始"
            end-placeholder="审批结束"
            clearable
            @change="loadApproved"
          />
          <el-button @click="resetApprovedFilters">重置筛选</el-button>
        </template>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="待审批发药" name="pending" />
        <el-tab-pane label="已审批记录" name="approved" />
      </el-tabs>

      <el-table v-if="activeTab === 'pending'" :data="rows" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="记录ID" width="90" />
        <el-table-column label="患者用户ID" width="110" align="center">
          <template #default="{ row }">{{ row.user?.id ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="患者" width="120">
          <template #default="{ row }">{{ row.user?.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="drug_name" label="药品" min-width="140" />
        <el-table-column prop="quantity" label="数量" width="70" align="center" />
        <el-table-column prop="prescription_id" label="处方号" width="160" show-overflow-tooltip />
        <el-table-column prop="record_time" label="开具时间" width="170">
          <template #default="{ row }">{{ formatDate(row.record_time) }}</template>
        </el-table-column>
        <el-table-column label="核对ID" width="140" align="center">
          <template #default="{ row }">
            <el-input
              v-model="confirmIds[row.id]"
              size="small"
              placeholder="填患者用户ID"
              style="width: 120px"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" :loading="row._agree" @click="agree(row)">同意发药</el-button>
            <el-button type="danger" size="small" plain :loading="row._reject" @click="reject(row)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else :data="approvedRows" v-loading="loadingApproved" stripe style="width: 100%; margin-top: 8px;">
        <el-table-column prop="id" label="记录ID" width="90" />
        <el-table-column label="患者用户ID" width="110" align="center">
          <template #default="{ row }">{{ row.user?.id ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="患者" width="120">
          <template #default="{ row }">{{ row.user?.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="drug_name" label="药品" min-width="140" />
        <el-table-column prop="quantity" label="数量" width="70" align="center" />
        <el-table-column prop="prescription_id" label="处方号" width="160" show-overflow-tooltip />
        <el-table-column prop="record_time" label="开具时间" width="170">
          <template #default="{ row }">{{ formatDate(row.record_time) }}</template>
        </el-table-column>
        <el-table-column prop="dispensed_at" label="审批时间" width="170">
          <template #default="{ row }">{{ formatDate(row.dispensed_at) }}</template>
        </el-table-column>
        <el-table-column label="审批人" width="110">
          <template #default="{ row }">{{ row.dispensed_by?.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="warning" size="small" plain :loading="row._undo" @click="undo(row)">撤销发药</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { medicationApi } from '../api/drugs.js'

const rows = ref([])
const loading = ref(false)
const approvedRows = ref([])
const loadingApproved = ref(false)
const activeTab = ref('pending')
const confirmIds = reactive({})
const approvedFilters = reactive({
  userId: '',
  drugName: '',
  approver: '',
  approvedRange: null
})

const formatDate = (s) => (s ? new Date(s).toLocaleString('zh-CN') : '-')

const loadPending = async () => {
  loading.value = true
  try {
    const { data } = await medicationApi.getRecords({
      dispense_status: 'pending',
      page_size: 200,
      page: 1
    })
    const list = data.results || []
    list.forEach((r) => {
      if (confirmIds[r.id] === undefined) confirmIds[r.id] = String(r.user?.id ?? '')
    })
    rows.value = list.map((r) => ({ ...r, _agree: false, _reject: false }))
  } catch (e) {
    console.error(e)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const loadApproved = async () => {
  loadingApproved.value = true
  try {
    const params = {
      dispense_status: 'dispensed',
      page_size: 200,
      page: 1
    }
    if ((approvedFilters.userId || '').trim()) params.user = approvedFilters.userId.trim()
    if ((approvedFilters.drugName || '').trim()) params.drug_name = approvedFilters.drugName.trim()
    if ((approvedFilters.approver || '').trim()) params.dispensed_by = approvedFilters.approver.trim()
    if (approvedFilters.approvedRange && approvedFilters.approvedRange.length === 2) {
      params.dispensed_from = approvedFilters.approvedRange[0]
      params.dispensed_to = approvedFilters.approvedRange[1]
    }
    const { data } = await medicationApi.getRecords(params)
    const list = data.results || []
    approvedRows.value = list.map((r) => ({ ...r, _undo: false }))
  } catch (e) {
    console.error(e)
    ElMessage.error('加载已审批记录失败')
  } finally {
    loadingApproved.value = false
  }
}

const resetApprovedFilters = async () => {
  approvedFilters.userId = ''
  approvedFilters.drugName = ''
  approvedFilters.approver = ''
  approvedFilters.approvedRange = null
  await loadApproved()
}

const load = async () => {
  await Promise.all([loadPending(), loadApproved()])
}

const agree = async (row) => {
  const raw = (confirmIds[row.id] ?? '').toString().trim()
  if (!raw) {
    ElMessage.warning('请填写患者用户ID以核对')
    return
  }
  if (raw !== String(row.user?.id ?? '')) {
    ElMessage.error('填写的用户ID与处方患者不一致')
    return
  }
  row._agree = true
  try {
    await medicationApi.dispense(row.id, { confirm_user_id: parseInt(raw, 10) })
    ElMessage.success('已发药并扣减库存')
    await load()
  } catch (e) {
    const msg = e.response?.data?.error || e.response?.data?.confirm_user_id?.[0] || '发药失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    row._agree = false
  }
}

const reject = async (row) => {
  try {
    await ElMessageBox.confirm('拒绝后该处方作废，不扣库存。确定？', '拒绝待发药', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  row._reject = true
  try {
    await medicationApi.rejectPending(row.id)
    ElMessage.success('已拒绝')
    await load()
  } catch (e) {
    const msg = e.response?.data?.error || '操作失败'
    ElMessage.error(msg)
  } finally {
    row._reject = false
  }
}

const undo = async (row) => {
  try {
    await ElMessageBox.confirm(
      '撤销发药后会回补库存，并将该记录重新变为待审批。确定继续？',
      '撤销发药',
      {
        type: 'warning',
        confirmButtonText: '确定撤销',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }
  row._undo = true
  try {
    await medicationApi.undoDispense(row.id)
    ElMessage.success('已撤销发药，记录回到待审批')
    await load()
    activeTab.value = 'pending'
  } catch (e) {
    const msg = e.response?.data?.error || '撤销发药失败'
    ElMessage.error(msg)
  } finally {
    row._undo = false
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.dispense-page {
  width: 100%;
}
.card-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-weight: bold;
}
.sub {
  font-weight: normal;
  font-size: 13px;
  color: #909399;
}
.toolbar {
  margin-bottom: 12px;
}
</style>
