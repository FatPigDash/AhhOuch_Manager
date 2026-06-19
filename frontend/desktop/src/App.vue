<script setup>
import { ref, onMounted } from 'vue'
import { api } from './api'

const title = ref('AhhOuch')

onMounted(async () => {
  try {
    const meta = await api.meta()
    title.value = meta.title
    document.title = meta.title
  } catch (_) { /* 後端未連線時沿用預設標題 */ }
})
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="brand">{{ title }}</router-link>
    <span class="role">客人</span>
  </header>
  <main class="app-main">
    <router-view />
  </main>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 14px 24px;
  background: #102a43;
  color: #fff;
}
.brand {
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
}
.role {
  font-size: 0.85rem;
  background: #334e68;
  padding: 2px 10px;
  border-radius: 999px;
}
.app-main {
  padding: 24px;
}
</style>
