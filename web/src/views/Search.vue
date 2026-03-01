<template>
  <div class="search-page">
    <div class="card">
      <h2>🔍 搜索书籍</h2>
      <div class="search-box">
        <input 
          v-model="keyword" 
          type="text" 
          placeholder="输入书名搜索..."
          @keyup.enter="handleSearch"
        />
        <button @click="handleSearch" :disabled="loading">搜索</button>
      </div>
    </div>

    <div v-if="loading" class="loading">搜索中...</div>
    
    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="results.length > 0" class="results">
      <div v-for="book in results" :key="book.id" class="book-item card">
        <div class="book-cover">
          <img v-if="book.bookImage" :src="book.bookImage" alt="封面" />
          <div v-else class="cover-placeholder">📖</div>
        </div>
        <div class="book-info">
          <h3>{{ book.bookTitle }}</h3>
          <p class="desc">{{ book.bookDesc }}</p>
          <div class="book-meta">
            <span v-if="book.bookAnchor" class="anchor">🎙️ {{ book.bookAnchor }}</span>
            <span class="heat">🔥 热度: {{ book.heat }}</span>
            <span>章节数: {{ book.count }}</span>
            <span v-if="book.updateStatus === 1" class="tag">完结</span>
            <span v-else-if="book.updateStatus === 2" class="tag serial">连载中</span>
          </div>
          <button class="btn-add" @click="addBook(book.id)">添加到我的书籍</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../utils/api.js'

const router = useRouter()
const keyword = ref('')
const results = ref([])
const loading = ref(false)
const error = ref('')

const handleSearch = async () => {
  if (!keyword.value.trim()) return
  
  loading.value = true
  error.value = ''
  results.value = []
  
  try {
    const res = await apiFetch(`/api/search?q=${encodeURIComponent(keyword.value)}`)
    const data = await res.json()
    
    if (data.error) {
      error.value = data.error
    } else {
      results.value = data.sort((a, b) => b.heat - a.heat)
    }
  } catch (e) {
    error.value = '搜索失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const addBook = async (bookId) => {
  try {
    const res = await apiFetch('/api/book/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: bookId })
    })
    const data = await res.json()
    window.showToast(data.message || data.error, data.message ? 'success' : 'error')
    if (data.message) router.push('/books')
  } catch (e) {
    window.showToast('添加失败: ' + e.message, 'error')
  }
}
</script>

<style scoped>
.search-page {
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

.search-box {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.search-box input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.search-box button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.search-box button:disabled {
  background: #ccc;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.book-item {
  display: flex;
  gap: 20px;
}

.book-cover {
  width: 120px;
  height: 160px;
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
  font-size: 48px;
}

.book-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.book-info h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.book-info .desc {
  color: #666;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  line-clamp: 3;
}

.book-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 10px 0;
}

.tag {
  background: #28a745;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.tag.serial {
  background: #fd7e14;
}

.heat {
  color: #ff6b6b;
  font-weight: bold;
}

.anchor {
  color: #6c757d;
  margin-right: 8px;
}

.btn-add {
  align-self: flex-start;
  padding: 8px 16px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #dc3545;
  padding: 10px;
  background: #f8d7da;
  border-radius: 4px;
}

@media (max-width: 600px) {
  .book-item {
    flex-direction: column;
  }
  
  .book-cover {
    width: 100%;
    height: 200px;
  }
  
  .book-cover img {
    object-fit: contain;
  }
}
</style>
