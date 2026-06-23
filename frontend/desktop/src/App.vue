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
  </header>
  <main class="app-main">
    <router-view />
  </main>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 12px;
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
.app-main {
  padding: 24px;
}
@media (max-width: 640px) {
  .app-header { padding: 10px 14px; }
  .brand { font-size: 1.1rem; }
  .app-main { padding: 14px; }
}
</style>
