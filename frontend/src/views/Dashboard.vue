<template>
  <div class="dashboard-container">
    <!-- 今日核心指标 -->
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

    <!-- 消耗趋势预测 -->
    <el-card class="chart-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>消耗趋势预测</span>
        </div>
      </template>
      <div ref="trendChartRef" style="width: 100%; height: 400px;"></div>
    </el-card>

    <!-- 药品关联矩阵 -->
    <el-card class="chart-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>药品关联矩阵</span>
          <span class="subtitle">（显示经常一起开出的药品组合）</span>
        </div>
      </template>
      <div ref="correlationChartRef" style="width: 100%; height: 500px;"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Wallet, Document, Warning, DataLine } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { dashboardApi } from '../api/drugs.js'

// 统计数据
const stats = ref([
  { key: 'total_amount', label: '总金额', value: '¥0', icon: 'Wallet', type: 'primary' },
  { key: 'pending_prescriptions', label: '待发药处方', value: '0', icon: 'Document', type: 'success' },
  { key: 'today_warnings', label: '今日新增预警', value: '0', icon: 'Warning', type: 'warning' },
  { key: 'turnover_rate', label: '周转率', value: '0%', icon: 'DataLine', type: 'info' }
])

// 图表引用
const trendChartRef = ref(null)
const correlationChartRef = ref(null)
let trendChart = null
let correlationChart = null

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await dashboardApi.getStats()
    const data = response.data
    
    stats.value[0].value = `¥${data.total_amount.toLocaleString()}`
    stats.value[1].value = data.pending_prescriptions.toString()
    stats.value[2].value = data.today_warnings.toString()
    stats.value[3].value = `${data.turnover_rate}%`
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

// 加载消耗趋势数据
const loadTrendChart = async () => {
  try {
    const response = await dashboardApi.getConsumptionTrend()
    const data = response.data
    
    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }
    
    const option = {
      title: {
        text: '药品消耗趋势与预测',
        left: 'center',
        textStyle: {
          fontSize: 16
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['实际消耗', '预测消耗'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: [...data.dates, ...data.forecast_dates],
        axisLabel: {
          rotate: 45,
          formatter: (value) => {
            // 只显示日期部分
            return value.split(' ')[0]
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '消耗量（件）'
      },
      series: [
        {
          name: '实际消耗',
          type: 'line',
          smooth: true,
          areaStyle: {
            opacity: 0.3
          },
          data: [...data.actual, ...new Array(data.forecast_dates.length).fill(null)],
          itemStyle: {
            color: '#409EFF'
          }
        },
        {
          name: '预测消耗',
          type: 'line',
          smooth: true,
          lineStyle: {
            type: 'dashed'
          },
          data: [...new Array(data.dates.length).fill(null), ...data.forecast],
          itemStyle: {
            color: '#F56C6C'
          }
        }
      ]
    }
    
    trendChart.setOption(option)
    
    // 响应式调整
    window.addEventListener('resize', () => {
      trendChart?.resize()
    })
  } catch (error) {
    console.error('加载趋势数据失败:', error)
    ElMessage.error('加载趋势数据失败')
  }
}

// 加载药品关联矩阵数据
const loadCorrelationChart = async () => {
  try {
    const response = await dashboardApi.getDrugCorrelation()
    const data = response.data.correlations
    
    if (!correlationChart) {
      correlationChart = echarts.init(correlationChartRef.value)
    }
    
    if (data.length === 0) {
      correlationChart.setOption({
        title: {
          text: '暂无药品关联数据',
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 16,
            color: '#909399'
          }
        }
      })
      return
    }
    
    // 构建节点和边数据
    const nodes = []
    const edges = []
    const drugSet = new Set()
    
    // 收集所有药品
    data.forEach(item => {
      if (!drugSet.has(item.drug1)) {
        nodes.push({
          id: item.drug1_id,
          name: item.drug1,
          symbolSize: 30,
          category: 0
        })
        drugSet.add(item.drug1)
      }
      if (!drugSet.has(item.drug2)) {
        nodes.push({
          id: item.drug2_id,
          name: item.drug2,
          symbolSize: 30,
          category: 0
        })
        drugSet.add(item.drug2)
      }
    })
    
    // 构建边（关联关系）
    data.forEach(item => {
      edges.push({
        source: item.drug1_id,
        target: item.drug2_id,
        value: item.count,
        label: {
          show: true,
          formatter: `${item.count}次`
        }
      })
    })
    
    const option = {
      title: {
        text: '药品关联关系图',
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          if (params.dataType === 'node') {
            return `${params.data.name}<br/>共现次数: ${params.data.value || 0}`
          } else {
            return `${params.data.source} ↔ ${params.data.target}<br/>共现次数: ${params.data.value}`
          }
        }
      },
      legend: {
        show: false
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: edges,
          categories: [{ name: '药品' }],
          roam: true,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}'
          },
          labelLayout: {
            hideOverlap: true
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3,
            width: (params) => {
              return params.data.value * 2
            }
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4
            }
          },
          force: {
            repulsion: 1000,
            gravity: 0.1,
            edgeLength: 200
          }
        }
      ]
    }
    
    correlationChart.setOption(option)
    
    // 响应式调整
    window.addEventListener('resize', () => {
      correlationChart?.resize()
    })
  } catch (error) {
    console.error('加载关联数据失败:', error)
    ElMessage.error('加载关联数据失败')
  }
}

// 初始化所有数据
const initDashboard = async () => {
  await loadStats()
  await nextTick()
  await loadTrendChart()
  await loadCorrelationChart()
}

onMounted(() => {
  initDashboard()
})

onUnmounted(() => {
  if (trendChart) {
    trendChart.dispose()
  }
  if (correlationChart) {
    correlationChart.dispose()
  }
})
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 120px;
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-card.primary {
  border-left: 4px solid #409EFF;
}

.stat-card.success {
  border-left: 4px solid #67C23A;
}

.stat-card.warning {
  border-left: 4px solid #E6A23C;
}

.stat-card.info {
  border-left: 4px solid #909399;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.stat-icon {
  flex-shrink: 0;
  margin-right: 20px;
  color: #409EFF;
}

.stat-card.success .stat-icon {
  color: #67C23A;
}

.stat-card.warning .stat-icon {
  color: #E6A23C;
}

.stat-card.info .stat-icon {
  color: #909399;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.chart-card {
  width: 100%;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subtitle {
  font-size: 12px;
  font-weight: normal;
  color: #909399;
}

@media (max-width: 768px) {
  .stat-card {
    height: 100px;
    margin-bottom: 10px;
  }
  
  .stat-value {
    font-size: 24px;
  }
  
  .stat-icon {
    margin-right: 10px;
  }
  
  .stat-icon :deep(svg) {
    width: 30px !important;
    height: 30px !important;
  }
}
</style>
