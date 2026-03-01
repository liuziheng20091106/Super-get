<template>
  <div class="books-page">
    <div class="card">
      <div class="header-row">
        <h2>📖 我的书籍</h2>
        <button @click="loadBooks">🔄 刷新</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="books.length === 0" class="empty">
      <p>暂无书籍</p>
      <router-link to="/search">
        <button class="btn-primary">去搜索</button>
      </router-link>
    </div>

    <div v-else class="book-list">
      <div 
        v-for="book in books" 
        :key="book.id" 
        class="book-card"
        @click="goToChapters(book.id)"
      >
        <div class="book-cover">
          <img v-if="book.image" :src="book.image" alt="封面" />
          <div v-else class="cover-placeholder">📖</div>
        </div>
        <div class="book-info">
          <div class="book-header">
            <h3>{{ book.title }}</h3>
            <div class="tags">
              <span v-if="book.updateStatus === 1" class="tag">完结</span>
              <span v-else-if="book.updateStatus === 2" class="tag serial">连载中</span>
            </div>
          </div>
          <p v-if="book.anchor" class="anchor">🎙️ {{ book.anchor }}</p>
          <p class="desc">{{ book.desc || '暂无简介' }}</p>
          <div class="book-footer">
            <span class="meta">章节数: {{ book.count }}</span>
            <span class="meta">已下载: {{ book.downloaded || 0 }}/{{ book.count || 0 }}</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (book.progress || 0) + '%' }"></div>
            </div>
          </div>
        </div>
        <div class="book-actions" @click.stop>
          <button class="btn-success" @click="downloadBook(book.id)">⬇️ 下载</button>
          <button 
            :class="isInTimer(book.id) ? 'btn-warning' : 'btn-timer'" 
            @click="toggleTimer(book)"
          >
            {{ isInTimer(book.id) ? '⏸️ 自动' : '▶️ 自动' }}
          </button>
          <button class="btn-danger" @click="removeBook(book.id)">🗑️</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../utils/api.js'

const router = useRouter()
const books = ref([])
const loading = ref(false)
const timerBookIds = ref([])

const loadBooks = async () => {
  try {
    const res = await apiFetch('/api/books')
    const newBooks = await res.json()
    
    for (const book of newBooks) {
      const detailRes = await apiFetch(`/api/book/${book.id}`)
      const detail = await detailRes.json()
      
      const existingBook = books.value.find(b => b.id === book.id)
      if (existingBook) {
        existingBook.count = book.count
        existingBook.updateStatus = book.updateStatus
        existingBook.image = book.image
        existingBook.desc = book.desc
        existingBook.title = book.title
        existingBook.downloaded = detail.downloaded
        existingBook.progress = detail.progress
      } else {
        books.value.push({
          ...book,
          downloaded: detail.downloaded,
          progress: detail.progress
        })
      }
    }
    
    const timerRes = await apiFetch('/api/timer/status')
    const timerData = await timerRes.json()
    timerBookIds.value = timerData.book_ids || []
    loading.value = false
  } catch (e) {
    console.error(e)
  }
}

const goToChapters = (bookId) => {
  router.push(`/chapters/${bookId}`)
}

const isInTimer = (bookId) => {
  return timerBookIds.value.includes(bookId)
}

const downloadBook = async (bookId) => {
  await apiFetch('/api/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId })
  })
  window.showToast('已开始下载', 'success')
}

const toggleTimer = async (book) => {
  try {
    if (isInTimer(book.id)) {
      const res = await apiFetch('/api/timer/book/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: book.id })
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
        body: JSON.stringify({ book_id: book.id })
      })
      const data = await res.json()
      if (!res.ok) {
        window.showToast(data.detail || '操作失败', 'error')
      } else {
        window.showToast(data.message || '已开启自动更新', 'success')
      }
    }
    loadBooks()
  } catch (e) {
    window.showToast('操作失败: ' + e.message, 'error')
  }
}

const removeBook = async (bookId) => {
  if (!confirm('确定要删除这本书吗?')) return
  await apiFetch(`/api/book/${bookId}`, { method: 'DELETE' })
  window.showToast('删除成功', 'success')
  loadBooks()
}

let timer = null
onMounted(() => {
  loadBooks()
  loading.value = true
  timer = setInterval(loadBooks, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.books-page {
  padding: 20px;
  max-width: 800px;
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
  align-items: center;
}

.header-row h2 {
  margin: 0;
}

.header-row button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.book-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  gap: 15px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.book-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.book-cover {
  width: 80px;
  height: 110px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f5f5;
}

.book-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.book-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.book-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.book-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tags {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

.tag {
  background: #28a745;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.tag.serial {
  background: #fd7e14;
}

.desc {
  color: #666;
  font-size: 13px;
  margin: 8px 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-clamp: 2;
}

.anchor {
  color: #6c757d;
  font-size: 13px;
  margin: 4px 0;
}

.book-footer {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.meta {
  color: #999;
  font-size: 12px;
}

.progress-bar {
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
  flex: 1;
  min-width: 100px;
}

.progress-fill {
  height: 100%;
  background: #28a745;
  transition: width 0.3s;
}

.book-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.book-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: #007bff;
  color: white;
  white-space: nowrap;
}

.btn-success {
  background: #28a745 !important;
}

.btn-warning {
  background: #fd7e14 !important;
}

.btn-timer {
  background: #6c757d !important;
}

.btn-danger {
  background: #dc3545 !important;
}

.btn-primary {
  background: #007bff !important;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty p {
  margin-bottom: 15px;
}

@media (max-width: 600px) {
  .book-card {
    flex-direction: column;
  }
  
  .book-cover {
    width: 100%;
    height: 180px;
  }
  
  .book-actions {
    flex-direction: row;
    justify-content: flex-end;
  }
}
</style>
