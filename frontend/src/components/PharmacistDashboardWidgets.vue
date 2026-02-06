<template>
  <el-card class="widget-card" shadow="hover">
    <template #header>
      <span>药剂师提醒</span>
    </template>
    <el-timeline v-if="alerts.length">
      <el-timeline-item
        v-for="(a, i) in alerts"
        :key="i"
        :timestamp="a.type === 'low_stock' ? '缺货' : '效期'"
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
  margin-top: 16px;
}
</style>
