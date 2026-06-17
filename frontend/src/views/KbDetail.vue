<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" style="text-align: center; padding: 40px">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <template v-else-if="kb">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px">
        <div>
          <el-button text @click="$router.push('/knowledge-bases')">
            <el-icon><ArrowLeft /></el-icon> 返回
          </el-button>
          <h2 style="margin-top: 8px">{{ kb.name }}</h2>
          <p style="color: #909399; font-size: 13px; margin-top: 4px">{{ kb.description || '暂无描述' }}</p>
        </div>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon> 上传文档
        </el-button>
      </div>

      <!-- KB Info -->
      <el-card shadow="never" style="margin-bottom: 20px">
        <el-descriptions :column="4" size="small" border>
          <el-descriptions-item label="Embedding模型">{{ kb.embedding_model }}</el-descriptions-item>
          <el-descriptions-item label="Chunk大小">{{ kb.chunk_size }}</el-descriptions-item>
          <el-descriptions-item label="重叠">{{ kb.chunk_overlap }}</el-descriptions-item>
          <el-descriptions-item label="Top-K">{{ kb.top_k }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Stats -->
      <div class="stat-cards">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold">{{ stats.total_documents }}</div>
            <div style="color: #909399; font-size: 12px; margin-top: 4px">文档总数</div>
          </div>
        </el-card>
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #67c23a">{{ stats.indexed_documents }}</div>
            <div style="color: #909399; font-size: 12px; margin-top: 4px">已索引</div>
          </div>
        </el-card>
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #e6a23c">{{ stats.pending_documents }}</div>
            <div style="color: #909399; font-size: 12px; margin-top: 4px">待处理</div>
          </div>
        </el-card>
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #409eff">{{ stats.total_chunks || stats.vector_chunks }}</div>
            <div style="color: #909399; font-size: 12px; margin-top: 4px">向量块</div>
          </div>
        </el-card>
      </div>

      <!-- Batch Actions -->
      <div v-if="hasPending" style="margin-bottom: 16px">
        <el-button type="warning" :loading="batchProcessing" @click="handleBatchProcess">
          <el-icon><Lightning /></el-icon> 批量处理待处理文档
        </el-button>
      </div>

      <!-- Document Table -->
      <el-card shadow="never">
        <template #header>
          <span>文档列表</span>
        </template>

        <el-table :data="documents" stripe style="width: 100%" v-loading="docsLoading">
          <el-table-column prop="filename" label="文件名" min-width="200">
            <template #default="{ row }">
              <el-icon style="margin-right: 4px; vertical-align: middle">
                <component :is="getFileIcon(row.file_type)" />
              </el-icon>
              {{ row.filename }}
            </template>
          </el-table-column>
          <el-table-column prop="file_type" label="类型" width="80" align="center" />
          <el-table-column prop="file_size" label="大小" width="100" align="right">
            <template #default="{ row }">
              {{ formatSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
              <span class="status-dot" :class="row.status" />
              <span>{{ statusMap[row.status] }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="向量块" width="80" align="center" />
          <el-table-column label="操作" width="200" align="center">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="previewDoc(row)">预览</el-button>
              <el-button
                v-if="row.status === 'pending'"
                text
                type="warning"
                size="small"
                :loading="processingDoc === row.id"
                @click="handleProcessDoc(row)"
              >
                处理
              </el-button>
              <el-button text type="danger" size="small" @click="handleDeleteDoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-result v-else-if="!loading && !kb" status="warning" title="知识库不存在" subtitle="请检查链接是否正确">
      <template #extra>
        <el-button type="primary" @click="$router.push('/knowledge-bases')">返回列表</el-button>
      </template>
    </el-result>

    <!-- Upload Dialog -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-upload
        ref="uploadRef"
        drag
        multiple
        :auto-upload="false"
        :file-list="uploadFiles"
        :on-change="handleUploadChange"
        :on-remove="handleUploadRemove"
        accept=".pdf,.txt,.md,.docx,.doc"
      >
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖拽到此处，或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip" style="color: #909399">
            支持 PDF、TXT、Markdown、DOCX 格式
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          上传并处理
        </el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog v-model="showPreviewDialog" :title="previewDocData?.filename || '文档预览'" width="800px" top="5vh">
      <template v-if="previewLoading">
        <div style="text-align: center; padding: 40px">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        </div>
      </template>
      <template v-else>
        <el-tabs v-model="previewTab">
          <el-tab-pane label="原文" name="content">
            <pre style="white-space: pre-wrap; font-size: 13px; line-height: 1.6; max-height: 500px; overflow-y: auto; background: #f9f9f9; padding: 16px; border-radius: 8px">
              {{ previewContent }}
            </pre>
          </el-tab-pane>
          <el-tab-pane :label="`分块 (${previewChunks.length})`" name="chunks">
            <div style="max-height: 500px; overflow-y: auto">
              <el-card
                v-for="(chunk, i) in previewChunks"
                :key="chunk.id"
                class="chunk-card"
                shadow="hover"
              >
                <template #header>
                  <span style="font-size: 12px; color: #909399">Chunk #{{ i + 1 }} | Score: {{ chunk.score || '-' }}</span>
                </template>
                <div class="chunk-content">{{ chunk.content }}</div>
                <div style="margin-top: 8px; font-size: 11px; color: #c0c4cc">
                  {{ JSON.stringify(chunk.metadata) }}
                </div>
              </el-card>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getKnowledgeBase, listDocuments, uploadDocuments,
  processDocument, batchProcessDocuments, getDocument,
  getDocumentContent, getDocumentChunks, deleteDocument, getKbStats,
} from '../api'

const route = useRoute()
const kbId = computed(() => route.params.id)

const loading = ref(true)
const kb = ref(null)
const stats = ref({})
const documents = ref([])
const docsLoading = ref(false)

const showUploadDialog = ref(false)
const uploadRef = ref(null)
const uploadFiles = ref([])
const uploading = ref(false)

const batchProcessing = ref(false)
const processingDoc = ref(null)

const showPreviewDialog = ref(false)
const previewDocData = ref(null)
const previewContent = ref('')
const previewChunks = ref([])
const previewLoading = ref(false)
const previewTab = ref('content')

const statusMap = {
  pending: '待处理',
  processing: '处理中',
  indexed: '已索引',
  failed: '失败',
}

const hasPending = computed(() => documents.value.some(d => d.status === 'pending'))

function getFileIcon(type) {
  const icons = { pdf: 'Reading', txt: 'Document', md: 'EditPen', docx: 'Notebook' }
  return icons[type] || 'Document'
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return `${size.toFixed(1)} ${units[i]}`
}

async function loadData() {
  loading.value = true
  try {
    const [kbRes, docRes, statsRes] = await Promise.all([
      getKnowledgeBase(kbId.value),
      listDocuments(kbId.value),
      getKbStats(kbId.value),
    ])
    kb.value = kbRes.data
    documents.value = docRes.data
    stats.value = statsRes.data
  } catch (e) {
    ElMessage.error('加载数据失败')
    kb.value = null
  } finally {
    loading.value = false
  }
}

function handleUploadChange(ev) {
  uploadFiles.value = ev.fileList
}

function handleUploadRemove(ev) {
  uploadFiles.value = uploadFiles.value.filter(f => f.uid !== ev.uid)
}

async function handleUpload() {
  if (!uploadFiles.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  const files = uploadFiles.value.map(f => f.raw).filter(Boolean)
  try {
    await uploadDocuments(kbId.value, files)
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    uploadFiles.value = []
    await loadData()
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleProcessDoc(doc) {
  processingDoc.value = doc.id
  try {
    await processDocument(doc.id)
    ElMessage.success('处理完成')
    await loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '处理失败')
  } finally {
    processingDoc.value = null
  }
}

async function handleBatchProcess() {
  batchProcessing.value = true
  try {
    const res = await batchProcessDocuments(kbId.value)
    ElMessage.success(`处理完成，共处理 ${res.data.processed} 个文档`)
    await loadData()
  } catch (e) {
    ElMessage.error('批量处理失败')
  } finally {
    batchProcessing.value = false
  }
}

async function previewDoc(doc) {
  previewDocData.value = doc
  showPreviewDialog.value = true
  previewTab.value = 'content'
  previewLoading.value = true

  try {
    const [contentRes, chunksRes] = await Promise.all([
      getDocumentContent(doc.id).catch(() => ({ data: { content: '无法读取文件内容' } })),
      getDocumentChunks(doc.id).catch(() => ({ data: { chunks: [] } })),
    ])
    previewContent.value = contentRes.data.content
    previewChunks.value = chunksRes.data.chunks || []
  } catch (e) {
    previewContent.value = '加载失败'
    previewChunks.value = []
  } finally {
    previewLoading.value = false
  }
}

function handleDeleteDoc(doc) {
  ElMessageBox.confirm(`确定删除文档「${doc.filename}」？`, '确认删除', {
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
  }).then(async () => {
    try {
      await deleteDocument(doc.id)
      ElMessage.success('删除成功')
      await loadData()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(loadData)
</script>
