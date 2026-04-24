import type { ProgressUpdate } from '~/types'

export const useWebSocket = (taskId: string, apiBase: string) => {
  const progress = ref<ProgressUpdate | null>(null)
  const connected = ref(false)
  const error = ref<string | null>(null)

  let ws: WebSocket | null = null

  const connect = () => {
    const wsUrl = apiBase.replace('http', 'ws') + `/api/ws/progress/${taskId}`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      progress.value = data
    }

    ws.onerror = () => {
      error.value = 'WebSocket connection error'
      connected.value = false
    }

    ws.onclose = () => {
      connected.value = false
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return {
    progress,
    connected,
    error,
    connect,
    disconnect
  }
}
