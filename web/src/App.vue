<template>
  <div class="app-container">
    <header class="header">
      <h1>📚 365听书管理</h1>
      <nav class="nav">
        <router-link to="/search">搜索</router-link>
        <router-link to="/books">书籍管理</router-link>
        <router-link to="/downloads">下载管理</router-link>
        <router-link to="/settings">⚙️ 设置</router-link>
      </nav>
    </header>
    <main class="main-content">
      <router-view />
    </main>
    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Toast from './components/Toast.vue'

const toastRef = ref(null)

const showToast = (text, type = 'info', duration = 3000) => {
  if (toastRef.value) {
    toastRef.value.show(text, type, duration)
  }
}

window.showToast = showToast
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  background: white;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header h1 {
  margin: 0 0 15px 0;
  color: #333;
}

.nav {
  display: flex;
  gap: 20px;
}

.nav a {
  text-decoration: none;
  color: #666;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.2s;
}

.nav a:hover {
  background: #f0f0f0;
}

.nav a.router-link-active {
  background: #007bff;
  color: white;
}

.main-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
