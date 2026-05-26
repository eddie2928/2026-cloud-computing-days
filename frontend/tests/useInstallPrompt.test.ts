import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

const DESKTOP_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120'
const IPHONE_SAFARI_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
const IPHONE_CHROME_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1'

function mockUA(ua: string) {
  Object.defineProperty(navigator, 'userAgent', { value: ua, configurable: true })
}

async function freshHook() {
  vi.resetModules()
  const mod = await import('../src/hooks/useInstallPrompt')
  return mod.useInstallPrompt
}

function makeInstallEvent() {
  const evt = new Event('beforeinstallprompt', { cancelable: true })
  Object.defineProperty(evt, 'prompt', { value: vi.fn().mockResolvedValue(undefined) })
  Object.defineProperty(evt, 'userChoice', { value: Promise.resolve({ outcome: 'accepted' }) })
  return evt
}

describe('useInstallPrompt', () => {
  beforeEach(() => {
    mockUA(DESKTOP_UA)
    Object.defineProperty(navigator, 'maxTouchPoints', { value: 0, configurable: true })
    // ensure matchMedia defaults to non-standalone
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    })
  })

  afterEach(() => {
    vi.resetModules()
  })

  it('초기 상태: canInstall=false', async () => {
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())
    expect(result.current.canInstall).toBe(false)
  })

  it('beforeinstallprompt 후 canInstall=true', async () => {
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())

    await act(async () => {
      window.dispatchEvent(makeInstallEvent())
    })

    expect(result.current.canInstall).toBe(true)
  })

  it('appinstalled 후 canInstall=false', async () => {
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())

    await act(async () => {
      window.dispatchEvent(makeInstallEvent())
    })
    expect(result.current.canInstall).toBe(true)

    await act(async () => {
      window.dispatchEvent(new Event('appinstalled'))
    })
    expect(result.current.canInstall).toBe(false)
  })

  it('iOS Safari UA: isIOS=true, isIOSSafari=true', async () => {
    mockUA(IPHONE_SAFARI_UA)
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())
    expect(result.current.isIOS).toBe(true)
    expect(result.current.isIOSSafari).toBe(true)
  })

  it('iOS Chrome UA: isIOS=true, isIOSSafari=false', async () => {
    mockUA(IPHONE_CHROME_UA)
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())
    expect(result.current.isIOS).toBe(true)
    expect(result.current.isIOSSafari).toBe(false)
  })

  it('데스크탑 UA: isIOS=false, isIOSSafari=false', async () => {
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())
    expect(result.current.isIOS).toBe(false)
    expect(result.current.isIOSSafari).toBe(false)
  })

  it('standalone 모드: isStandalone=true', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: query === '(display-mode: standalone)',
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    })
    const useInstallPrompt = await freshHook()
    const { result } = renderHook(() => useInstallPrompt())
    expect(result.current.isStandalone).toBe(true)
  })
})
