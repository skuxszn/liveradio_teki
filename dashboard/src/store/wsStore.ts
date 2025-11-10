import { create } from 'zustand'

interface WsState {
  connected: boolean
  reconnectCount: number
  lastEvent?: { type: string; data: any } | null
  setConnected: (v: boolean) => void
  bumpReconnect: () => void
  setEvent: (type: string, data: any) => void
}

export const useWsStore = create<WsState>((set) => ({
  connected: false,
  reconnectCount: 0,
  lastEvent: null,
  setConnected: (v) => set({ connected: v, reconnectCount: v ? 0 : 0 }),
  bumpReconnect: () => set((s) => ({ reconnectCount: s.reconnectCount + 1 })),
  setEvent: (type, data) => set({ lastEvent: { type, data } }),
}))



