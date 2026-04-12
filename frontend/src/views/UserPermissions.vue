<template>
  <el-card>
    <template #header>权限设置</template>
    <p class="muted">
      角色与接口权限由后端 DRF Permission 控制。此处可放置审批流、公告审核等扩展配置。
    </p>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="管理员">员工管理、系统公告发布、全量数据与操作审计等。</el-descriptions-item>
      <el-descriptions-item label="医师">开具处方、撤销本人处方、本科室数据（按后续规则扩展）。</el-descriptions-item>
      <el-descriptions-item label="药剂师">入库、库存盘点、药品信息查看。</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<style scoped>
.muted {
  color: #606266;
  margin-bottom: 16px;
}
</style>
