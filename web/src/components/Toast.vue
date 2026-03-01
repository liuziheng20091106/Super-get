<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div 
        v-for="msg in messages" 
        :key="msg.id" 
        class="toast"
        :class="msg.type"
      >
        {{ msg.text }}
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const messages = ref([])
let id = 0

const show = (text, type = 'info', duration = 3000) => {
  const msgId = ++id
  messages.value.push({ id: msgId, text, type })
  setTimeout(() => {
    messages.value = messages.value.filter(m => m.id !== msgId)
  }, duration)
}

defineExpose({ show })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  padding: 12px 20px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  white-space: nowrap;
}

.toast.info {
  background: #007bff;
}

.toast.success {
  background: #28a745;
}

.toast.warning {
  background: #fd7e14;
}

.toast.error {
  background: #dc3545;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
