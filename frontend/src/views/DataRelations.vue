<template>
  <div class="data-relations">
    <el-card class="rel-card">
      <template #header>
        <div class="header-row">
          <div class="title-wrap">
            <div class="title">药品关联关系图</div>
            <div class="subtitle">按处方共现频率构建，支持拖拽/缩放</div>
          </div>
          <div class="controls">
            <el-tooltip content="默认近30天（全院），用于演示统一口径" placement="top">
              <span class="label">时间</span>
            </el-tooltip>
            <el-segmented
              v-model="days"
              :options="[
                { label: '7天', value: 7 },
                { label: '30天', value: 30 },
                { label: '90天', value: 90 }
              ]"
              size="small"
              @change="load"
            />

            <el-tooltip content="整体：展示全网；中心：聚焦某个药品" placement="top">
              <span class="label">模式</span>
            </el-tooltip>
            <el-segmented
              v-model="mode"
              :options="[
                { label: '整体关系网', value: 'overall' },
                { label: '中心聚焦', value: 'center' }
              ]"
              size="small"
              @change="render"
            />

            <el-tooltip content="选择中心药品，仅展示其关联网络" placement="top">
              <span class="label">中心药品</span>
            </el-tooltip>
            <el-select
              v-model="centerId"
              size="small"
              filterable
              clearable
              placeholder="自动（热度最高）"
              style="width: 220px"
              :disabled="mode !== 'center'"
              @change="render"
            >
              <el-option
                v-for="o in centerOptions"
                :key="o.id"
                :label="o.label"
                :value="o.id"
              />
            </el-select>

            <el-tooltip content="展示中心药品的 Top N 关联" placement="top">
              <span class="label" style="margin-left: 10px;">关联Top</span>
            </el-tooltip>
            <el-select v-model="neighborTop" size="small" style="width: 120px" @change="render">
              <el-option :value="8" label="8" />
              <el-option :value="12" label="12" />
              <el-option :value="18" label="18" />
              <el-option :value="25" label="25" />
            </el-select>

            <el-tooltip content="限制连线数量，避免图过密" placement="top">
              <span class="label">连线Top</span>
            </el-tooltip>
            <el-select v-model="edgeTop" size="small" style="width: 120px" @change="render">
              <el-option :value="100" label="100" />
              <el-option :value="200" label="200" />
              <el-option :value="400" label="400" />
            </el-select>
            <el-tooltip content="过滤弱关联（共现次数过低的连线）" placement="top">
              <span class="label" style="margin-left: 10px;">最小共现</span>
            </el-tooltip>
            <el-input-number v-model="minWeight" size="small" :min="0" :max="99" @change="render" />
            <el-button size="small" @click="load" style="margin-left: 10px;">刷新</el-button>
          </div>
        </div>
      </template>
      <div class="content">
        <div ref="graphRef" class="graph"></div>
        <div class="side">
          <div class="side-title">{{ mode === 'center' ? 'Top 关联（中心药品）' : '关系网概览' }}</div>
          <div v-if="!centerSummary.name" class="side-empty">暂无数据</div>
          <div v-else class="side-meta">
            <div class="meta-name">{{ centerSummary.name }}</div>
            <div class="meta-sub">关联节点：{{ centerSummary.nodeCount }}｜连线：{{ centerSummary.edgeCount }}</div>
            <div v-if="mode === 'overall' && (centerSummary.top || []).length < 10" class="meta-sub">
              当前筛选条件下不足 10 条强关联，可把“最小共现”调低或把“连线Top”调高。
            </div>
          </div>
          <el-scrollbar height="520px">
            <div v-for="(x, idx) in (centerSummary.top || [])" :key="idx" class="rank-row">
              <div class="rank-left">
                <div class="rank-idx">{{ idx + 1 }}</div>
                <div class="rank-name" :title="x.name">{{ x.name }}</div>
              </div>
              <div class="rank-val">{{ x.w }}</div>
            </div>
          </el-scrollbar>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { dashboardApi } from '../api/drugs.js'

const graphRef = ref(null)
let chart = null

const days = ref(30)
const mode = ref('overall') // overall | center
const edgeTop = ref(200)
const minWeight = ref(0)
const neighborTop = ref(12)
const centerId = ref('')
const centerOptions = ref([])
const centerSummary = ref({ name: '', nodeCount: 0, edgeCount: 0, top: [] })

let rawMatrix = { labels: [], matrix: [] }

const palette = [
  '#4cc9f0', // cyan
  '#3a86ff', // blue
  '#8338ec', // purple
  '#ff006e', // pink
  '#ffbe0b', // yellow
  '#06d6a0', // green
  '#fb5607', // orange
]

const stableHash = (s) => {
  let h = 0
  for (let i = 0; i < (s || '').length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

const colorForName = (name) => {
  // Use HSL to avoid too-dark colors on dark background.
  const hue = stableHash(name) % 360
  return `hsl(${hue}, 85%, 62%)`
}

const computeDegrees = (dm) => {
  const labels = dm.labels || []
  const matrix = dm.matrix || []
  const n = labels.length
  const deg = new Array(n).fill(0)
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const v = matrix[i] && matrix[i][j] !== undefined ? Number(matrix[i][j] || 0) : 0
      if (v <= 0) continue
      deg[i] += v
      deg[j] += v
    }
  }
  return deg
}

const buildGraph = (dm) => {
  const labels = dm.labels || []
  const matrix = dm.matrix || []
  const n = labels.length
  if (!n) return { nodes: [], links: [], maxW: 1 }

  const deg = computeDegrees(dm)

  // 整体模式：全网关系（保留强边 + 控制边数）
  if (mode.value === 'overall') {
    const allLinks = []
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const v = matrix[i] && matrix[i][j] !== undefined ? Number(matrix[i][j] || 0) : 0
        if (v <= 0) continue
        if (v < (minWeight.value || 0)) continue
        allLinks.push({ source: i, target: j, value: v })
      }
    }
    allLinks.sort((a, b) => b.value - a.value)
    const picked = allLinks.slice(0, edgeTop.value || 0)

    const used = new Set()
    picked.forEach((l) => {
      used.add(l.source)
      used.add(l.target)
    })

    // Show labels for top-k hottest nodes in overall view.
    const usedArr = Array.from(used)
    const topLabelK = 26
    const topByDeg = usedArr
      .map((idx) => ({ idx, d: deg[idx] || 0 }))
      .sort((a, b) => b.d - a.d)
      .slice(0, topLabelK)
      .reduce((s, x) => (s.add(x.idx), s), new Set())

    const maxDeg = Math.max(1, ...Array.from(used).map((idx) => deg[idx] || 0))
    const nodes = Array.from(used).map((idx) => {
      const d = deg[idx] || 0
      const size = 12 + Math.round(34 * d / maxDeg)
      const name = labels[idx]
      const color = colorForName(name)
      return {
        id: String(idx),
        name,
        value: d,
        symbolSize: size,
        category: 0,
        label: {
          show: topByDeg.has(idx),
          color: 'rgba(235, 245, 255, 0.92)',
          fontSize: 12,
          backgroundColor: 'rgba(5, 8, 22, 0.55)',
          padding: [3, 6],
          borderRadius: 6,
          textBorderColor: 'rgba(0,0,0,0.65)',
          textBorderWidth: 3,
          overflow: 'truncate',
          width: 140,
        },
        itemStyle: {
          color,
          shadowBlur: 18,
          shadowColor: 'rgba(255,255,255,0.10)',
          borderColor: 'rgba(255,255,255,0.18)',
          borderWidth: 1,
        },
      }
    })

    const maxW = Math.max(1, ...picked.map((l) => l.value))
    const showEdgeNames = picked.length <= 80
    const graphLinks = picked.map((l) => ({
      source: String(l.source),
      target: String(l.target),
      value: l.value,
      lineStyle: {
        width: 0.6 + 3.6 * (l.value / maxW),
        opacity: 0.10 + 0.55 * (l.value / maxW),
      },
      label: showEdgeNames
        ? {
            show: true,
            fontSize: 9,
            color: 'rgba(220, 235, 255, 0.92)',
            formatter: `${labels[l.source]} ↔ ${labels[l.target]}\n×${l.value}`,
          }
        : { show: false },
    }))

    centerSummary.value = {
      name: `全网（阈值≥${minWeight.value}，取强边Top ${edgeTop.value}）`,
      nodeCount: nodes.length,
      edgeCount: graphLinks.length,
      top: picked.slice(0, 10).map((l) => ({
        name: `${labels[l.source]} ↔ ${labels[l.target]}`,
        w: l.value,
      })),
    }

    return { nodes, links: graphLinks, maxW }
  }

  // 选中心：优先用户选择，否则取度数最大
  let c = -1
  if (centerId.value !== '') {
    const parsed = Number(centerId.value)
    if (!Number.isNaN(parsed)) c = parsed
  }
  if (c < 0 || c >= n) {
    let best = 0
    for (let i = 1; i < n; i++) if ((deg[i] || 0) > (deg[best] || 0)) best = i
    c = best
  }

  // 只保留中心的 top 邻居，内容更聚焦
  const neigh = []
  for (let j = 0; j < n; j++) {
    if (j === c) continue
    const a = c < j ? c : j
    const b = c < j ? j : c
    const v = matrix[a] && matrix[a][b] !== undefined ? Number(matrix[a][b] || 0) : 0
    if (v <= 0) continue
    neigh.push({ id: j, w: v })
  }
  neigh.sort((x, y) => y.w - x.w)
  const topNeigh = neigh.filter((x) => x.w >= (minWeight.value || 0)).slice(0, neighborTop.value)

  // 构建边：中心-邻居为主；若 edgeTop 允许，补少量“邻居之间”的强边
  const used = new Set([c])
  topNeigh.forEach((x) => used.add(x.id))

  const links = []
  topNeigh.forEach((x) => links.push({ source: c, target: x.id, value: x.w }))

  const extra = []
  const usedArr = Array.from(used)
  for (let i = 0; i < usedArr.length; i++) {
    for (let j = i + 1; j < usedArr.length; j++) {
      const u = usedArr[i]
      const v = usedArr[j]
      if (u === c || v === c) continue // 已有中心边
      const a = u < v ? u : v
      const b = u < v ? v : u
      const w = matrix[a] && matrix[a][b] !== undefined ? Number(matrix[a][b] || 0) : 0
      if (w <= 0) continue
      extra.push({ source: u, target: v, value: w })
    }
  }
  extra.sort((a, b) => b.value - a.value)
  const maxExtra = Math.max(0, (edgeTop.value || 0) - links.length)
  extra.slice(0, maxExtra).forEach((x) => links.push(x))

  const maxDeg = Math.max(1, ...Array.from(used).map((idx) => deg[idx] || 0))
  const nodes = Array.from(used).map((idx) => {
    const d = deg[idx] || 0
    const size = 14 + Math.round(34 * d / maxDeg)
    const name = labels[idx]
    const color = colorForName(name)
    const isCenter = idx === c
    return {
      id: String(idx),
      name,
      value: d,
      symbolSize: isCenter ? Math.max(size + 12, 44) : size,
      category: 0,
      label: {
        show: isCenter ? true : size >= 26,
        color: 'rgba(235, 245, 255, 0.92)',
        fontSize: isCenter ? 13 : 12,
        backgroundColor: 'rgba(5, 8, 22, 0.55)',
        padding: [3, 6],
        borderRadius: 6,
        textBorderColor: 'rgba(0,0,0,0.65)',
        textBorderWidth: 3,
        overflow: 'truncate',
        width: 140,
      },
      itemStyle: {
        color,
        shadowBlur: isCenter ? 38 : 24,
        shadowColor: color.replace(')', ',0.35)').replace('rgb', 'rgba'),
        borderColor: 'rgba(255,255,255,0.22)',
        borderWidth: isCenter ? 2 : 1,
      },
    }
  })

  const maxW = Math.max(1, ...links.map((l) => l.value))
  const graphLinks = links.map((l) => ({
    source: String(l.source),
    target: String(l.target),
    value: l.value,
    lineStyle: {
      width: 0.8 + 4.2 * (l.value / maxW),
      opacity: 0.18 + 0.55 * (l.value / maxW),
    },
    label: {
      show: true,
      fontSize: 10,
      color: 'rgba(220, 235, 255, 0.95)',
      formatter: `${labels[l.source]} ↔ ${labels[l.target]}\n×${l.value}`,
    },
  }))

  // 右侧“Top 关联”列表
  centerSummary.value = {
    name: labels[c] || '',
    nodeCount: nodes.length,
    edgeCount: graphLinks.length,
    top: topNeigh.map((x) => ({ name: labels[x.id] || '-', w: x.w })),
  }

  return { nodes, links: graphLinks, maxW }
}

const render = () => {
  if (!graphRef.value) return
  if (!chart) chart = echarts.init(graphRef.value, null, { renderer: 'canvas' })

  const { nodes, links } = buildGraph(rawMatrix)
  const labels = rawMatrix.labels || []
  if (!nodes.length) {
    chart.setOption({
      backgroundColor: '#071126',
      title: {
        text: '暂无足够数据生成关系图',
        left: 'center',
        top: 'center',
        textStyle: { color: '#9aa4b2', fontSize: 14, fontWeight: 500 }
      }
    })
    return
  }

  const categories = [{ name: '药品（颜色区分节点；连线为处方共现）', itemStyle: { color: palette[0] } }]

  chart.setOption({
    backgroundColor: {
      type: 'radial',
      x: 0.45,
      y: 0.42,
      r: 0.95,
      colorStops: [
        { offset: 0, color: '#0c2048' },
        { offset: 0.55, color: '#071126' },
        { offset: 1, color: '#050816' },
      ],
    },
    tooltip: {
      backgroundColor: 'rgba(8, 16, 34, 0.92)',
      borderColor: 'rgba(255,255,255,0.12)',
      borderWidth: 1,
      textStyle: { color: '#e6f0ff' },
      formatter: (p) => {
        if (p.dataType === 'edge') {
          const si = Number(p.data.source)
          const ti = Number(p.data.target)
          const a = labels[si] || p.data.source
          const b = labels[ti] || p.data.target
          return `<div style="font-weight:600;margin-bottom:4px;">关联强度</div>${a} ↔ ${b}<br/>共现: <b>${p.data.value}</b>`
        }
        return `<div style="font-weight:600;margin-bottom:4px;">${p.data.name}</div>节点热度: <b>${p.data.value}</b>`
      }
    },
    legend: { show: false },
    toolbox: {
      show: true,
      right: 12,
      top: 10,
      iconStyle: { borderColor: 'rgba(214, 228, 255, 0.65)' },
      feature: {
        restore: { title: '重置' },
        saveAsImage: { title: '导出图片', backgroundColor: '#050816' },
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        links,
        categories,
        focusNodeAdjacency: true,
        edgeSymbol: ['none', 'none'],
        force: {
          repulsion: mode.value === 'overall' ? 420 : 320,
          edgeLength: mode.value === 'overall' ? [90, 240] : [80, 220],
          gravity: mode.value === 'overall' ? 0.015 : 0.02,
          friction: 0.18,
        },
        label: {
          color: 'rgba(235, 245, 255, 0.92)',
          fontSize: 12,
          textBorderColor: 'rgba(0,0,0,0.55)',
          textBorderWidth: 3,
        },
        lineStyle: {
          color: 'source',
          curveness: 0.26,
        },
        itemStyle: {
          borderColor: 'rgba(255,255,255,0.18)',
          borderWidth: 1,
        },
        emphasis: {
          scale: true,
          focus: 'adjacency',
          label: { show: true },
          lineStyle: { opacity: 0.95, width: 4 },
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.55)',
            borderWidth: 2,
            shadowBlur: 34,
          }
        }
      }
    ]
  }, { notMerge: true })
}

const load = async () => {
  try {
    const { data } = await dashboardApi.getTrends({ days: days.value })
    rawMatrix = data.drug_matrix || { labels: [], matrix: [] }
    const labels = rawMatrix.labels || []
    const deg = computeDegrees(rawMatrix)
    const opts = labels
      .map((label, idx) => ({ id: String(idx), label, deg: deg[idx] || 0 }))
      .filter((x) => x.deg > 0)
      .sort((a, b) => b.deg - a.deg)
      .slice(0, 500)
      .map((x) => ({ id: x.id, label: `${x.label}（热度:${x.deg}）` }))
    centerOptions.value = opts
    render()
  } catch (e) {
    console.error(e)
    ElMessage.error('加载关联数据失败')
  }
}

const onResize = () => chart?.resize()

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.data-relations :deep(.el-card__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.data-relations :deep(.el-card__body) {
  background: #050816;
}
.rel-card {
  border-radius: 14px;
  overflow: hidden;
}
.content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 14px;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.title {
  font-weight: 650;
  letter-spacing: 0.2px;
}
.subtitle {
  font-size: 12px;
  color: #909399;
}
.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.label {
  color: #606266;
  font-size: 12px;
}
.graph {
  width: 100%;
  height: 620px;
  border-radius: 10px;
  overflow: hidden;
}
.side {
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
  border: 1px solid rgba(255,255,255,0.10);
  padding: 12px 12px 8px;
  overflow: hidden;
}
.side-title {
  font-weight: 650;
  color: #e6f0ff;
  margin-bottom: 8px;
}
.side-empty {
  color: rgba(214, 228, 255, 0.65);
  font-size: 12px;
  padding: 8px 0;
}
.side-meta {
  margin-bottom: 10px;
}
.meta-name {
  color: rgba(235, 245, 255, 0.95);
  font-weight: 600;
  line-height: 1.2;
}
.meta-sub {
  color: rgba(214, 228, 255, 0.62);
  font-size: 12px;
  margin-top: 2px;
}
.rank-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 6px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.rank-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.rank-idx {
  width: 22px;
  height: 22px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: rgba(235, 245, 255, 0.9);
  background: rgba(58, 134, 255, 0.18);
  border: 1px solid rgba(58, 134, 255, 0.22);
}
.rank-name {
  color: rgba(235, 245, 255, 0.9);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}
.rank-val {
  color: rgba(255, 190, 11, 0.92);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

@media (max-width: 1100px) {
  .content {
    grid-template-columns: 1fr;
  }
  .side {
    order: 2;
  }
}
</style>

