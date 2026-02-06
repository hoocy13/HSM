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

    <!-- 库存紧缺Top10 -->
    <el-card class="chart-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>库存紧缺 Top 10</span>
        </div>
      </template>
      <el-table :data="lowStockData" style="width: 100%" stripe>
        <el-table-column type="index" label="排名" width="60" align="center" />
        <el-table-column prop="name" label="药品名称" min-width="150" />
        <el-table-column prop="stock" label="当前库存" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.severity === 'high' ? '#F56C6C' : row.severity === 'medium' ? '#E6A23C' : '#FFD700' }">
              {{ row.stock }}件
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="safety_stock" label="安全库存" width="100" align="center" />
        <el-table-column prop="gap_percentage" label="缺口程度" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'high' ? 'danger' : row.severity === 'medium' ? 'warning' : 'info'" size="small">
              {{ row.gap_percentage }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="suggested_purchase" label="建议采购" width="100" align="center">
          <template #default="{ row }">
            <span style="color: #409EFF; font-weight: bold;">{{ row.suggested_purchase }}件</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 过期预警分布 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>过期预警分布图</span>
            </div>
          </template>
          <div ref="expiryChartRef" style="width: 100%; height: 400px;"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>经常一起被开出的药品 Top 5</span>
            </div>
          </template>
          <div ref="top5ChartRef" style="width: 100%; height: 400px;"></div>
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
const expiryChartRef = ref(null)
const top5ChartRef = ref(null)
let trendChart = null
let correlationChart = null
let expiryChart = null
let top5Chart = null

// 库存紧缺数据
const lowStockData = ref([])

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

// 加载药品关联矩阵数据（关系图）
const loadCorrelationChart = async () => {
  try {
    const response = await dashboardApi.getDrugCorrelation()
    const data = response.data
    
    if (!correlationChart) {
      correlationChart = echarts.init(correlationChartRef.value)
    }
    
    // 检查新格式（nodes和links）
    if (data.nodes && data.links) {
      if (data.nodes.length === 0) {
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
              return `${params.data.name}<br/>总消耗: ${params.data.value || 0}件`
            } else {
              const link = params.data
              return `${link.source} ↔ ${link.target}<br/>共现次数: ${link.value}次<br/>${link.clinical_advice ? `<span style="color: #F56C6C;">临床建议: ${link.clinical_advice}</span>` : ''}`
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
            data: data.nodes.map(node => ({
              id: node.id,
              name: node.name,
              value: node.value || node.symbolSize || 30,
              symbolSize: node.symbolSize || 30,
              category: 0
            })),
            links: data.links.map(link => ({
              source: link.source,
              target: link.target,
              value: link.value,
              lineStyle: link.lineStyle || { width: 2 },
              label: link.label
            })),
            categories: [{ name: '药品' }],
            roam: true,
            label: {
              show: true,
              position: 'right',
              formatter: '{b}',
              fontSize: 12
            },
            labelLayout: {
              hideOverlap: true
            },
            lineStyle: {
              color: '#409EFF',
              curveness: 0.3,
              width: (params) => {
                // 使用links中的lineStyle.width
                return params.data.lineStyle?.width || 2
              }
            },
            emphasis: {
              focus: 'adjacency',
              lineStyle: {
                width: 6
              }
            },
            force: {
              repulsion: 1000,
              gravity: 0.1,
              edgeLength: 200,
              layoutAnimation: true
            }
          }
        ]
      }
      
      correlationChart.setOption(option)
    } else {
      // 兼容旧格式
      const correlations = data.correlations || []
      
      if (correlations.length === 0) {
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
      
      correlations.forEach(item => {
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
      
      correlations.forEach(item => {
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
    }
    
    // 响应式调整
    window.addEventListener('resize', () => {
      correlationChart?.resize()
    })
  } catch (error) {
    console.error('加载关联数据失败:', error)
    ElMessage.error('加载关联数据失败')
  }
}

// 加载库存紧缺Top10
const loadLowStockChart = async () => {
  try {
    const response = await dashboardApi.getLowStockTop10()
    const data = response.data.results || []
    lowStockData.value = data
  } catch (error) {
    console.error('加载库存紧缺数据失败:', error)
    ElMessage.error('加载库存紧缺数据失败')
    lowStockData.value = []
  }
}

// 加载过期预警分布（饼图）
const loadExpiryChart = async () => {
  try {
    const response = await dashboardApi.getExpiryDistribution()
    const data = response.data
    
    if (!expiryChart) {
      expiryChart = echarts.init(expiryChartRef.value)
    }
    
    // 提取数据（兼容新旧格式）
    let expired = 0
    let expiring_soon = 0
    let safe = 0
    
    if (data.summary) {
      expired = data.summary.expired || 0
      expiring_soon = data.summary.expiring_soon || 0
      safe = data.summary.safe || 0
    } else if (data.data && data.data.length > 0) {
      // 从旭日图格式中提取
      data.data.forEach(statusItem => {
        const statusName = statusItem.name
        const value = statusItem.value || 0
        if (statusName === '已过期') {
          expired = value
        } else if (statusName === '快过期') {
          expiring_soon = value
        } else if (statusName === '安全') {
          safe = value
        }
      })
    } else {
      expired = data.expired || 0
      expiring_soon = data.expiring_soon || 0
      safe = data.safe || 0
    }
    
    const option = {
      title: {
        text: '药品效期分布',
        left: 'center',
        textStyle: { fontSize: 16 }
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        bottom: 'center'
      },
      series: [{
        name: '效期状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}\n({d}%)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        data: [
          { value: expired, name: '已过期', itemStyle: { color: '#F56C6C' } },
          { value: expiring_soon, name: '快过期（30天内）', itemStyle: { color: '#E6A23C' } },
          { value: safe, name: '安全', itemStyle: { color: '#67C23A' } }
        ]
      }]
    }
    
    expiryChart.setOption(option)
    
    window.addEventListener('resize', () => {
      expiryChart?.resize()
    })
  } catch (error) {
    console.error('加载过期分布数据失败:', error)
    ElMessage.error('加载过期分布数据失败')
  }
}

// 加载Top5关联药品
const loadTop5Chart = async () => {
  try {
    const response = await dashboardApi.getTop5Correlated()
    const data = response.data.results || []
    
    if (!top5Chart) {
      top5Chart = echarts.init(top5ChartRef.value)
    }
    
    if (data.length === 0) {
      top5Chart.setOption({
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { fontSize: 16, color: '#909399' }
        }
      })
      return
    }
    
    const option = {
      title: {
        text: '经常一起被开出的药品 Top 5',
        left: 'center',
        top: 10,
        textStyle: { fontSize: 16 }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          const item = params[0]
          const data = item.data
          let result = `${item.name.replace(/\n/g, ' + ')}<br/>共现次数: ${data.value || data}次`
          if (data.clinical_advice) {
            result += `<br/><span style="color: #F56C6C;">临床建议: ${data.clinical_advice}</span>`
          }
          return result
        }
      },
      grid: {
        left: '5%',
        right: '5%',
        bottom: '35%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.map(item => `${item.drug1}\n+ ${item.drug2}`),
        axisLabel: { 
          rotate: -45, // 旋转45度，避免文字重叠
          interval: 0,
          fontSize: 10,
          lineHeight: 14,
          margin: 10, // 增加标签与轴的距离
          formatter: (value) => {
            // 如果文字太长，截断并显示省略号
            const lines = value.split('\n')
            if (lines.length > 0) {
              const maxLength = 8 // 每行最大字符数
              return lines.map(line => {
                if (line.length > maxLength) {
                  return line.substring(0, maxLength) + '...'
                }
                return line
              }).join('\n')
            }
            return value
          },
          textStyle: {
            color: '#333',
            fontSize: 10
          }
        },
        axisTick: {
          alignWithLabel: true // 刻度线与标签对齐
        }
      },
      yAxis: {
        type: 'value',
        name: '共现次数'
      },
      series: [{
        name: '共现次数',
        type: 'bar',
        barWidth: '50%',
        data: data.map(item => ({
          value: item.count,
          clinical_advice: item.clinical_advice
        })),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}次'
        }
      }]
    }
    
    top5Chart.setOption(option)
    
    // 响应式调整：根据窗口宽度动态调整配置
    const handleResize = () => {
      if (!top5Chart) return
      
      const width = window.innerWidth
      let updateOption = {}
      
      // 根据屏幕宽度调整标签旋转角度和字体大小
      if (width < 768) {
        // 移动端：旋转90度，更小的字体，更多底部空间
        updateOption = {
          xAxis: [{
            axisLabel: {
              rotate: -90,
              fontSize: 9
            }
          }],
          grid: [{
            bottom: '40%'
          }]
        }
      } else if (width < 1024) {
        // 平板：旋转45度
        updateOption = {
          xAxis: [{
            axisLabel: {
              rotate: -45,
              fontSize: 10
            }
          }],
          grid: [{
            bottom: '35%'
          }]
        }
      } else {
        // 桌面：旋转45度
        updateOption = {
          xAxis: [{
            axisLabel: {
              rotate: -45,
              fontSize: 10
            }
          }],
          grid: [{
            bottom: '30%'
          }]
        }
      }
      
      top5Chart.setOption(updateOption)
      top5Chart.resize()
    }
    
    window.addEventListener('resize', handleResize)
    
    // 初始化时也检查一次
    setTimeout(handleResize, 100)
  } catch (error) {
    console.error('加载Top5关联数据失败:', error)
    ElMessage.error('加载Top5关联数据失败')
  }
}

// 初始化所有数据
const initDashboard = async () => {
  await loadStats()
  await nextTick()
  await loadLowStockChart()
  await loadExpiryChart()
  await loadTop5Chart()
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
  if (lowStockChart) {
    lowStockChart.dispose()
  }
  if (expiryChart) {
    expiryChart.dispose()
  }
  if (top5Chart) {
    top5Chart.dispose()
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
