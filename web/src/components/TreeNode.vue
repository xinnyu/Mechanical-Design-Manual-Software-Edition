<template>
  <div class="tree-node">
    <div
      class="node-label"
      :class="{ leaf: isLeaf, active: isActive, 'has-content': !!node.contentId }"
      @click="handleClick"
    >
      <span v-if="!isLeaf" class="toggle">{{ expanded ? '▾' : '▸' }}</span>
      <span v-else class="toggle dot">·</span>
      <span class="name">{{ node.name }}</span>
    </div>
    <div v-if="expanded && node.children" class="children">
      <TreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  activeId: { type: Number, default: null },
})

const emit = defineEmits(['select'])

const expanded = ref(false)
const isLeaf = computed(() => !props.node.children?.length)
const isActive = computed(() => props.node.id === props.activeId)

function handleClick() {
  if (isLeaf.value) {
    emit('select', props.node)
  } else {
    expanded.value = !expanded.value
  }
}
</script>

<style scoped>
.tree-node {
  user-select: none;
}
.node-label {
  display: flex;
  align-items: baseline;
  padding: 3px 8px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: #333;
}
.node-label:hover {
  background: #f0f0f0;
}
.node-label.active {
  background: #e3f2fd;
  color: #1565c0;
  font-weight: 500;
}
.toggle {
  flex-shrink: 0;
  width: 14px;
  font-size: 12px;
  color: #999;
}
.toggle.dot {
  color: #ccc;
  font-size: 18px;
  line-height: 0;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.children {
  padding-left: 16px;
}
</style>
