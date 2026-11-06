<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()
</script>

<template>
  <router-view />
  <div class="toast-wrap">
    <transition-group name="fade">
      <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="t.type">
        <span class="dot"></span>{{ t.message }}
      </div>
    </transition-group>
  </div>
</template>
