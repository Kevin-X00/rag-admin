<template>
  <div class="app-container">
    <!-- Sidebar -->
    <div class="sidebar">
      <div class="sidebar-logo">
        <el-icon style="margin-right: 8px"><Files /></el-icon>
        RAG Admin
      </div>
      <div class="sidebar-menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-menu-item"
          :class="{ active: $route.path === item.path }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.name }}</span>
        </router-link>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-area">
      <div class="page-header">
        <el-icon><component :is="currentIcon" /></el-icon>
        <span>{{ currentTitle }}</span>
      </div>
      <div class="page-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { path: '/', name: '总览', icon: 'DataAnalysis' },
  { path: '/knowledge-bases', name: '知识库管理', icon: 'Collection' },
  { path: '/qa-test', name: '问答测试', icon: 'ChatLineSquare' },
]

const currentTitle = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item ? item.name : 'RAG Admin'
})

const currentIcon = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item ? item.icon : 'Files'
})
</script>
