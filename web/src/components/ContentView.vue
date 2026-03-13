<template>
  <main class="content-view">
    <div v-if="loading" class="status">加载中...</div>
    <div v-else-if="node" class="content">
      <h1>{{ node.name }}</h1>
      <div class="text-content">{{ content }}</div>
    </div>
    <div v-else class="placeholder">
      <div class="hero">
        <h1>机械设计手册</h1>
        <p>电子版 · Web 版</p>
        <p class="hint">从左侧目录选择内容，或使用搜索栏查找</p>
      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  node: { type: Object, default: null },
})

const content = ref('')
const loading = ref(false)

// 内容缓存：按章节文件缓存
const chapterCache = {}

async function loadContent(contentId) {
  if (!contentId) {
    content.value = ''
    return
  }
  const chapter = contentId.split('\\')[0] || 'misc'

  if (!chapterCache[chapter]) {
    loading.value = true
    try {
      const res = await fetch(import.meta.env.BASE_URL + `data/chapters/${chapter}.json`)
      chapterCache[chapter] = await res.json()
    } catch {
      content.value = '内容加载失败'
      loading.value = false
      return
    }
  }
  loading.value = false
  content.value = chapterCache[chapter][contentId] || '暂无内容'
}

watch(
  () => props.node,
  (node) => {
    if (node?.contentId) {
      loadContent(node.contentId)
    } else {
      content.value = ''
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.content-view {
  flex: 1;
  height: 100vh;
  overflow-y: auto;
  padding: 32px 48px;
  background: #fff;
}
.content h1 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 24px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #e0e0e0;
}
.text-content {
  font-size: 14px;
  line-height: 2;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.hero {
  text-align: center;
  color: #999;
}
.hero h1 {
  font-size: 28px;
  color: #555;
  margin: 0 0 8px;
  border: none;
}
.hero p {
  margin: 4px 0;
  font-size: 16px;
}
.hero .hint {
  margin-top: 24px;
  font-size: 14px;
  color: #bbb;
}
.status {
  padding: 40px;
  text-align: center;
  color: #999;
}
</style>
