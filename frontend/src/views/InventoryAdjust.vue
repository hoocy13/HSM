<template>
  <el-card>
    <template #header>库存盘点 / 损溢录入</template>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 520px">
      <el-form-item label="药品" prop="drug">
        <el-select v-model="form.drug" placeholder="请选择药品" filterable style="width: 100%">
          <el-option
            v-for="d in drugs"
            :key="d.id"
            :label="`${d.name} (库存 ${d.stock})`"
            :value="d.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="调整数量" prop="quantity_change">
        <el-input-number v-model="form.quantity_change" style="width: 100%" />
        <p class="hint">正数增加，负数减少（报损、差错等）。</p>
      </el-form-item>
      <el-form-item label="原因" prop="reason">
        <el-input v-model="form.reason" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="submit">提交</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { drugApi, inventoryApi } from '../api/drugs.js'

const formRef = ref(null)
const loading = ref(false)
const drugs = ref([])
const form = reactive({
  drug: null,
  quantity_change: 0,
  reason: ''
})
const rules = {
  drug: [{ required: true, message: '请选择药品', trigger: 'change' }],
  quantity_change: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  reason: [{ required: true, message: '请填写原因', trigger: 'blur' }]
}

onMounted(async () => {
  try {
    const res = await drugApi.getDrugs({ page_size: 2000 })
    drugs.value = res.data.results || []
  } catch (e) {
    ElMessage.error('加载药品失败')
  }
})

const submit = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await inventoryApi.create({
        drug: form.drug,
        quantity_change: form.quantity_change,
        reason: form.reason
      })
      ElMessage.success('已提交')
      form.reason = ''
      form.quantity_change = 0
      form.drug = null
      const res = await drugApi.getDrugs({ page_size: 2000 })
      drugs.value = res.data.results || []
    } catch (e) {
      const d = e.response?.data
      ElMessage.error(typeof d === 'object' ? Object.values(d).flat()[0] : d || '失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #909399;
  margin: 6px 0 0;
}
</style>
