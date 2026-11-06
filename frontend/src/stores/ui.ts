import { defineStore } from 'pinia'

interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

let seq = 0

export const useUiStore = defineStore('ui', {
  state: () => ({ toasts: [] as ToastItem[] }),
  actions: {
    toast(message: string, type: 'success' | 'error' | 'info' = 'success') {
      const id = ++seq
      this.toasts.push({ id, message, type })
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id)
      }, 2600)
    }
  }
})
