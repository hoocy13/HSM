<template>
  <div>
    <el-card>
      <template #header>入库记录</template>
      <p class="hint">含「药品入库」及正数库存调整流水。</p>
      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="drug_name" label="药品" />
        <el-table-column prop="quantity_change" label="数量" width="100" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a">+{{ row.quantity_change }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" />
        <el-table-column prop="created_by_name" label="操作人" width="120" />
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi } from '../api/drugs.js'

const rows = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formatDate = (s) => (s ? new Date(s).toLocaleString('zh-CN') : '-')

const load = async () => {
  loading.value = true
  try {
    const { data } = await inventoryApi.list({
      page: page.value,
      page_size: pageSize.value,
      only_in: 1
    })
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
.hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 12px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
