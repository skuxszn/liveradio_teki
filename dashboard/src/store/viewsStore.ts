import { create } from 'zustand'

export interface MappingView {
  id: string
  name: string
  params: { search?: string; page?: number }
}

interface ViewsState {
  views: MappingView[]
  saveView: (name: string, params: { search?: string; page?: number }) => void
  removeView: (id: string) => void
}

export const useViewsStore = create<ViewsState>((set) => ({
  views: [],
  saveView: (name, params) => set((s) => ({ views: [{ id: crypto.randomUUID(), name, params }, ...s.views].slice(0, 20) })),
  removeView: (id) => set((s) => ({ views: s.views.filter(v => v.id !== id) })),
}))



