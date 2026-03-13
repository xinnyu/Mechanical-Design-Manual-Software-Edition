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
 * - 数据中 \t = 原始表格单元格分隔
 * - \n = 段落/大块分隔
 * - 含 tab 的行 → 渲染为 HTML table
 * - 纯文本行 → 普通段落
 */
const formattedContent = computed(() => {
  if (!content.value) return ''
  return formatText(content.value)
})

function formatText(text) {
  const paragraphs = text.split('\n')
  const result = []

  for (const para of paragraphs) {
    const trimmed = para.trim()
    if (!trimmed) continue

    if (trimmed.includes('\t')) {
      // 含 tab 的行 → 表格数据
      result.push(renderTabularLine(trimmed))
    } else {
      // 普通文本
      result.push(`<p class="para">${escapeHtml(trimmed)}</p>`)
    }
  }

  return result.join('')
}

/**
 * 将 tab 分隔的行渲染为 HTML 表格。
 * 检测表头（第一组 cells）和数据区域，按列数自动分行。
 */
function renderTabularLine(line) {
  const cells = line.split('\t')

  // 过滤尾部空 cell
  while (cells.length > 0 && cells[cells.length - 1].trim() === '') {
    cells.pop()
  }

  if (cells.length <= 1) {
    return `<p class="para">${escapeHtml(cells[0] || '')}</p>`
  }

  // 检测列数：找第一组连续非空 cells 作为表头来推断
  // 如果有空字符串 cell，可能是合并单元格的标志
  const colCount = detectColumnCount(cells)

  if (colCount <= 1 || colCount > 20) {
    // 无法推断列数，用 pre 展示
    const text = cells.filter(c => c.trim()).join('  ')
    return `<pre class="data-block">${escapeHtml(text)}</pre>`
  }

  // 按列数分行
  const rows = []
  for (let i = 0; i < cells.length; i += colCount) {
    rows.push(cells.slice(i, i + colCount))
  }

  // 渲染为 table
  let html = '<div class="table-wrap"><table class="data-table">'

  // 第一行作为表头
  if (rows.length > 0) {
    html += '<thead><tr>'
    for (const cell of rows[0]) {
      html += `<th>${escapeHtml(cell)}</th>`
    }
    html += '</tr></thead>'
  }

  // 数据行
  if (rows.length > 1) {
    html += '<tbody>'
    for (let i = 1; i < rows.length; i++) {
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

/**
 * 推断列数：从表头区域的非空 cells 模式推断。
 * 策略：找到第一个空字符串的位置作为列数候选，
 * 如果没有空字符串，尝试常见列数。
 */
function detectColumnCount(cells) {
  // 方法1：如果前面几个 cells 后出现空 cell，可能标志表头结束
  // 但空 cell 也可能是合并单元格

  // 方法2：尝试不同列数，找最干净的分割
  // 评分标准：行尾空 cell 最少的列数
  const maxCols = Math.min(15, cells.length)
  let bestCols = 0
  let bestScore = -1

  for (let cols = 2; cols <= maxCols; cols++) {
    if (cells.length % cols !== 0) continue

    const numRows = cells.length / cols
    if (numRows < 2) continue

    // 评分：非空 cell 的比例
    let nonEmpty = 0
    for (const cell of cells) {
      if (cell.trim()) nonEmpty++
    }
    const score = nonEmpty / cells.length

    // 偏好较小的列数（更可能是正确的）
    const adjustedScore = score + (1 / cols) * 0.1

    if (adjustedScore > bestScore) {
      bestScore = adjustedScore
      bestCols = cols
    }
  }

  // 如果无法整除，找接近整除的列数
  if (bestCols === 0) {
    for (let cols = 2; cols <= maxCols; cols++) {
      const remainder = cells.length % cols
      if (remainder <= 2) {
        bestCols = cols
        break
      }
    }
  }

  return bestCols || 0
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
