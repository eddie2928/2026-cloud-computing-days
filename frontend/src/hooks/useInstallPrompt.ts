import { useEffect, useRef, useState } from 'react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export interface InstallPromptState {
  canInstall: boolean
  isIOS: boolean
  isStandalone: boolean
  promptInstall: () => Promise<void>
}

function detectIOS(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}

function detectStandalone(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && (navigator as { standalone?: boolean }).standalone === true)
  )
}

export function useInstallPrompt(): InstallPromptState {
  const [canInstall, setCanInstall] = useState(false)
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null)

  const isIOS = detectIOS()
  const isStandalone = detectStandalone()

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault()
      deferredPrompt.current = e as BeforeInstallPromptEvent
      setCanInstall(true)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  useEffect(() => {
    const handler = () => setCanInstall(false)
    window.addEventListener('appinstalled', handler)
    return () => window.removeEventListener('appinstalled', handler)
  }, [])

  const promptInstall = async () => {
    if (!deferredPrompt.current) return
    await deferredPrompt.current.prompt()
    await deferredPrompt.current.userChoice
    deferredPrompt.current = null
    setCanInstall(false)
  }

  return { canInstall, isIOS, isStandalone, promptInstall }
}
