<template>
  <div class="downloads-page">
    <!-- 下载管理 -->
    <div class="card">
      <h2>⬇️ 下载管理</h2>
      <div class="control-panel">
        <button 
          v-if="!downloadStatus.is_running || downloadStatus.is_paused" 
          class="btn-success" 
          @click="startDownload"
        >
          ▶️ 开始下载
        </button>
        <button v-if="downloadStatus.is_running && !downloadStatus.is_paused" @click="pauseDownload">
          ⏸️ 暂停
        </button>
        <button v-if="downloadStatus.is_running && downloadStatus.is_paused" class="btn-primary" @click="resumeDownload">
          ▶️ 继续
        </button>
        <button class="btn-danger" @click="cancelDownload">⏹️ 取消</button>
      </div>
      
      <div class="status-grid">
        <div class="status-item">
          <span class="label">总任务</span>
          <span class="value">{{ downloadStatus.total }}</span>
        </div>
        <div class="status-item">
          <span class="label">待下载</span>
          <span class="value">{{ downloadStatus.pending }}</span>
        </div>
        <div class="status-item">
          <span class="label">下载中</span>
          <span class="value">{{ downloadStatus.downloading }}</span>
        </div>
        <div class="status-item">
          <span class="label">已完成</span>
          <span class="value success">{{ downloadStatus.completed }}</span>
        </div>
        <div class="status-item">
          <span class="label">失败</span>
          <span class="value danger">{{ downloadStatus.failed }}</span>
        </div>
        <div class="status-item">
          <span class="label">状态</span>
          <span class="value">{{ statusText }}</span>
        </div>
      </div>
    </div>

    <!-- 定时任务 -->
    <div class="card">
      <h2>⏰ 定时同步任务</h2>
      <div class="control-panel">
        <button 
          v-if="!timerStatus.is_running" 
          class="btn-success" 
          @click="startTimer"
        >
          ▶️ 启动定时任务
        </button>
        <button v-else class="btn-danger" @click="stopTimer">
          ⏹️ 停止定时任务
        </button>
      </div>
      
      <div class="timer-info">
        <div class="info-item">
          <span class="label">状态</span>
          <span class="value">{{ timerStatus.is_running ? '运行中' : '已停止' }}</span>
        </div>
        <div class="info-item">
          <span class="label">同步间隔</span>
          <span class="value">{{ timerStatus.interval_hours }} 小时</span>
        </div>
        <div class="info-item">
          <span class="label">监控书籍</span>
          <span class="value">{{ timerStatus.book_ids?.length || 0 }} 本</span>
        </div>
      </div>

      <div v-if="timerStatus.book_ids?.length > 0" class="timer-books">
        <h4>监控中的书籍ID:</h4>
        <div class="book-tags">
          <span v-for="id in timerStatus.book_ids" :key="id" class="book-tag">
            {{ id }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiFetch } from '../utils/api.js'

const downloadStatus = ref({
  total: 0,
  pending: 0,
  downloading: 0,
  paused: 0,
  completed: 0,
  failed: 0,
  is_running: false,
  is_paused: false
})

const timerStatus = ref({
  is_running: false,
  interval_hours: 1.0,
  book_ids: []
})

const statusText = computed(() => {
  if (!downloadStatus.value.is_running) return '已停止'
  if (downloadStatus.value.is_paused) return '已暂停'
  return '运行中'
})

const fetchDownloadStatus = async () => {
  try {
    const res = await apiFetch('/api/download/status')
    downloadStatus.value = await res.json()
  } catch (e) {
    console.error(e)
  }
}

const fetchTimerStatus = async () => {
  try {
    const res = await apiFetch('/api/timer/status')
    timerStatus.value = await res.json()
  } catch (e) {
    console.error(e)
  }
}

const startDownload = async () => {
  await apiFetch('/api/download/start', { method: 'POST' })
  fetchDownloadStatus()
}

const pauseDownload = async () => {
  await apiFetch('/api/download/pause', { method: 'POST' })
  fetchDownloadStatus()
}

const resumeDownload = async () => {
  await apiFetch('/api/download/resume', { method: 'POST' })
  fetchDownloadStatus()
}

const cancelDownload = async () => {
  if (!confirm('确定要取消所有下载吗?')) return
  await apiFetch('/api/download/cancel', { method: 'POST' })
  fetchDownloadStatus()
}

const startTimer = async () => {
  const res = await apiFetch('/api/timer/start', { method: 'POST' })
  const data = await res.json()
  if (!res.ok) {
    window.showToast(data.detail || '启动失败', 'error')
  } else {
    window.showToast(data.message || '定时任务已启动', 'success')
  }
  fetchTimerStatus()
}

const stopTimer = async () => {
  await apiFetch('/api/timer/stop', { method: 'POST' })
  window.showToast('定时任务已停止', 'info')
  fetchTimerStatus()
}

let timer = null
onMounted(() => {
  fetchDownloadStatus()
  fetchTimerStatus()
  timer = setInterval(() => {
    fetchDownloadStatus()
    fetchTimerStatus()
  }, 2000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.downloads-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.card h2 {
  margin: 0 0 15px 0;
}

.control-panel {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.control-panel button {
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: #007bff;
  color: white;
  white-space: nowrap;
}

.btn-success {
  background: #28a745 !important;
}

.btn-primary {
  background: #17a2b8 !important;
}

.btn-danger {
  background: #dc3545 !important;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
}

.status-item, .info-item {
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-item .label, .info-item .label {
  color: #666;
  font-size: 12px;
}

.status-item .value, .info-item .value {
  font-weight: bold;
  font-size: 16px;
}

.status-item .value.success {
  color: #28a745;
}

.status-item .value.danger {
  color: #dc3545;
}

.timer-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 15px;
}

.timer-books h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.book-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.book-tag {
  background: #e9ecef;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
}

@media (max-width: 600px) {
  .status-grid, .timer-info {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
