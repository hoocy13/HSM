<template>
  <div class="warnings-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>智能预警</span>
          <el-button type="primary" @click="refreshWarnings">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-alert
        title="智能预警说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #default>
          <p>系统采用动态阈值算法，自动检测以下情况：</p>
          <ul>
            <li><strong>有效期预警：</strong>有效期少于30天的药品</li>
            <li><strong>库存预警：</strong>根据过去30天的平均消耗量，自动计算安全库存天数（默认7天），当前库存低于安全库存时触发预警</li>
            <li><strong>建议采购量：</strong>系统自动计算建议采购量 = 安全库存 - 当前库存 + 缓冲（安全库存的20%）</li>
          </ul>
        </template>
      </el-alert>
      
      <div class="table-wrapper">
        <el-table
          :data="warningDrugs"
          v-loading="loading"
          style="width: 100%"
          stripe
          :row-class-name="getRowClassName"
        >
        <el-table-column prop="id" label="ID" width="80" />
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
            <div v-if="row.warning_reasons && row.warning_reasons.length > 0">
              <el-tag v-for="reason in row.warning_reasons" :key="reason" 
                :type="reason === '即将过期' ? 'danger' : 'warning'" 
                size="small" 
                style="margin-right: 5px; margin-bottom: 5px">
                {{ reason }}
              </el-tag>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="安全库存" width="120" align="center">
          <template #default="{ row }">
            <span>{{ row.safety_stock || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日均消耗" width="120" align="center">
          <template #default="{ row }">
            <span>{{ row.avg_daily_consumption !== undefined ? row.avg_daily_consumption : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="建议采购量" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.suggested_purchase > 0" type="success" size="small">
              {{ row.suggested_purchase }}件
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
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
          </template>
        </el-table-column>
        </el-table>
      </div>
      
      <div v-if="warningDrugs.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无预警药品" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { drugApi } from '../api/drugs.js'
import { useRouter } from 'vue-router'

const router = useRouter()
const warningDrugs = ref([])
const loading = ref(false)

const fetchWarnings = async () => {
  loading.value = true
  try {
    const response = await drugApi.getWarnings()
    warningDrugs.value = response.data.results || []
  } catch (error) {
    console.error('获取预警药品失败:', error)
    ElMessage.error('获取预警药品失败')
  } finally {
    loading.value = false
  }
}

const refreshWarnings = () => {
  fetchWarnings()
}

const handleStockIn = (row) => {
  router.push({ path: '/layout/drugs', query: { action: 'stockIn', id: row.id } })
}

const handleEdit = (row) => {
  router.push({ path: '/layout/drugs', query: { action: 'edit', id: row.id } })
}

const formatDateOnly = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

const getStockTagType = (stock) => {
  if (stock < 50) return 'danger'
  if (stock < 100) return 'warning'
  return 'success'
}

const getRowClassName = ({ row }) => {
  if (row.is_expiring_soon || row.is_low_stock) {
    return 'warning-row'
  }
  return ''
}

onMounted(() => {
  fetchWarnings()
})
</script>

<style scoped>
.warnings-container {
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

.warning-text {
  color: #f56c6c;
  font-weight: bold;
}

.empty-state {
  margin-top: 40px;
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
}
</style>

<style>
.el-table .warning-row {
  background-color: #fef0f0 !important;
}

.el-table .warning-row:hover {
  background-color: #fde2e2 !important;
}
</style>
