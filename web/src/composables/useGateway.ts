import { onMounted, onUnmounted } from 'vue'
import { gatewayService } from '@/services/gateway'

export function useGateway() {
  onMounted(() => {
    gatewayService.connect()
  })

  onUnmounted(() => {
    // Keep connection alive across views; only close on app teardown if needed.
  })

  return {
    service: gatewayService,
  }
}
