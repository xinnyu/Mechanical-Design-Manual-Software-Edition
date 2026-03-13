<template>
  <main class="content-view">
    <div v-if="loading" class="status">加载中...</div>
    <div v-else-if="node" class="content">
      <h1>{{ node.name }}</h1>
      <div class="text-content" v-html="formattedContent"></div>
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
import { ref, computed, watch } from 'vue'

const props = defineProps({
  node: { type: Object, default: null },
})

const content = ref('')
const loading = ref(false)

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

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/**
 * 格式化内容：
 * - 数据已在 Python 端预处理：\n = 行分隔, \t = 列分隔
 * - 连续的含 tab 行 → 合并渲染为一个 HTML table
 * - 纯文本行 → 普通段落
 */
const formattedContent = computed(() => {
  if (!content.value) return ''
  return formatText(content.value)
})

function formatText(text) {
  const lines = text.split('\n')
  const result = []
  let tableRows = []

  function flushTable() {
    if (tableRows.length === 0) return
    result.push(renderTable(tableRows))
    tableRows = []
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      flushTable()
      continue
    }

    if (trimmed.includes('\t')) {
      tableRows.push(trimmed.split('\t'))
    } else {
      flushTable()
      result.push(`<p class="para">${escapeHtml(trimmed)}</p>`)
    }
  }
  flushTable()

  return result.join('')
}

/**
 * 将多行 tab 分隔数据渲染为 HTML 表格。
 * 第一行作为表头，其余为数据行。
 */
function renderTable(rows) {
  if (rows.length === 0) return ''

  // 找最大列数
  let maxCols = 0
  for (const row of rows) {
    if (row.length > maxCols) maxCols = row.length
  }

  // 判断第一行是否为表头（含非数值内容）
  const firstRow = rows[0]
  const isHeaderRow = firstRow.some(c => c.trim() && !/^-?\d*\.?\d+$/.test(c.trim()) && c.trim() !== '-')

  let html = '<div class="table-wrap"><table class="data-table">'

  let dataStart = 0
  if (isHeaderRow) {
    html += '<thead><tr>'
    for (const cell of firstRow) {
      const colspan = firstRow.length < maxCols && firstRow.indexOf(cell) === 0
        ? '' : ''
      html += `<th>${escapeHtml(cell)}</th>`
    }
    html += '</tr></thead>'
    dataStart = 1
  }

  if (rows.length > dataStart) {
    html += '<tbody>'
    for (let i = dataStart; i < rows.length; i++) {
      html += '<tr>'
      for (const cell of rows[i]) {
        html += `<td>${escapeHtml(cell)}</td>`
      }
      html += '</tr>'
    }
    html += '</tbody>'
  }

  html += '</table></div>'
  return html
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
.content :deep(.para) {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin: 8px 0;
}
.content :deep(.data-block) {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 16px 20px;
  margin: 12px 0;
  overflow-x: auto;
  white-space: pre;
}
.content :deep(.table-wrap) {
  overflow-x: auto;
  margin: 12px 0;
}
.content :deep(.data-table) {
  border-collapse: collapse;
  font-size: 13px;
  width: auto;
  min-width: 400px;
}
.content :deep(.data-table th),
.content :deep(.data-table td) {
  border: 1px solid #dee2e6;
  padding: 6px 12px;
  text-align: left;
  white-space: nowrap;
}
.content :deep(.data-table th) {
  background: #f1f3f5;
  font-weight: 600;
  color: #333;
}
.content :deep(.data-table td) {
  color: #444;
}
.content :deep(.data-table tbody tr:hover) {
  background: #f8f9fa;
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
