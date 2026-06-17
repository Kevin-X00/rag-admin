<template>
  <div>
    <h2 style="margin-bottom: 20px">系统总览</h2>

    <!-- Loading -->
    <div v-if="loading" style="text-align: center; padding: 40px">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p style="margin-top: 12px; color: #909399">加载中...</p>
    </div>

    <!-- Stats Cards -->
    <div v-else class="stat-cards">
      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>知识库</span>
            <el-icon :size="24" color="#409eff"><Collection /></el-icon>
          </div>
        </template>
        <div style="font-size: 32px; font-weight: bold; color: #303133">
          {{ stats.total_knowledge_bases }}
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>文档总数</span>
            <el-icon :size="24" color="#67c23a"><Document /></el-icon>
          </div>
        </template>
        <div style="font-size: 32px; font-weight: bold; color: #303133">
          {{ stats.total_documents }}
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>已索引</span>
            <el-icon :size="24" color="#409eff"><Select /></el-icon>
          </div>
        </template>
        <div style="font-size: 32px; font-weight: bold; color: #303133">
          {{ stats.total_indexed_documents }}
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>向量块总数</span>
            <el-icon :size="24" color="#e6a23c"><Connection /></el-icon>
          </div>
        </template>
        <div style="font-size: 32px; font-weight: bold; color: #303133">
          {{ stats.total_chunks }}
        </div>
      </el-card>
    </div>

    <!-- KB List Table -->
    <el-card v-if="!loading && stats.knowledge_bases?.length" shadow="never">
      <template #header>
        <span>知识库列表</span>
      </template>
      <el-table :data="stats.knowledge_bases" stripe style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="documents" label="文档数" width="100" align="center" />
        <el-table-column prop="indexed" label="已索引" width="100" align="center" />
        <el-table-column prop="chunks" label="向量块" width="100" align="center" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button text type="primary" @click="$router.push(`/knowledge-bases/${row.id}`)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Empty State -->
    <el-empty v-if="!loading && stats.total_knowledge_bases === 0" description="暂无知识库">
      <el-button type="primary" @click="$router.push('/knowledge-bases')">
        创建知识库
      </el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getOverviewStats } from '../api'

const loading = ref(true)
const stats = ref({
  total_knowledge_bases: 0,
  total_documents: 0,
  total_indexed_documents: 0,
  total_chunks: 0,
  knowledge_bases: [],
})

onMounted(async () => {
  try {
    const res = await getOverviewStats()
    stats.value = res.data
  } catch (e) {
    console.error('Failed to load stats:', e)
  } finally {
    loading.value = false
  }
})
</script>
