interface SseCallbacks {
  onStatus: (step: string) => void
  onDone: (data: unknown) => void
  onError: (err: Error) => void
}

export async function postSSE(path: string, body: unknown, callbacks: SseCallbacks): Promise<void> {
  let res: Response
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    })
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error(String(err)))
    return
  }

  if (res.status === 401) {
    window.location.href = '/login'
    return
  }

  if (!res.ok || !res.body) {
    callbacks.onError(new Error(`HTTP ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const events = buffer.split('\n\n')
      buffer = events.pop() ?? ''

      for (const raw of events) {
        if (!raw.trim()) continue
        const lines = raw.split('\n')
        let eventType = 'message'
        let dataLine = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          else if (line.startsWith('data: ')) dataLine = line.slice(6)
        }
        if (!dataLine) continue
        const parsed = JSON.parse(dataLine)
        if (eventType === 'status') {
          callbacks.onStatus(parsed.step)
        } else if (eventType === 'done') {
          callbacks.onDone(parsed)
        } else if (eventType === 'error') {
          callbacks.onError(new Error(parsed.detail ?? 'SSE error'))
        }
      }
    }
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error(String(err)))
  } finally {
    reader.releaseLock()
  }
}
