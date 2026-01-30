<script setup>
</script>

<template>
  <div id="app">
    <router-view />
  </div>
</template>

<style>
#app {
  width: 100%;
  min-height: 100vh;
  overflow-x: hidden;
}

/* 全局响应式样式 */
@media (max-width: 1200px) {
  .el-table {
    font-size: 14px;
  }
}

@media (max-width: 768px) {
  .el-table {
    font-size: 12px;
  }
  
  .el-table .el-table__cell {
    padding: 8px 4px;
  }
  
  .el-button {
    padding: 5px 10px;
    font-size: 12px;
  }
  
  .el-dialog {
    width: 90% !important;
    margin: 0 auto;
  }
}

@media (max-width: 480px) {
  .el-table {
    font-size: 11px;
  }
  
  .el-card {
    margin: 0;
    border-radius: 0;
  }
}
</style>
