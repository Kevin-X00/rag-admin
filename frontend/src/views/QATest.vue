<template>
  <div class="qa-container">
    <h2 style="margin-bottom: 20px">问答测试</h2>

    <div style="display: flex; gap: 16px; margin-bottom: 16px">
      <el-select
        v-model="selectedKbId"
        placeholder="选择知识库"
        style="width: 300px"
        @change="loadHistory"
      >
        <el-option
          v-for="kb in kbs"
          :key="kb.id"
          :label="kb.name"
          :value="kb.id"
        />
      </el-select>
      <el-input-number v-model="topK" :min="1" :max="20" size="default" />
      <span style="line-height: 32px; color: #909399; font-size: 13px">Top-K</span>
    </div>

    <!-- Messages -->
    <div class="qa-messages" ref="messagesRef">
      <div v-if="messages.length === 0" style="text-align: center; padding: 60px 20px; color: #c0c4cc">
        <el-icon :size="48"><ChatLineSquare /></el-icon>
        <p style="margin-top: 12px">选择知识库并输入问题开始测试</p>
      </div>

      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="qa-message"
        :class="msg.role"
      >
        <div v-if="msg.role === 'assistant' && msg.sources?.length" class="qa-sources">
          <details>
            <summary style="cursor: pointer; color: #409eff">参考资料 ({{ msg.sources.length }})</summary>
            <div v-for="(src, j) in msg.sources" :key="j" style="margin-top: 8px; padding: 8px; background: #fff; border-radius: 6px; border: 1px solid #e4e7ed">
              <div style="font-size: 12px; color: #909399; margin-bottom: 4px">
                来源 {{ j + 1 }} | 相似度: {{ src.score }}
              </div>
              <div style="font-size: 12px; line-height: 1.5; white-space: pre-wrap">{{ src.content }}</div>
            </div>
          </details>
        </div>

        <div class="qa-message-bubble">
          <div v-if="msg.role === 'assistant' && msg.streaming" style="display: flex; align-items: center; gap: 8px">
            <span>{{ msg.content }}</span>
            <span class="cursor-blink" style="display: inline-block; width: 8px; height: 16px; background: #409eff; animation: blink 1s step-end infinite">|</span>
          </div>
          <div v-else>{{ msg.content }}</div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="qa-input-area">
      <el-input
        v-model="query"
        type="textarea"
        :rows="2"
        placeholder="输入问题..."
        :disabled="!selectedKbId || answering"
        @keydown.enter.prevent="handleSend"
      />
      <el-button
        type="primary"
        :loading="answering"
        :disabled="!query.trim() || !selectedKbId"
        @click="handleSend"
        style="height: 100%"
      >
        <el-icon><Promotion /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { listKnowledgeBases, searchQA, searchRetrieve } from '../api'

const kbs = ref([])
const selectedKbId = ref('')
const topK = ref(5)
const query = ref('')
const answering = ref(false)
const messages = ref([])
const messagesRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

async function loadKBs() {
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
  } catch (e) {
    ElMessage.error('加载知识库列表失败')
  }
}

function loadHistory() {
  messages.value = []
}

async function handleSend() {
  if (!query.value.trim() || !selectedKbId.value) return
  if (answering.value) return

  const userQuery = query.value.trim()
  query.value = ''

  // Add user message
  messages.value.push({ role: 'user', content: userQuery })

  // Add placeholder assistant message
  const assistantMsg = { role: 'assistant', content: '', streaming: true, sources: [] }
  messages.value.push(assistantMsg)
  scrollToBottom()

  answering.value = true
  try {
    // Retrieve chunks first for display
    const retrieveRes = await searchRetrieve(selectedKbId.value, userQuery, topK.value)
    assistantMsg.sources = retrieveRes.data.chunks || []
    assistantMsg.content = ''

    // Then get QA answer
    const qaRes = await searchQA(selectedKbId.value, userQuery, topK.value)
    assistantMsg.content = qaRes.data.answer || '（未获取到回答）'
    assistantMsg.streaming = false
  } catch (e) {
    assistantMsg.content = '（查询失败：' + (e.response?.data?.detail || e.message) + '）'
    assistantMsg.streaming = false
  } finally {
    answering.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  loadKBs()
})
</script>

<style scoped>
.cursor-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
