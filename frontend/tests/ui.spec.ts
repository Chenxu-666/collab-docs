import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '@/stores/ui'

describe('ui store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('toast 添加消息到列表', () => {
    const store = useUiStore()
    store.toast('保存成功', 'success')
    expect(store.toasts.length).toBe(1)
    expect(store.toasts[0].message).toBe('保存成功')
    expect(store.toasts[0].type).toBe('success')
  })

  it('toast 默认类型为 success', () => {
    const store = useUiStore()
    store.toast('提示')
    expect(store.toasts[0].type).toBe('success')
  })

  it('toast 2.6 秒后自动移除', () => {
    const store = useUiStore()
    store.toast('临时提示')
    expect(store.toasts.length).toBe(1)
    vi.advanceTimersByTime(2600)
    expect(store.toasts.length).toBe(0)
  })
})
