<template>
  <div class="chapters-page">
    <div class="card">
      <div class="header-row">
        <div>
          <router-link to="/books" class="back-link">← 返回书籍列表</router-link>
          <h2>{{ bookTitle }}</h2>
          <p class="meta">共 {{ chapters.length }} 章，已选 {{ selectedChapters.length }} 章</p>
        </div>
        <div class="actions">
          <button @click="updateChapters">🔄 更新章节</button>
          <button class="btn-success" @click="downloadAll">⬇️ 下载全部</button>
          <button 
            v-if="selectedChapters.length > 0"
            class="btn-primary" 
            @click="downloadSelected"
          >
            ⬇️ 下载选中 ({{ selectedChapters.length }})
          </button>
          <button 
            :class="isInTimer ? 'btn-warning' : 'btn-timer'" 
            @click="toggleTimer"
          >
            {{ isInTimer ? '⏹️ 停止自动更新' : '▶️ 开启自动更新' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="chapter-list">
      <div class="list-header">
        <label class="checkbox-label">
          <input 
            type="checkbox" 
            :checked="isAllSelected" 
            :indeterminate="isIndeterminate"
            @change="toggleAll"
          />
          全选
        </label>
        <span class="select-tip">仅可选中未下载的章节</span>
      </div>
      <div 
        v-for="chapter in chapters" 
        :key="chapter.chapterid" 
        class="chapter-item"
        :class="{ downloaded: chapter.downloaded }"
      >
        <div class="chapter-info">
          <label class="checkbox-label" :class="{ disabled: chapter.downloaded }">
            <input 
              type="checkbox" 
              :checked="selectedChapters.includes(chapter.chapterid)"
              :disabled="chapter.downloaded"
              @change="toggleChapter(chapter.chapterid)"
            />
            <span class="position">{{ chapter.position }}</span>
            <span class="title">{{ chapter.title }}</span>
          </label>
        </div>
        <div class="chapter-actions">
          <span class="status">{{ chapter.downloaded ? '✓ 已下载' : '未下载' }}</span>
          <button 
            v-if="!chapter.downloaded" 
            class="btn-small"
            @click="downloadChapter(chapter.chapterid)"
          >
            ⬇️
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiFetch } from '../utils/api.js'

const route = useRoute()
const bookId = route.params.id
const bookTitle = ref('')
const chapters = ref([])
const loading = ref(false)
const isInTimer = ref(false)
const selectedChapters = ref([])

const isAllSelected = computed(() => {
  const undownloaded = chapters.value.filter(c => !c.downloaded)
  return undownloaded.length > 0 && undownloaded.every(c => selectedChapters.value.includes(c.chapterid))
})

const isIndeterminate = computed(() => {
  const undownloaded = chapters.value.filter(c => !c.downloaded)
  const selected = undownloaded.filter(c => selectedChapters.value.includes(c.chapterid))
  return selected.length > 0 && selected.length < undownloaded.length
})

const toggleChapter = (chapterId) => {
  const index = selectedChapters.value.indexOf(chapterId)
  if (index === -1) {
    selectedChapters.value.push(chapterId)
  } else {
    selectedChapters.value.splice(index, 1)
  }
}

const toggleAll = () => {
  if (isAllSelected.value) {
    selectedChapters.value = []
  } else {
    const undownloaded = chapters.value.filter(c => !c.downloaded)
    selectedChapters.value = undownloaded.map(c => c.chapterid)
  }
}

const loadChapters = async () => {
  loading.value = true
  try {
    const bookRes = await apiFetch(`/api/book/${bookId}`)
    const book = await bookRes.json()
    bookTitle.value = book.title
    
    const chaptersRes = await apiFetch(`/api/book/${bookId}/chapters`)
    chapters.value = await chaptersRes.json()
    
    const timerRes = await apiFetch('/api/timer/status')
    const timerData = await timerRes.json()
    isInTimer.value = (timerData.book_ids || []).includes(parseInt(bookId))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const updateChapters = async () => {
  await apiFetch(`/api/book/${bookId}/chapters`, { method: 'POST' })
  loadChapters()
}

const downloadChapter = async (chapterId) => {
  await apiFetch('/api/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: parseInt(bookId), chapter_ids: [chapterId] })
  })
  window.showToast('已开始下载', 'success')
}

const downloadAll = async () => {
  await apiFetch('/api/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: parseInt(bookId) })
  })
  window.showToast('已开始下载', 'success')
}

const downloadSelected = async () => {
  if (selectedChapters.value.length === 0) {
    window.showToast('请先选择章节', 'warning')
    return
  }
  await apiFetch('/api/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      book_id: parseInt(bookId), 
      chapter_ids: selectedChapters.value 
    })
  })
  window.showToast(`已开始下载 ${selectedChapters.value.length} 个章节`, 'success')
  selectedChapters.value = []
}

const toggleTimer = async () => {
  try {
    if (isInTimer.value) {
      const res = await apiFetch('/api/timer/book/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: parseInt(bookId) })
      })
      const data = await res.json()
      if (!res.ok) {
        window.showToast(data.detail || '操作失败', 'error')
      } else {
        window.showToast(data.message || '已关闭自动更新', 'info')
      }
    } else {
      const res = await apiFetch('/api/timer/book/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: parseInt(bookId) })
      })
      const data = await res.json()
      if (!res.ok) {
        window.showToast(data.detail || '操作失败', 'error')
      } else {
        window.showToast(data.message || '已开启自动更新', 'success')
      }
    }
    loadChapters()
  } catch (e) {
    window.showToast('操作失败: ' + e.message, 'error')
  }
}

onMounted(() => {
  loadChapters()
})
</script>

<style scoped>
.chapters-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 15px;
}

.back-link {
  color: #666;
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  color: #007bff;
}

.header-row h2 {
  margin: 10px 0 5px 0;
}

.meta {
  color: #999;
  font-size: 14px;
  margin: 0;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.actions button {
  padding: 8px 16px;
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
  background: #007bff !important;
}

.btn-warning {
  background: #fd7e14 !important;
}

.btn-timer {
  background: #6c757d !important;
}

.chapter-list {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chapter-item {
  padding: 12px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.chapter-item:last-child {
  border-bottom: none;
}

.chapter-item.downloaded {
  color: #28a745;
  background: #f0fff4;
}

.list-header {
  padding: 12px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
}

.checkbox-label.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-label.disabled input[type="checkbox"] {
  cursor: not-allowed;
}

.select-tip {
  color: #999;
  font-size: 12px;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 15px;
  flex: 1;
  min-width: 0;
}

.position {
  color: #999;
  font-size: 14px;
  min-width: 30px;
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.status {
  color: #999;
  font-size: 13px;
  white-space: nowrap;
}

.chapter-item.downloaded .status {
  color: #28a745;
}

.btn-small {
  padding: 4px 8px;
  font-size: 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

@media (max-width: 600px) {
  .chapter-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .chapter-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
