import { precacheAndRoute } from 'workbox-precaching'

declare const self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)

self.addEventListener('push', (event: PushEvent) => {
  const data = event.data?.json() as { title?: string; body?: string; url?: string } | undefined
  const title = data?.title ?? 'Days'
  const body = data?.body ?? '오늘 하루를 기록해보세요 ✍️'
  const url = data?.url ?? '/'

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/icons/pwa-192x192.png',
      badge: '/icons/pwa-192x192.png',
      data: { url },
    })
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const url: string = (event.notification.data as { url?: string })?.url ?? '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      const existing = clients.find((c) => c.url === url && 'focus' in c)
      if (existing) return existing.focus()
      return self.clients.openWindow(url)
    })
  )
})
