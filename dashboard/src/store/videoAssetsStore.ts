import { create } from 'zustand';

export type UploadItemStatus = 'queued' | 'uploading' | 'success' | 'error' | 'cancelled';

export interface UploadQueueItem {
  id: string; // uuid
  file: File;
  progress: number;
  status: UploadItemStatus;
  error?: string;
  tags?: string[];
}

interface VideoAssetsState {
  selectedIds: Set<number>;
  toggleSelect: (id: number) => void;
  clearSelection: () => void;
  setSelected: (ids: number[]) => void;
  selectAll: (ids: number[]) => void;

  previewAssetId: number | null;
  openPreview: (id: number) => void;
  closePreview: () => void;

  uploadQueue: UploadQueueItem[];
  enqueue: (item: UploadQueueItem) => void;
  updateQueueItem: (id: string, patch: Partial<UploadQueueItem>) => void;
  removeQueueItem: (id: string) => void;
  clearQueue: () => void;
}

export const useVideoAssetsStore = create<VideoAssetsState>((set) => ({
  selectedIds: new Set<number>(),
  toggleSelect: (id) =>
    set((s) => {
      const next = new Set(s.selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { selectedIds: next };
    }),
  clearSelection: () => set({ selectedIds: new Set() }),
  setSelected: (ids) => set({ selectedIds: new Set(ids) }),
  selectAll: (ids) => set({ selectedIds: new Set(ids) }),

  previewAssetId: null,
  openPreview: (id) => set({ previewAssetId: id }),
  closePreview: () => set({ previewAssetId: null }),

  uploadQueue: [],
  enqueue: (item) => set((s) => ({ uploadQueue: [...s.uploadQueue, item] })),
  updateQueueItem: (id, patch) =>
    set((s) => ({
      uploadQueue: s.uploadQueue.map((it) => (it.id === id ? { ...it, ...patch } : it)),
    })),
  removeQueueItem: (id) =>
    set((s) => ({ uploadQueue: s.uploadQueue.filter((it) => it.id !== id) })),
  clearQueue: () => set({ uploadQueue: [] }),
}));


