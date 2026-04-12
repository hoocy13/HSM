<template>
  <el-card class="widget-card" shadow="hover">
    <template #header>
      <span>医师提醒</span>
    </template>
    <el-timeline v-if="alerts.length">
      <el-timeline-item
        v-for="(a, i) in alerts"
        :key="i"
        :timestamp="a.type === 'disease_trend' ? '疾病趋势' : '到货提醒'"
        placement="top"
      >
        {{ a.message }}
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="暂无提醒" />
  </el-card>
</template>

<script setup>
defineProps({
  alerts: { type: Array, default: () => [] }
})
</script>

<style scoped>
.widget-card {
  margin-top: 0;
  height: 100%;
}
</style>
