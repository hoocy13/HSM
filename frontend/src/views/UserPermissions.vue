<template>
  <el-card>
    <template #header>权限设置</template>
    <p class="muted">
      角色与接口权限由后端 DRF Permission 控制。此处可放置审批流、公告审核等扩展配置。
    </p>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="管理员">员工管理、系统公告发布、全量数据与操作审计等。</el-descriptions-item>
      <el-descriptions-item label="医师">用药记录（开具处方，待发药不扣库存）、撤销本人处方、数据看板；不进入药品列表。</el-descriptions-item>
      <el-descriptions-item label="药剂师">审批发药、药品列表与入库、库存盘点；不进入用药记录菜单。</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<style scoped>
.muted {
  color: #606266;
  margin-bottom: 16px;
}
</style>
