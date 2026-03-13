<template>
  <div class="search-bar">
    <div class="search-input-wrap">
      <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16">
        <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
      </svg>
      <input
        ref="inputRef"
        v-model="query"
        placeholder="搜索手册内容..."
        @input="onSearch"
        @keydown.escape="clearSearch"
      />
      <span v-if="query" class="clear-btn" @click="clearSearch">&times;</span>
    </div>
    <div v-if="results.length" class="search-results">
      <div
        v-for="r in results"
        :key="r.item.id"
        class="result-item"
        @click="selectResult(r.item)"
      >
        <div class="result-name">{{ r.item.name }}</div>
        <div v-if="r.item.preview" class="result-preview">{{ r.item.preview.slice(0, 120) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Fuse from 'fuse.js'

const emit = defineEmits(['select'])

const inputRef = ref(null)
const query = ref('')
const results = ref([])
let fuse = null

onMounted(async () => {
  const res = await fetch(import.meta.env.BASE_URL + 'data/search-index.json')
  const data = await res.json()
  fuse = new Fuse(data, {
    keys: [
      { name: 'name', weight: 2 },
      { name: 'preview', weight: 1 },
    ],
    threshold: 0.3,
    minMatchCharLength: 2,
  })
})

let debounceTimer = null
function onSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (!fuse || !query.value.trim()) {
      results.value = []
      return
    }
    results.value = fuse.search(query.value.trim(), { limit: 30 })
  }, 200)
}

function selectResult(item) {
  emit('select', item)
  query.value = ''
  results.value = []
}

function clearSearch() {
  query.value = ''
  results.value = []
}
</script>

<style scoped>
.search-bar {
  position: relative;
}
.search-input-wrap {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
  background: #fff;
}
.search-icon {
  flex-shrink: 0;
  color: #999;
  margin-right: 8px;
}
input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  background: transparent;
}
input::placeholder {
  color: #bbb;
}
.clear-btn {
  cursor: pointer;
  color: #999;
  font-size: 18px;
  padding: 0 4px;
}
.clear-btn:hover {
  color: #333;
}
.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 400px;
  overflow-y: auto;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
}
.result-item {
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}
.result-item:hover {
  background: #f5f5f5;
}
.result-name {
  font-size: 13px;
  font-weight: 500;
  color: #1565c0;
  margin-bottom: 2px;
}
.result-preview {
  font-size: 12px;
  color: #888;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
