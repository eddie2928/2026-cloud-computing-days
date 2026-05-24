import client from '../api/client'

export type PushState = 'unsupported' | 'denied' | 'granted' | 'subscribed' | 'default'

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const output = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    output[i] = rawData.charCodeAt(i)
  }
  return output
}

export async function getPushState(): Promise<PushState> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return 'unsupported'
  }
  const perm = Notification.permission
  if (perm === 'denied') return 'denied'

  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (sub) return 'subscribed'
  return perm === 'granted' ? 'granted' : 'default'
}

export async function subscribePush(): Promise<void> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Push not supported in this browser')
  }

  const perm = await Notification.requestPermission()
  if (perm !== 'granted') throw new Error('Permission denied')

  const { data } = await client.get<{ public_key: string }>('/push/public-key')
  const applicationServerKey = urlBase64ToUint8Array(data.public_key)

  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  })

  const json = sub.toJSON()
  await client.post('/push/subscribe', {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
  })
}

export async function unsubscribePush(): Promise<void> {
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (!sub) return

  const json = sub.toJSON()
  await sub.unsubscribe()
  await client.delete('/push/unsubscribe', {
    data: { endpoint: json.endpoint, keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth } },
  })
}
