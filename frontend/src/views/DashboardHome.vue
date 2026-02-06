<template>
  <div class="dash-home">
    <el-row :gutter="20">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>公告栏</template>
          <el-empty v-if="!announcements.length" description="暂无公告" />
          <ul v-else class="list">
            <li v-for="a in announcements" :key="a.id">
              <strong>{{ a.title }}</strong>
              <p class="muted">{{ a.content }}</p>
            </li>
          </ul>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>政策更新</template>
          <el-empty v-if="!policies.length" description="暂无政策" />
          <ul v-else class="list">
            <li v-for="p in policies" :key="p.id">
              <strong>{{ p.title }}</strong>
              <p class="muted">{{ p.content }}</p>
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <DoctorDashboardWidgets
      v-if="showDoctor"
      :alerts="doctorAlerts"
    />
    <PharmacistDashboardWidgets
      v-if="showPharmacist"
      :alerts="pharmacistAlerts"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dashboardApi } from '../api/drugs.js'
import DoctorDashboardWidgets from '../components/DoctorDashboardWidgets.vue'
import PharmacistDashboardWidgets from '../components/PharmacistDashboardWidgets.vue'

const announcements = ref([])
const policies = ref([])
const doctorAlerts = ref([])
const pharmacistAlerts = ref([])
const role = ref('patient')

const showDoctor = computed(() => role.value === 'doctor' || role.value === 'admin')
const showPharmacist = computed(() => role.value === 'pharmacist' || role.value === 'admin')

const load = async () => {
  try {
    const u = localStorage.getItem('user')
    if (u) {
      const parsed = JSON.parse(u)
      role.value = parsed.role || 'patient'
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
.dash-home {
  max-width: 1200px;
}
.list {
  margin: 0;
  padding-left: 18px;
}
.muted {
  color: #909399;
  font-size: 13px;
  margin: 6px 0 0;
}
</style>
