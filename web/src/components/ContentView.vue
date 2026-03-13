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
  const chapter = (contentId.split('\\')[0] || 'misc').toUpperCase()

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
 * - 无 tab 的连续行 → 检测是否为扁平表格数据（如交替的文本/数值行）
 * - 纯文本行 → 普通段落
 */
const formattedContent = computed(() => {
  if (!content.value) return ''
  return formatText(content.value)
})

/**
 * 检测一个 cell 是否为数值（包含数字、范围如 0.1~0.2、或 - 占位）
 */
function isNumericCell(s) {
  s = s.trim()
  if (!s) return false
  if (s === '-' || s === '—') return true
  // 匹配数字、带范围的数字、带单位后缀的数字
  return /^-?\d*\.?\d+([~～×\-]\d*\.?\d+)?[%①②③④⑤⑥⑦⑧⑨⑩]?$/.test(s)
}

/**
 * 检测一个字符串是否看起来像表头文字（非纯数值）
 */
function isHeaderText(s) {
  s = s.trim()
  if (!s) return false
  if (isNumericCell(s)) return false
  return true
}

/**
 * 尝试从连续的单列行中检测扁平表格（列数被展开为逐行排列的数据）。
 * 返回 { detected: boolean, cols: number } 或 null。
 *
 * 常见模式：
 * 1) 标题行 → N 个表头行 → 然后每 N 行为一组数据
 * 2) 交替的 文本/数值 行 → 2 列表格
 */
function detectFlatTable(lines) {
  if (lines.length < 4) return null

  // 尝试检测列数：从第一个数值行开始，看连续数值行的模式
  // 方法：找到第一个数值出现的位置，然后看间隔
  const isNum = lines.map(l => isNumericCell(l.trim()))

  // 计算每种候选列数下的 "对齐分数"
  let bestCols = 0
  let bestScore = -1

  for (let cols = 2; cols <= Math.min(12, Math.floor(lines.length / 2)); cols++) {
    // 尝试找到数据开始位置（跳过表头行）
    for (let start = 0; start < Math.min(cols * 3, lines.length - cols); start++) {
      let score = 0
      let total = 0
      for (let i = start; i + cols <= lines.length; i += cols) {
        const row = lines.slice(i, i + cols)
        // 一个好的数据行应该有一致的数值/文本模式
        const numCount = row.filter(l => isNumericCell(l.trim())).length
        if (numCount > 0) score += numCount
        total += cols
      }
      if (total > 0 && score / total > bestScore) {
        bestScore = score / total
        bestCols = cols
      }
    }
  }

  // 至少20%的cell应该是数值才算表格
  if (bestScore > 0.15 && bestCols >= 2) {
    return { detected: true, cols: bestCols }
  }

  // 特殊模式：交替的 key-value 行（如 标准代号/标准名称 的列表）
  // 检查是否有规律的缩进模式
  const indented = lines.map(l => l.startsWith('\u3000') || l.startsWith('   '))
  let alternating = 0
  for (let i = 0; i < lines.length - 1; i += 2) {
    if (!indented[i] && indented[i + 1]) alternating++
  }
  if (alternating > lines.length * 0.3) {
    return { detected: true, cols: 2 }
  }

  return null
}

/**
 * 将扁平的单列行重建为表格行数组
 */
function rebuildFlatRows(lines, cols) {
  const rows = []

  // 找到表头区域：开头的非数值行
  let headerEnd = 0
  // 扫描找到第一个数值出现的位置
  for (let i = 0; i < lines.length; i++) {
    if (isNumericCell(lines[i].trim())) {
      // 回退到对齐位置
      headerEnd = i
      break
    }
  }

  // 如果表头行数等于 cols，就是正常的表头
  if (headerEnd > 0 && headerEnd <= cols) {
    rows.push(lines.slice(0, headerEnd))
    // 剩余的按 cols 分行
    for (let i = headerEnd; i < lines.length; i += cols) {
      rows.push(lines.slice(i, i + cols).map(l => l.trim()))
    }
  } else if (headerEnd > cols) {
    // 表头过多，可能包含标题+表头
    // 把前面的作为标题段落处理，后面按 cols 分
    rows.push(lines.slice(0, cols))
    for (let i = cols; i < lines.length; i += cols) {
      rows.push(lines.slice(i, i + cols).map(l => l.trim()))
    }
  } else {
    // 全部按 cols 分行
    for (let i = 0; i < lines.length; i += cols) {
      rows.push(lines.slice(i, i + cols).map(l => l.trim()))
    }
  }

  return rows
}

function formatText(text) {
  const lines = text.split('\n')
  const result = []
  let tableRows = []    // 含 tab 的行（已拆分为 array）
  let plainLines = []   // 不含 tab 的连续行

  function flushTable() {
    if (tableRows.length === 0) return
    result.push(renderTable(tableRows))
    tableRows = []
  }

  function flushPlain() {
    if (plainLines.length === 0) return

    // 检测是否为扁平表格
    if (plainLines.length >= 4) {
      const detection = detectFlatTable(plainLines)
      if (detection && detection.detected) {
        const rows = rebuildFlatRows(plainLines, detection.cols)
        if (rows.length > 1) {
          result.push(renderTable(rows))
          plainLines = []
          return
        }
      }
    }

    // 普通段落
    for (const line of plainLines) {
      const trimmed = line.trim()
      if (trimmed) {
        result.push(`<p class="para">${escapeHtml(trimmed)}</p>`)
      }
    }
    plainLines = []
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      flushTable()
      flushPlain()
      continue
    }

    if (trimmed.includes('\t')) {
      flushPlain()
      tableRows.push(trimmed.split('\t'))
    } else {
      flushTable()
      plainLines.push(trimmed)
    }
  }
  flushTable()
  flushPlain()

  return result.join('')
}

/**
 * 将多行数据渲染为 HTML 表格。
 * 支持：
 * - 自动检测表头行（含非数值内容的行）
 * - 多行表头
 * - 列数不一致时自动添加 colspan
 * - 分类行（以全角空格开头的缩进行）样式区分
 */
function renderTable(rows) {
  if (rows.length === 0) return ''

  // 找最大列数
  let maxCols = 0
  for (const row of rows) {
    if (row.length > maxCols) maxCols = row.length
  }

  // 如果只有1列，渲染为简单列表
  if (maxCols <= 1) {
    let html = '<div class="list-block">'
    for (const row of rows) {
      const cell = (row[0] || '').trim()
      if (!cell) continue
      const isIndented = cell.startsWith('\u3000') || cell.startsWith('   ')
      const cls = isIndented ? 'list-item indent' : 'list-item'
      html += `<div class="${cls}">${escapeHtml(cell)}</div>`
    }
    html += '</div>'
    return html
  }

  // 判断表头行数：从第一行开始，连续的「大部分cell都是非数值」的行作为表头
  let headerRows = 0
  for (let i = 0; i < Math.min(rows.length - 1, 5); i++) {
    const row = rows[i]
    const nonEmpty = row.filter(c => c.trim())
    const headerCells = nonEmpty.filter(c => isHeaderText(c))
    // 如果超过一半的非空cell是文本，认为是表头行
    if (nonEmpty.length > 0 && headerCells.length >= nonEmpty.length * 0.6) {
      headerRows = i + 1
    } else {
      break
    }
  }

  // 至少保留一个表头行（如果第一行有文本）
  if (headerRows === 0) {
    const firstRow = rows[0]
    const hasText = firstRow.some(c => c.trim() && isHeaderText(c))
    if (hasText) headerRows = 1
  }

  let html = '<div class="table-wrap"><table class="data-table">'

  // 渲染表头
  if (headerRows > 0) {
    html += '<thead>'
    for (let i = 0; i < headerRows; i++) {
      html += '<tr>'
      const row = rows[i]
      for (let j = 0; j < row.length; j++) {
        const cell = row[j]
        // 如果这行列数少于最大列数，最后一个cell用colspan填满
        if (row.length < maxCols && j === row.length - 1) {
          const span = maxCols - row.length + 1
          html += `<th colspan="${span}">${escapeHtml(cell)}</th>`
        } else {
          html += `<th>${escapeHtml(cell)}</th>`
        }
      }
      html += '</tr>'
    }
    html += '</thead>'
  }

  // 渲染数据行
  if (rows.length > headerRows) {
    html += '<tbody>'
    for (let i = headerRows; i < rows.length; i++) {
      const row = rows[i]
      // 检测分类行：第一个cell有内容且是文本，其他cell都为空
      const firstCell = (row[0] || '').trim()
      const isCategory = row.length === 1 && firstCell && isHeaderText(firstCell) && !firstCell.startsWith('\u3000') && !firstCell.startsWith('   ')
      const isIndented = firstCell.startsWith('\u3000') || firstCell.startsWith('   ')

      let rowClass = ''
      if (isCategory) rowClass = ' class="category-row"'
      else if (isIndented) rowClass = ' class="indent-row"'

      html += `<tr${rowClass}>`
      for (let j = 0; j < row.length; j++) {
        const cell = row[j] || ''
        // 列数不够时，最后一个cell用colspan填满
        if (row.length < maxCols && j === row.length - 1) {
          const span = maxCols - row.length + 1
          if (isCategory) {
            html += `<td colspan="${maxCols}">${escapeHtml(cell)}</td>`
          } else {
            html += `<td colspan="${span}">${escapeHtml(cell)}</td>`
          }
        } else {
          // 数值cell右对齐
          const trimmed = cell.trim()
          const isNum = isNumericCell(trimmed)
          const tdClass = isNum ? ' class="num-cell"' : ''
          html += `<td${tdClass}>${escapeHtml(cell)}</td>`
        }
      }
      // 如果分类行只有1个cell，已经用colspan覆盖了
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

/* === 标题 === */
.content h1 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 20px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #333;
  font-family: "SimSun", "STSong", "Songti SC", serif;
  letter-spacing: 0.5px;
}

/* === 段落 === */
.content :deep(.para) {
  font-size: 14px;
  line-height: 2;
  color: #222;
  margin: 6px 0;
  text-indent: 2em;
  font-family: "SimSun", "STSong", "Songti SC", "PingFang SC", serif;
}

/* === 表格容器 === */
.content :deep(.table-wrap) {
  overflow-x: auto;
  margin: 16px 0;
  border: 2px solid #333;
}

/* === 数据表格 === */
.content :deep(.data-table) {
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
  min-width: 400px;
  font-family: "SimSun", "STSong", "Songti SC", "PingFang SC", serif;
  line-height: 1.6;
}

/* 表格单元格通用样式 */
.content :deep(.data-table th),
.content :deep(.data-table td) {
  border: 1px solid #555;
  padding: 5px 10px;
  text-align: center;
  vertical-align: middle;
  word-break: break-word;
  white-space: normal;
}

/* 表头 */
.content :deep(.data-table thead th) {
  background: #e8e8e8;
  font-weight: 700;
  color: #111;
  font-size: 13px;
  padding: 6px 10px;
}

/* 数据行 */
.content :deep(.data-table tbody td) {
  color: #222;
  background: #fff;
}

/* 数值单元格右对齐 */
.content :deep(.data-table td.num-cell) {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* 分类行（大类标题行） */
.content :deep(.data-table tr.category-row td) {
  background: #f0f0f0;
  font-weight: 700;
  color: #111;
  text-align: left;
  padding-left: 10px;
}

/* 缩进行（子项目） */
.content :deep(.data-table tr.indent-row td:first-child) {
  text-align: left;
  padding-left: 20px;
}

/* 偶数行斑马纹 */
.content :deep(.data-table tbody tr:nth-child(even):not(.category-row)) {
  background: #fafafa;
}

/* 悬停效果 */
.content :deep(.data-table tbody tr:hover) {
  background: #e8f0fe;
}

/* === 列表块（单列数据） === */
.content :deep(.list-block) {
  margin: 12px 0;
  border: 2px solid #333;
  font-family: "SimSun", "STSong", "Songti SC", "PingFang SC", serif;
  font-size: 13px;
  line-height: 1.8;
}

.content :deep(.list-item) {
  padding: 4px 12px;
  border-bottom: 1px solid #ddd;
  color: #222;
}

.content :deep(.list-item:last-child) {
  border-bottom: none;
}

.content :deep(.list-item.indent) {
  padding-left: 28px;
  color: #444;
}

/* === 数据块（预格式化） === */
.content :deep(.data-block) {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 16px 20px;
  margin: 12px 0;
  overflow-x: auto;
  white-space: pre;
}

/* === 占位页面 === */
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
