<template>
  <el-card>
    <template #header>操作审计</template>
    <div class="toolbar">
      <el-select v-model="filterAction" placeholder="行为类型" clearable style="width: 200px">
        <el-option label="开具处方" value="CREATE_PRESCRIPTION" />
        <el-option label="撤销处方" value="CANCEL_PRESCRIPTION" />
        <el-option label="入库" value="STOCK_IN" />
        <el-option label="库存调整" value="INVENTORY_ADJUST" />
        <el-option label="更新药品" value="UPDATE_DRUG" />
        <el-option label="创建用户" value="CREATE_USER" />
        <el-option label="变更角色" value="UPDATE_USER_ROLE" />
        <el-option label="发布公告" value="CREATE_ANNOUNCEMENT" />
        <el-option label="更新公告" value="UPDATE_ANNOUNCEMENT" />
        <el-option label="删除公告" value="DELETE_ANNOUNCEMENT" />
        <el-option label="审批发药" value="APPROVE_DISPENSE" />
        <el-option label="拒绝待发药" value="REJECT_DISPENSE" />
      </el-select>
      <el-input v-model="filterUserId" placeholder="用户名或用户ID" clearable style="width: 200px" />
      <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column prop="id" label="记录编号" width="100" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="action_type" label="行为" width="160" />
      <el-table-column prop="target_type" label="对象类型" width="100" />
      <el-table-column prop="target_id" label="对象ID" width="80" />
      <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
    </el-table>
    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { operationLogApi } from '../api/drugs.js'

const rows = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterAction = ref('')
const filterUserId = ref('')
const dateRange = ref(null)

const formatDate = (s) => (s ? new Date(s).toLocaleString('zh-CN') : '-')

const load = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterAction.value) params.action_type = filterAction.value
    if (filterUserId.value) params.user_id = filterUserId.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const { data } = await operationLogApi.list(params)
    rows.value = data.results || []
    total.value = data.count ?? 0
  } catch (e) {
    console.error(e)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
