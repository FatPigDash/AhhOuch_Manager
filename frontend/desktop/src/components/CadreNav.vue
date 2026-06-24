<script setup>
// 幹部內的子頁籤：美容師資訊 / 班表（各自獨立頁面，S1）
</script>

<template>
  <nav class="cadre-nav">
    <router-link :to="{ name: 'cadre-list' }" class="tab">資訊卡片</router-link>
    <router-link :to="{ name: 'schedule-list' }" class="tab">班表</router-link>
    <router-link :to="{ name: 'publish-settings' }" class="tab">發布設定</router-link>
  </nav>
</template>

<style scoped>
.cadre-nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
.tab {
  padding: 6px 16px;
  border-radius: 8px;
  background: #e4e7eb;
  color: #486581;
  text-decoration: none;
  font-size: 0.95rem;
}
.tab.router-link-active { background: #102a43; color: #fff; font-weight: 600; }
</style>
