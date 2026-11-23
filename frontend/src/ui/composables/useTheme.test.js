import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('theme preference', () => {
  let root
  let storage

  beforeEach(() => {
    vi.resetModules()
    root = { dataset: { theme: 'dark' } }
    storage = { setItem: vi.fn() }
    vi.stubGlobal('document', { documentElement: root, createElement: () => ({}) })
    vi.stubGlobal('localStorage', storage)
  })
  afterEach(() => vi.unstubAllGlobals())

  it('switches the rendered theme and saves the preference', async () => {
    const { useTheme } = await import('./useTheme.js')
    const { theme, toggleTheme } = useTheme()
    toggleTheme()
    expect(theme.value).toBe('light')
    expect(root.dataset.theme).toBe('light')
    expect(storage.setItem).toHaveBeenLastCalledWith('shad-theme', 'light')
    toggleTheme()
    expect(root.dataset.theme).toBe('dark')
    expect(storage.setItem).toHaveBeenLastCalledWith('shad-theme', 'dark')
  })

  it('keeps the preference when page layouts are remounted', async () => {
    const { useTheme } = await import('./useTheme.js')
    useTheme().toggleTheme()
    expect(useTheme().theme.value).toBe('light')
  })

  it('respects the light theme already applied before bootstrap', async () => {
    root.dataset.theme = 'light'
    const { useTheme } = await import('./useTheme.js')
    expect(useTheme().theme.value).toBe('light')
    useTheme().toggleTheme()
    expect(root.dataset.theme).toBe('dark')
  })

  it('still switches the interface when storage is unavailable', async () => {
    storage.setItem.mockImplementation(() => { throw new Error('Storage disabled') })
    const { useTheme } = await import('./useTheme.js')
    expect(() => useTheme().toggleTheme()).not.toThrow()
    expect(root.dataset.theme).toBe('light')
  })
})
