<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import CadreNav from "../components/CadreNav.vue";

const router = useRouter();
const cards = ref([]);
const newName = ref("");
const error = ref("");

async function load() {
  try {
    cards.value = await api.listCadreCards();
  } catch (e) {
    error.value = e.message;
  }
}
async function addCard() {
  const name = newName.value.trim();
  if (!name) return;
  try {
    await api.createCadreCard(name);
    newName.value = "";
    await load();
  } catch (e) {
    error.value = e.message;
  }
}
async function removeCard(card) {
  if (!confirm(`刪除資訊卡片「${card.name}」？`)) return;
  try {
    await api.deleteCadreCard(card.id);
    await load();
  } catch (e) {
    error.value = e.message;
  }
}
function open(card) {
  router.push({ name: "cadre-card", params: { id: card.id } });
}
onMounted(load);
</script>

<template>
  <section>
    <CadreNav />
    <h1>美容師資訊卡片</h1>
    <p v-if="error" class="error">{{ error }}</p>

    <form class="add-bar" @submit.prevent="addCard">
      <input
        v-model="newName"
        placeholder="輸入名字或編號即可建立"
        maxlength="100"
      />
      <button type="submit">＋ 新增資訊卡片</button>
    </form>

    <p v-if="cards.length === 0" class="empty">尚無資訊卡片，請先新增。</p>

    <ul class="grid">
      <li v-for="card in cards" :key="card.id" class="card">
        <div class="body" @click="open(card)">
          <div class="cover" :class="{ placeholder: !card.cover_image }">
            <img v-if="card.cover_image" :src="card.cover_image" alt="" />
            <span v-else>無封面</span>
          </div>
          <h3>{{ card.name }}</h3>
          <p v-if="card.short_intro" class="meta">{{ card.short_intro }}</p>
        </div>
        <div class="actions">
          <button class="ghost" @click.stop="open(card)">編輯／發布</button>
          <button class="danger" @click.stop="removeCard(card)">刪除</button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
h1 {
  margin-top: 0;
}
.error {
  color: #cf1124;
}
.empty {
  color: #829ab1;
}
.add-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}
.add-bar input {
  flex: 1;
  max-width: 360px;
  padding: 8px 12px;
  border: 1px solid #cbd2d9;
  border-radius: 8px;
}
.add-bar button {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: #2680c2;
  color: #fff;
}
.grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
}
.body {
  cursor: pointer;
}
.cover {
  height: 260px;
  background: #f0f4f8;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cover.placeholder span {
  color: #9fb3c8;
  font-size: 0.85rem;
}
.card h3 {
  margin: 10px 14px 4px;
}
.meta {
  margin: 0 14px 10px;
  color: #486581;
  font-size: 0.9rem;
}
.actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 14px;
  margin-top: auto;
}
.actions button {
  font-size: 0.85rem;
  padding: 6px 10px;
  border: none;
  border-radius: 8px;
}
.ghost {
  background: #e4e7eb;
  color: #334e68;
}
.danger {
  background: #fbeae5;
  color: #cf1124;
}
</style>
