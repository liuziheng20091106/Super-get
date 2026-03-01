<template>
  <div class="settings-page">
    <div class="card">
      <div class="header-row">
        <h2>⚙️ 设置</h2>
        <button @click="loadConfig">🔄 刷新</button>
      </div>
    </div>
    <div style="margin: 16px 0;"></div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="settings-content">
      <div class="settings-grid">
        <div class="card">
          <h3>服务器设置</h3>
          <div class="form-group">
            <label>后端服务器地址</label>
            <div class="input-with-button">
              <input type="text" v-model="serverAddress" placeholder="例如: http://localhost:5000" />
              <button class="btn-small" @click="saveServerAddress">保存</button>
            </div>
            <p class="help-text">留空则使用默认代理地址。保存后刷新页面生效。</p>
          </div>
        </div>

        <div class="card">
          <h3>请求设置</h3>
          <div class="form-group">
            <label>请求间隔 (秒)</label>
            <input type="number" v-model.number="config.request_interval" step="0.1" min="0" />
          </div>
          <div class="form-group">
            <label>请求超时 (秒)</label>
            <input type="number" v-model.number="config.request_timeout" step="1" min="1" />
          </div>
          <div class="form-group">
            <label>最大重试次数</label>
            <input type="number" v-model.number="config.max_retries" step="1" min="0" />
          </div>
        </div>

        <div class="card">
          <h3>下载设置</h3>
          <div class="form-group">
            <label>最大工作线程数</label>
            <input type="number" v-model.number="config.max_workers" step="1" min="1" />
          </div>
          <div class="form-group">
            <label>下载超时 (秒)</label>
            <input type="number" v-model.number="config.download_timeout" step="1" min="1" />
          </div>
          <div class="form-group">
            <label>默认下载目录</label>
            <input type="text" v-model="config.default_download_dir" />
          </div>
        </div>

        <div class="card">
          <h3>定时任务设置</h3>
          <div class="form-group">
            <label>自动同步间隔 (小时)</label>
            <input type="number" v-model.number="config.auto_sync" step="0.1" min="0.1" />
          </div>
        </div>

        <div class="card">
          <h3>日志设置</h3>
          <div class="form-group">
            <label>日志级别(重启生效)</label>
            <select v-model="config.log_level">
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>

        <div class="card info-card">
          <h3>关于</h3>
          <p>版本: {{ config.version }}</p>
        </div>
      </div>

      <div class="actions">
        <button class="btn-primary" @click="saveConfig">💾 保存设置</button>
      </div>
    </div>

    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Toast from '../components/Toast.vue'
import { getApiBaseUrl, setApiBaseUrl, apiFetch } from '../utils/api.js'

const loading = ref(false)
const toastRef = ref(null)
const serverAddress = ref('')
const config = ref({
  version: '',
  request_interval: 1,
  request_timeout: 10,
  max_retries: 3,
  max_workers: 2,
  download_timeout: 60,
  default_download_dir: 'downloads',
  log_level: 'INFO',
  auto_sync: 1.0
})

const loadConfig = async () => {
  loading.value = true
  try {
    const res = await apiFetch('/api/config')
    if (res.ok) {
      config.value = await res.json()
    }
  } catch (e) {
    if (toastRef.value) {
      toastRef.value.show('加载配置失败')
    }
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  const fields = [
    'request_interval',
    'request_timeout',
    'max_retries',
    'max_workers',
    'download_timeout',
    'default_download_dir',
    'log_level',
    'auto_sync'
  ]

  for (const key of fields) {
    try {
      const res = await apiFetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: config.value[key] })
      })
      if (!res.ok) {
        throw new Error()
      }
    } catch (e) {
      if (toastRef.value) {
        toastRef.value.show(`保存 ${key} 失败`)
      }
      return
    }
  }

  if (toastRef.value) {
    toastRef.value.show('设置已保存')
  }
}

onMounted(() => {
  serverAddress.value = getApiBaseUrl()
  loadConfig()
})

const saveServerAddress = () => {
  setApiBaseUrl(serverAddress.value)
  if (toastRef.value) {
    toastRef.value.show('服务器地址已保存，刷新页面后生效')
  }
}
</script>

<style scoped>
.settings-page {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-content {
  display: flex;
  flex-direction: column;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .settings-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-row h2 {
  margin: 0;
  font-size: 20px;
}

.settings-content h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #666;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #4CAF50;
}

.input-with-button {
  display: flex;
  gap: 8px;
}

.input-with-button input {
  flex: 1;
}

.input-with-button .btn-small {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.input-with-button .btn-small:hover {
  background: #0056b3;
}

.help-text {
  margin-top: 6px;
  font-size: 12px;
  color: #999;
}

.info-card p {
  margin: 8px 0;
  font-size: 14px;
  color: #666;
}

.actions {
  margin-top: 24px;
  text-align: center;
}

.actions button {
  padding: 12px 32px;
  font-size: 16px;
}

.btn-primary {
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 10px 20px;
  font-size: 14px;
}

.btn-primary:hover {
  background: #45a049;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
