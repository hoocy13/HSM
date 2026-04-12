<template>
  <div class="announce-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <span class="title">系统公告</span>
            <p class="subtitle">在此发布、编辑公告；仅「启用」的公告会在工作台「院内公告」区域展示。</p>
          </div>
          <el-button type="primary" @click="openCreate">发布公告</el-button>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="content" label="内容摘要" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ excerpt(row.content) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :loading="row._toggling"
              @change="(v) => toggleActive(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="load"
          @current-change="load"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑公告' : '发布公告'"
      width="640px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="公告标题" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="正文支持多行，将展示在工作台" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" active-text="展示在工作台" inactive-text="仅保存不展示" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { announcementApi } from '../api/drugs.js'

const rows = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)
const form = reactive({
  title: '',
  content: '',
  is_active: true
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

const excerpt = (s) => {
  const t = (s || '').replace(/\s+/g, ' ').trim()
  return t.length > 80 ? `${t.slice(0, 80)}…` : t || '—'
}

const formatTime = (s) => {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN')
}

const load = async () => {
  loading.value = true
  try {
    const { data } = await announcementApi.list({
      page: page.value,
      page_size: pageSize.value
    })
    const list = (data.results || []).map((r) => ({ ...r, _toggling: false }))
    rows.value = list
    total.value = data.count ?? 0
  } catch (e) {
    console.error(e)
    ElMessage.error('加载公告失败')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  isEdit.value = false
  editingId.value = null
  form.title = ''
  form.content = ''
  form.is_active = true
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editingId.value = row.id
  form.title = row.title
  form.content = row.content
  form.is_active = row.is_active
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.resetFields?.()
}

const submit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = {
      title: (form.title || '').trim(),
      content: (form.content || '').trim(),
      is_active: form.is_active
    }
    if (isEdit.value) {
      await announcementApi.patch(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await announcementApi.create(payload)
      ElMessage.success('已发布')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    const d = e.response?.data
    const msg = typeof d === 'object' ? Object.values(d).flat()[0] : d
    ElMessage.error(msg || '保存失败')
  } finally {
    saving.value = false
  }
}

const toggleActive = async (row, val) => {
  row._toggling = true
  try {
    await announcementApi.patch(row.id, { is_active: val })
    ElMessage.success(val ? '已启用' : '已停用')
  } catch (e) {
    row.is_active = !val
    ElMessage.error('更新失败')
  } finally {
    row._toggling = false
  }
}

const remove = (row) => {
  ElMessageBox.confirm(`确定删除公告「${row.title}」？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  })
    .then(async () => {
      try {
        await announcementApi.delete(row.id)
        ElMessage.success('已删除')
        load()
      } catch (e) {
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.announce-page {
  max-width: 1100px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  max-width: 560px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
