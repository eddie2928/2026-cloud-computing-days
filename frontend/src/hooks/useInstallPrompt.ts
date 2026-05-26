import { useEffect, useState } from 'react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export interface InstallPromptState {
  canInstall: boolean
  isIOS: boolean
  isIOSSafari: boolean
  isStandalone: boolean
  promptInstall: () => Promise<void>
}

// ---- module scope: capture events before any component mounts ----
let deferredPrompt: BeforeInstallPromptEvent | null = null
const subscribers = new Set<(canInstall: boolean) => void>()

function notifyAll(canInstall: boolean) {
  subscribers.forEach(fn => fn(canInstall))
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferredPrompt = e as BeforeInstallPromptEvent
  notifyAll(true)
})

window.addEventListener('appinstalled', () => {
  deferredPrompt = null
  notifyAll(false)
})
// -----------------------------------------------------------------

function detectIOS(): boolean {
  const ua = navigator.userAgent
  return /iphone|ipad|ipod/i.test(ua) ||
    (/Macintosh/i.test(ua) && navigator.maxTouchPoints > 1)
}

function detectIOSSafari(): boolean {
  if (!detectIOS()) return false
  return !/CriOS|FxiOS|EdgiOS|OPiOS/i.test(navigator.userAgent)
}

function detectStandalone(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && (navigator as { standalone?: boolean }).standalone === true)
  )
}

export function useInstallPrompt(): InstallPromptState {
  const [canInstall, setCanInstall] = useState(() => deferredPrompt !== null)

  const isIOS = detectIOS()
  const isIOSSafari = detectIOSSafari()
  const isStandalone = detectStandalone()

  useEffect(() => {
    subscribers.add(setCanInstall)
    return () => { subscribers.delete(setCanInstall) }
  }, [])

  const promptInstall = async () => {
    if (!deferredPrompt) return
    await deferredPrompt.prompt()
    await deferredPrompt.userChoice
    deferredPrompt = null
    notifyAll(false)
  }

  return { canInstall, isIOS, isIOSSafari, isStandalone, promptInstall }
}
