<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新建知识库
      </el-button>
    </div>

    <!-- Loading -->
    <div v-if="loading" style="text-align: center; padding: 40px">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <!-- Empty State -->
    <el-empty v-else-if="kbs.length === 0" description="暂无知识库，点击右上角创建" />

    <!-- KB Cards -->
    <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px">
      <el-card v-for="kb in kbs" :key="kb.id" shadow="hover" :body-style="{ padding: '20px' }">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <h3 style="margin-bottom: 8px; font-size: 16px">{{ kb.name }}</h3>
            <p style="color: #909399; font-size: 13px; margin-bottom: 12px">
              {{ kb.description || '暂无描述' }}
            </p>
          </div>
          <el-dropdown trigger="click" @command="(cmd) => handleKbAction(cmd, kb)">
            <el-button text>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon><Edit /></el-icon> 编辑
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided style="color: #f56c6c">
                  <el-icon><Delete /></el-icon> 删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-descriptions :column="3" size="small" border style="margin-bottom: 12px">
          <el-descriptions-item label="Chunk大小">{{ kb.chunk_size }}</el-descriptions-item>
          <el-descriptions-item label="重叠">{{ kb.chunk_overlap }}</el-descriptions-item>
          <el-descriptions-item label="Top-K">{{ kb.top_k }}</el-descriptions-item>
        </el-descriptions>

        <div style="font-size: 12px; color: #909399; margin-bottom: 12px">
          模型: {{ kb.embedding_model }}
        </div>

        <el-button type="primary" size="small" @click="$router.push(`/knowledge-bases/${kb.id}`)">
          <el-icon><View /></el-icon> 管理
        </el-button>
      </el-card>
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreateDialog" title="新建知识库" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="知识库描述" />
        </el-form-item>
        <el-form-item label="Embedding模型">
          <el-input v-model="createForm.embedding_model" placeholder="BAAI/bge-small-zh-v1.5" />
        </el-form-item>
        <el-form-item label="Chunk大小">
          <el-input-number v-model="createForm.chunk_size" :min="64" :max="2048" :step="64" />
        </el-form-item>
        <el-form-item label="重叠">
          <el-input-number v-model="createForm.chunk_overlap" :min="0" :max="512" :step="16" />
        </el-form-item>
        <el-form-item label="Top-K">
          <el-input-number v-model="createForm.top_k" :min="1" :max="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEditDialog" title="编辑知识库" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Chunk大小">
          <el-input-number v-model="editForm.chunk_size" :min="64" :max="2048" :step="64" />
        </el-form-item>
        <el-form-item label="重叠">
          <el-input-number v-model="editForm.chunk_overlap" :min="0" :max="512" :step="16" />
        </el-form-item>
        <el-form-item label="Top-K">
          <el-input-number v-model="editForm.top_k" :min="1" :max="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '../api'

const loading = ref(true)
const kbs = ref([])

const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({
  name: '',
  description: '',
  embedding_model: 'BAAI/bge-small-zh-v1.5',
  chunk_size: 512,
  chunk_overlap: 64,
  top_k: 5,
})

const showEditDialog = ref(false)
const updating = ref(false)
const editingKb = ref(null)
const editForm = ref({})

async function loadKBs() {
  loading.value = true
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
  } catch (e) {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.name) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  creating.value = true
  try {
    await createKnowledgeBase(createForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    createForm.value = {
      name: '', description: '', embedding_model: 'BAAI/bge-small-zh-v1.5',
      chunk_size: 512, chunk_overlap: 64, top_k: 5,
    }
    await loadKBs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function handleKbAction(cmd, kb) {
  if (cmd === 'edit') {
    editingKb.value = kb
    editForm.value = {
      name: kb.name,
      description: kb.description,
      chunk_size: kb.chunk_size,
      chunk_overlap: kb.chunk_overlap,
      top_k: kb.top_k,
    }
    showEditDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(`确定删除知识库「${kb.name}」？所有文档和向量数据将被移除。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    }).then(async () => {
      try {
        await deleteKnowledgeBase(kb.id)
        ElMessage.success('删除成功')
        await loadKBs()
      } catch (e) {
        ElMessage.error('删除失败')
      }
    }).catch(() => {})
  }
}

async function handleUpdate() {
  if (!editingKb.value) return
  updating.value = true
  try {
    await updateKnowledgeBase(editingKb.value.id, editForm.value)
    ElMessage.success('更新成功')
    showEditDialog.value = false
    await loadKBs()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    updating.value = false
  }
}

onMounted(loadKBs)
</script>
