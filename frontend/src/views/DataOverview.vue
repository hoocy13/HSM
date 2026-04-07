<template>
  <div class="data-overview">
    <el-card class="filter-card" style="margin-bottom: 12px;">
      <div class="filter-row">
        <div class="filter-title">时间窗口</div>
        <el-segmented
          v-model="days"
          :options="[
            { label: '近7天', value: 7 },
            { label: '近30天', value: 30 },
            { label: '近90天', value: 90 }
          ]"
          @change="loadStats"
        />
      </div>
    </el-card>
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="stat in stats" :key="stat.key">
        <el-card class="stat-card" :class="stat.type">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="40">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-value">{{ stat.value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="chart-card" style="margin-top: 20px;">
      <template #header>
        <span>库存紧缺 Top 10</span>
      </template>
      <el-table :data="lowStockData" style="width: 100%" stripe>
        <el-table-column type="index" label="排名" width="60" align="center" />
        <el-table-column prop="name" label="药品名称" min-width="150" />
        <el-table-column prop="stock" label="当前库存" width="100" align="center" />
        <el-table-column prop="safety_stock" label="安全库存" width="100" align="center" />
        <el-table-column prop="gap_percentage" label="缺口程度" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'high' ? 'danger' : row.severity === 'medium' ? 'warning' : 'info'" size="small">
              {{ row.gap_percentage }}%
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Goods, Warning, Bell } from '@element-plus/icons-vue'
import { dashboardApi } from '../api/drugs.js'

const days = ref(30)
const stats = ref([
  { key: 'total_medication_count', label: '用药总次数', value: '0', icon: Document, type: 'primary' },
  { key: 'active_drug_count', label: '活跃药品数量', value: '0', icon: Goods, type: 'success' },
  { key: 'low_stock_count', label: '低库存数量', value: '0', icon: Warning, type: 'warning' },
  { key: 'warning_count', label: '预警数量', value: '0', icon: Bell, type: 'info' }
])

const lowStockData = ref([])

const loadStats = async () => {
  try {
    const { data } = await dashboardApi.getStats({ days: days.value })
    stats.value[0].value = String(data.total_medication_count ?? 0)
    stats.value[1].value = String(data.active_drug_count ?? 0)
    stats.value[2].value = String(data.low_stock_count ?? 0)
    stats.value[3].value = String(data.warning_count ?? 0)
  } catch (e) {
    console.error(e)
    ElMessage.error('加载数据概览失败')
  }
}

const loadLow = async () => {
  try {
    const { data } = await dashboardApi.getLowStockTop10()
    lowStockData.value = data.results || []
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  loadStats()
  loadLow()
})
</script>

<style scoped>
.filter-card :deep(.el-card__body) {
  padding: 10px 12px;
}
.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.filter-title {
  font-weight: 600;
  color: #303133;
}
.stat-card {
  margin-bottom: 12px;
}
.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-label {
  color: #909399;
  font-size: 14px;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
}
.chart-card {
  width: 100%;
}
</style>
