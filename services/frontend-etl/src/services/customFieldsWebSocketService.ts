/**
 * Custom Fields WebSocket Service for real-time extraction status monitoring
 *
 * Handles:
 * - Real-time status updates for custom fields extraction (Extraction → Transform → Embedding)
 * - Per-tenant tracking (not per integration)
 * - Connection management with reconnection logic
 * - Completion events to trigger UI refresh
 */

export interface CustomFieldsStatus {
  extraction: 'idle' | 'running' | 'finished' | 'failed'
  transform: 'idle' | 'running' | 'finished' | 'failed'
  embedding: 'idle' | 'running' | 'finished' | 'failed'
  isActive: boolean
}

export interface CustomFieldsEventHandlers {
  onStatusUpdate?: (status: CustomFieldsStatus) => void
  onCompletion?: () => void
}

interface WebSocketMessage {
  type: 'status_update' | 'completion'
  worker_type?: 'extraction' | 'transform' | 'embedding'
  status?: 'idle' | 'running' | 'finished' | 'failed'
  error_message?: string
}

class CustomFieldsWebSocketService {
  private connection: WebSocket | null = null
  private currentTenantId: number | null = null
  private status: CustomFieldsStatus = {
    extraction: 'idle',
    transform: 'idle',
    embedding: 'idle',
    isActive: false
  }
  private eventHandlers: CustomFieldsEventHandlers = {}
  private token: string | null = null
  private isInitialized = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000

  /**
   * Initialize the service with authentication token
   */
  async initializeService(token: string): Promise<void> {
    this.token = token
    this.isInitialized = true
  }

  /**
   * Check if the service is ready to accept connections
   */
  isReady(): boolean {
    return this.isInitialized && this.token !== null
  }

  /**
   * Connect to custom fields WebSocket channel for a tenant
   */
  connect(tenantId: number, handlers: CustomFieldsEventHandlers): () => void {
    if (!this.isInitialized || !this.token) {
      console.warn('[CF-WS] Service not initialized')
      return () => {}
    }

    // Disconnect existing connection if any
    this.disconnect()

    this.currentTenantId = tenantId
    this.eventHandlers = handlers

    // Reset status
    this.status = {
      extraction: 'idle',
      transform: 'idle',
      embedding: 'idle',
      isActive: false
    }

    // Connect to WebSocket
    this.connectToChannel(tenantId)

    // Return cleanup function
    return () => this.disconnect()
  }

  /**
   * Connect to the WebSocket channel
   */
  private connectToChannel(tenantId: number): void {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const backendHost = import.meta.env.VITE_API_BASE_URL?.replace(/^https?:\/\//, '') || 'localhost:3001'
      const wsUrl = `${protocol}//${backendHost}/ws/custom-fields/${tenantId}?token=${encodeURIComponent(this.token!)}`

      const ws = new WebSocket(wsUrl)
      this.connection = ws

      ws.onopen = () => {
        console.log('[CF-WS] Connected to custom fields channel')
        this.reconnectAttempts = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message, tenantId)
        } catch (error) {
          console.error('[CF-WS] Error parsing message:', error)
        }
      }

      ws.onclose = (event) => {
        console.log('[CF-WS] Connection closed')
        this.connection = null

        // Attempt reconnection if not a clean close
        if (event.code !== 1000 && this.isInitialized && this.currentTenantId === tenantId) {
          this.attemptReconnection(tenantId)
        }
      }

      ws.onerror = (error) => {
        console.error('[CF-WS] Connection error:', error)
      }

    } catch (error) {
      console.error('[CF-WS] Failed to connect:', error)
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: WebSocketMessage, tenantId: number): void {
    console.log('[CF-WS] Received message:', message)

    if (message.type === 'status_update' && message.worker_type && message.status) {
      // Update worker status
      this.status[message.worker_type] = message.status

      // Update isActive flag
      this.status.isActive =
        this.status.extraction === 'running' ||
        this.status.transform === 'running' ||
        this.status.embedding === 'running'

      console.log('[CF-WS] Updated status:', this.status)

      // Notify handlers
      this.eventHandlers.onStatusUpdate?.(this.status)

    } else if (message.type === 'completion') {
      console.log('[CF-WS] Received completion event')

      // Reset status to idle
      this.status = {
        extraction: 'idle',
        transform: 'idle',
        embedding: 'idle',
        isActive: false
      }

      // Notify completion handler
      this.eventHandlers.onCompletion?.()
    }
  }

  /**
   * Attempt to reconnect to the WebSocket channel
   */
  private attemptReconnection(tenantId: number): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++

      setTimeout(() => {
        if (this.isInitialized && this.currentTenantId === tenantId) {
          console.log(`[CF-WS] Reconnecting... (attempt ${this.reconnectAttempts})`)
          this.connectToChannel(tenantId)
        }
      }, this.reconnectDelay * this.reconnectAttempts)
    } else {
      console.error('[CF-WS] Max reconnection attempts reached')
    }
  }

  /**
   * Get current status
   */
  getStatus(): CustomFieldsStatus {
    return { ...this.status }
  }

  /**
   * Check if extraction is currently active
   */
  isActive(): boolean {
    return this.status.isActive
  }

  /**
   * Disconnect from the WebSocket channel
   */
  disconnect(): void {
    if (this.connection) {
      try {
        if (this.connection.readyState === WebSocket.OPEN) {
          this.connection.close(1000, 'Manual disconnect')
        }
      } catch (error) {
        // Ignore errors during cleanup
      }
      this.connection = null
    }

    this.currentTenantId = null
    this.eventHandlers = {}
    this.reconnectAttempts = 0
  }

  /**
   * Shutdown the service completely (used on logout)
   */
  shutdown(): void {
    this.disconnect()
    this.isInitialized = false
    this.token = null
  }

  /**
   * Update authentication token
   */
  async updateToken(newToken: string): Promise<void> {
    this.token = newToken
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connection?.readyState === WebSocket.OPEN
  }
}

// Export singleton instance
export const customFieldsWebSocketService = new CustomFieldsWebSocketService()

