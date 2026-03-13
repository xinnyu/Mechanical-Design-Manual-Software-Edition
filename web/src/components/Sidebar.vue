<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>机械设计手册</h2>
    </div>
    <div class="tree-container">
      <div v-if="loading" class="loading">加载目录中...</div>
      <TreeNode
        v-for="root in tree"
        :key="root.id"
        :node="root"
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import TreeNode from './TreeNode.vue'

defineProps({
  activeId: { type: Number, default: null },
})

defineEmits(['select'])

const tree = ref([])
const loading = ref(true)

onMounted(async () => {
  const res = await fetch(import.meta.env.BASE_URL + 'data/tree.json')
  tree.value = await res.json()
  loading.value = false
})
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
.sidebar-header {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #e0e0e0;
}
.sidebar-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}
.tree-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.loading {
  padding: 20px;
  color: #999;
  text-align: center;
}
</style>
