<template>
  <div class="app">
    <div class="left-panel">
      <SearchBar @select="selectNode" />
      <Sidebar :active-id="activeNode?.id" @select="selectNode" />
    </div>
    <ContentView :node="activeNode" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ContentView from './components/ContentView.vue'
import SearchBar from './components/SearchBar.vue'

const activeNode = ref(null)

function selectNode(node) {
  activeNode.value = node
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
}
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.left-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  min-width: 360px;
  height: 100vh;
  border-right: 1px solid #e0e0e0;
  background: #fafafa;
}
</style>
