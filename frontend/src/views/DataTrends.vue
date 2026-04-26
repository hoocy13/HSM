<template>
  <div class="data-trends">
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
          @change="load"
        />
      </div>
    </el-card>
    <el-card>
      <template #header>
        <span>用药趋势（按日记录量）</span>
        <span class="hint">点击折线数据点可查看当日全部用药记录</span>
      </template>
      <div ref="lineRef" style="width: 100%; height: 380px;"></div>
    </el-card>
    <el-card style="margin-top: 20px;">
      <template #header>疾病标签统计（时间窗口内用药记录）</template>
      <div ref="diseaseRef" style="width: 100%; height: 360px;"></div>
    </el-card>
    <el-card style="margin-top: 20px;">
      <template #header>药品关联矩阵（热力图）</template>
      <div ref="heatRef" style="width: 100%; height: 480px;"></div>
    </el-card>

    <el-dialog v-model="dayDialogVisible" :title="dayDialogTitle" width="900px" destroy-on-close>
      <el-table :data="dayRecords" v-loading="dayRecordsLoading" stripe max-height="480">
        <el-table-column prop="id" label="记录ID" width="90" />
        <el-table-column prop="drug_name" label="药品" min-width="120" />
        <el-table-column prop="disease_name" label="疾病/诊断" width="120" show-overflow-tooltip />
        <el-table-column label="用户" width="100">
          <template #default="{ row }">{{ row.user?.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="70" align="center" />
        <el-table-column prop="record_time" label="记录时间" width="170">
          <template #default="{ row }">{{ formatRowTime(row.record_time) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { dashboardApi, medicationApi } from '../api/drugs.js'

const lineRef = ref(null)
const diseaseRef = ref(null)
const heatRef = ref(null)
let lineChart = null
let diseaseChart = null
let heatChart = null
const days = ref(30)

const dayDialogVisible = ref(false)
const dayDialogTitle = ref('')
const dayRecords = ref([])
const dayRecordsLoading = ref(false)

const BAR_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
]

const formatRowTime = (s) => {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN')
}

const openDayRecords = async (dateStr) => {
  dayDialogTitle.value = `${dateStr} 的用药记录`
  dayDialogVisible.value = true
  dayRecordsLoading.value = true
  dayRecords.value = []
  try {
    const { data } = await medicationApi.getRecords({
      date_from: dateStr,
      date_to: dateStr,
      dispense_status: 'dispensed',
      page_size: 500
    })
    dayRecords.value = data.results || []
  } catch (e) {
    console.error(e)
    ElMessage.error('加载当日记录失败')
  } finally {
    dayRecordsLoading.value = false
  }
}

const bindLineClick = () => {
  if (!lineChart) return
  lineChart.off('click')
  lineChart.on('click', (params) => {
    const dateStr = params?.name
    if (dateStr && typeof dateStr === 'string') {
      openDayRecords(dateStr)
    }
  })
}

const load = async () => {
  try {
    const { data } = await dashboardApi.getTrends({ days: days.value })
    const trend = data.prescription_trend || []
    const diseaseTrend = data.disease_trend || []
    const dm = data.drug_matrix || { labels: [], matrix: [] }

    if (lineRef.value) {
      if (!lineChart) lineChart = echarts.init(lineRef.value)
      lineChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: trend.map((t) => t.date),
          axisLabel: { rotate: 45 }
        },
        yAxis: { type: 'value', name: '记录条数' },
        series: [
          {
            name: '用药记录数',
            type: 'line',
            smooth: true,
            data: trend.map((t) => t.count),
            areaStyle: { opacity: 0.15 },
            itemStyle: { color: '#409EFF' }
          }
        ]
      })
      bindLineClick()
    }

    if (diseaseRef.value) {
      if (!diseaseChart) diseaseChart = echarts.init(diseaseRef.value)
      const dlist = diseaseTrend.filter((x) => x.disease && x.count > 0)
      diseaseChart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 80, right: 40, top: 40, bottom: 80 },
        xAxis: {
          type: 'category',
          data: dlist.map((x) => x.disease),
          axisLabel: { rotate: 40, interval: 0 }
        },
        yAxis: { type: 'value', name: '记录数' },
        series: [
          {
            name: '记录数',
            type: 'bar',
            data: dlist.map((x, i) => ({
              value: x.count,
              itemStyle: { color: BAR_COLORS[i % BAR_COLORS.length] }
            }))
          }
        ]
      })
    }

    const labels = dm.labels || []
    const matrix = dm.matrix || []
    if (heatRef.value && labels.length) {
      if (!heatChart) heatChart = echarts.init(heatRef.value)
      const n = labels.length
      const data = []
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          const v = matrix[i] && matrix[i][j] !== undefined ? matrix[i][j] : 0
          data.push([j, i, v])
        }
      }
      heatChart.setOption({
        tooltip: {
          position: 'top',
          formatter: (p) => {
            const x = labels[p.data[0]]
            const y = labels[p.data[1]]
            return `${y} × ${x}<br/>共现: ${p.data[2]}`
          }
        },
        grid: { left: 120, top: 80, right: 40, bottom: 80 },
        xAxis: {
          type: 'category',
          data: labels,
          splitArea: { show: true },
          axisLabel: { rotate: 45, interval: 0, fontSize: 10 }
        },
        yAxis: {
          type: 'category',
          data: labels,
          splitArea: { show: true },
          axisLabel: { fontSize: 10 }
        },
        visualMap: {
          min: 0,
          max: Math.max(1, ...data.map((d) => d[2])),
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: 10,
          inRange: { color: ['#ebedf0', '#196127'] }
        },
        series: [
          {
            name: '共现',
            type: 'heatmap',
            data,
            label: { show: false },
            emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } }
          }
        ]
      })
    } else if (heatRef.value) {
      if (!heatChart) heatChart = echarts.init(heatRef.value)
      heatChart.setOption({
        title: {
          text: '暂无足够数据生成矩阵',
          left: 'center',
          top: 'center',
          textStyle: { color: '#909399' }
        }
      })
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载趋势数据失败')
  }
}

const onResize = () => {
  lineChart?.resize()
  diseaseChart?.resize()
  heatChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  lineChart?.dispose()
  diseaseChart?.dispose()
  heatChart?.dispose()
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
.hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}
</style>
