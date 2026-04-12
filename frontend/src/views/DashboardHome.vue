<template>
  <div class="workspace">
    <header class="welcome">
      <div class="welcome-text">
        <p class="welcome-kicker">工作台</p>
        <h1 class="welcome-title">{{ greeting }}，{{ displayName }}</h1>
        <p class="welcome-sub">{{ todayText }}</p>
      </div>
    </header>

    <!-- 系统公告：与上方欢迎条同一视觉语言的横向信息条 -->
    <section v-if="announcements.length" class="announce-stack" aria-label="系统公告">
      <article
        v-for="a in announcements"
        :key="a.id"
        class="info-strip info-strip--announce"
      >
        <div class="info-strip-main">
          <p class="info-strip-kicker">系统公告</p>
          <h2 class="info-strip-title">{{ a.title }}</h2>
          <p class="info-strip-body">{{ a.content }}</p>
        </div>
        <time class="info-strip-time">{{ formatDate(a.created_at) }}</time>
      </article>
    </section>

    <section class="board">
      <h2 class="board-title">
        <span class="board-title-bar" />
        工作指引
      </h2>
      <el-row :gutter="16" class="board-row">
        <el-col :xs="24" :lg="12">
          <div class="panel">
            <div class="panel-head">
              <el-icon class="panel-head-icon"><Notebook /></el-icon>
              <span>日常操作提示</span>
            </div>
            <div class="panel-body">
              <ul class="tip-list">
                <li>医师开具处方时，每张处方仅对应一种药品；提交前请核对药品库存与有效期。</li>
                <li>药剂师可通过「药品列表」右上角完成入库与库存盘点；列表中的「预警状态」支持排序，便于优先处理效期与缺货。</li>
                <li>「数据看板」内指标按时间窗口统计；在「数据趋势」中点击折线某日数据点，可查看当日用药记录明细。</li>
                <li>撤销处方将同步回滚库存，请仅在确认无误后操作。</li>
                <li v-if="!announcements.length">系统公告由管理员在「用户管理 → 系统公告」发布，启用后将显示在本页顶部横条。</li>
              </ul>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :lg="12">
          <div class="panel">
            <div class="panel-head">
              <el-icon class="panel-head-icon"><Lock /></el-icon>
              <span>安全与数据说明</span>
            </div>
            <div class="panel-body">
              <ul class="tip-list">
                <li>员工账号由管理员在「用户管理」中统一创建并分配角色（管理员 / 医师 / 药剂师），请使用本人账号登录。</li>
                <li>处方开具、入库、库存调整、用户信息变更等关键操作会写入「操作审计」，便于院内质控与教学演示追溯。</li>
                <li>医师与药剂师默认仅能查看<strong>本科室</strong>范围内的药品与用药记录；管理员可查看全院数据。</li>
                <li>若页面数据与实物库存不一致，请以库房实际盘点为准，并在系统中补录调整原因。</li>
              </ul>
              <template v-if="policies.length">
                <p class="panel-subtitle">制度与政策（系统）</p>
                <ul class="tip-list tip-list--compact">
                  <li v-for="p in policies" :key="p.id" class="tip-item-api">
                    <strong>{{ p.title }}</strong>
                    <span class="tip-meta">{{ formatDate(p.created_at) }}</span>
                    <p class="tip-api-desc">{{ p.content }}</p>
                  </li>
                </ul>
              </template>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <section v-if="showDoctor || showPharmacist" class="board board--alerts">
      <h2 class="board-title">
        <span class="board-title-bar" />
        业务提醒
      </h2>
      <el-row :gutter="16">
        <el-col v-if="showDoctor" :xs="24" :md="showPharmacist ? 12 : 24">
          <DoctorDashboardWidgets :alerts="doctorAlerts" class="hosp-widget" />
        </el-col>
        <el-col v-if="showPharmacist" :xs="24" :md="showDoctor ? 12 : 24">
          <PharmacistDashboardWidgets :alerts="pharmacistAlerts" class="hosp-widget" />
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Notebook, Lock } from '@element-plus/icons-vue'
import { dashboardApi } from '../api/drugs.js'
import DoctorDashboardWidgets from '../components/DoctorDashboardWidgets.vue'
import PharmacistDashboardWidgets from '../components/PharmacistDashboardWidgets.vue'

const announcements = ref([])
const policies = ref([])
const doctorAlerts = ref([])
const pharmacistAlerts = ref([])
const role = ref('doctor')
const username = ref('')

const showDoctor = computed(() => role.value === 'doctor' || role.value === 'admin')
const showPharmacist = computed(() => role.value === 'pharmacist' || role.value === 'admin')

const displayName = computed(() => username.value || '用户')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('zh-CN', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

const formatDate = (s) => {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const load = async () => {
  try {
    const u = localStorage.getItem('user')
    if (u) {
      const parsed = JSON.parse(u)
      role.value = parsed.role || 'doctor'
      username.value = parsed.username || ''
    }
    const { data } = await dashboardApi.getHome()
    announcements.value = data.announcements || []
    policies.value = data.policies || []
    doctorAlerts.value = data.doctor_alerts || []
    pharmacistAlerts.value = data.pharmacist_alerts || []
  } catch (e) {
    console.error(e)
    ElMessage.error('加载工作台失败')
  }
}

onMounted(load)
</script>

<style scoped>
/* 与侧栏 #304156、主色 #409EFF、顶栏/主区 Element 默认灰白体系对齐 */
.workspace {
  --sidebar-deep: #304156;
  --sidebar-muted: #bfcbd9;
  --primary: #409eff;
  --text-main: #303133;
  --text-secondary: #606266;
  --border: #e4e7ed;
  --bg-subtle: #f5f7fa;

  max-width: 1180px;
  margin: 0 auto;
  padding: 0 0 24px;
}

.welcome {
  margin-bottom: 16px;
  padding: 18px 20px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  border-left: 4px solid var(--primary);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.welcome-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  letter-spacing: 0.06em;
}

.welcome-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
}

.welcome-sub {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.announce-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.info-strip {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.info-strip--announce {
  border-left: 4px solid #67c23a;
}

.info-strip-main {
  min-width: 0;
  flex: 1;
}

.info-strip-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: #67c23a;
  letter-spacing: 0.06em;
}

.info-strip-title {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.35;
}

.info-strip-body {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.info-strip-time {
  flex-shrink: 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  padding-top: 22px;
  white-space: nowrap;
}

@media (max-width: 640px) {
  .info-strip {
    flex-direction: column;
  }
  .info-strip-time {
    padding-top: 0;
  }
}

.board {
  margin-bottom: 4px;
}

.board--alerts {
  margin-top: 12px;
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.board-title-bar {
  width: 3px;
  height: 16px;
  border-radius: 1px;
  background: var(--primary);
}

.board-row {
  align-items: stretch;
}

.panel {
  height: 100%;
  min-height: 220px;
  margin-bottom: 16px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.06);
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}

.panel-head-icon {
  color: var(--primary);
  font-size: 18px;
}

.panel-body {
  padding: 14px 16px 16px;
}

.panel-subtitle {
  margin: 16px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sidebar-deep);
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.tip-list {
  margin: 0;
  padding-left: 1.25rem;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.65;
}

.tip-list li {
  margin-bottom: 10px;
}

.tip-list li:last-child {
  margin-bottom: 0;
}

.tip-list--compact {
  list-style: none;
  padding-left: 0;
}

.tip-item-api {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.tip-item-api:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.tip-meta {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: normal;
  color: #909399;
}

.tip-api-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
}

.workspace :deep(.hosp-widget.el-card) {
  margin-top: 0;
  border-radius: 4px;
  border: 1px solid var(--border);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.06);
  background: #fff;
}

.workspace :deep(.hosp-widget .el-card__header) {
  font-weight: 600;
  color: var(--text-main);
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
  padding: 12px 16px;
}

.workspace :deep(.hosp-widget .el-card__body) {
  color: var(--text-secondary);
}

.workspace :deep(.hosp-widget .el-timeline-item__timestamp) {
  color: #909399;
  font-weight: 500;
}
</style>
