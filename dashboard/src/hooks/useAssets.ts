import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { assetService, type VideoAsset } from '@/services/asset.service';

export function useAssets(params: { page: number; limit: number; search?: string; sort?: 'filename' | 'created_at' | 'file_size' | 'duration'; direction?: 'asc' | 'desc' }) {
  const { page, limit, search, sort = 'created_at', direction = 'desc' } = params;
  return useQuery<{
    items: VideoAsset[];
    pagination: { page: number; limit: number; total: number; pages: number };
  }>({
    queryKey: ['assets', { page, limit, search, sort, direction }],
    queryFn: () => assetService.list({ page, limit, search, sort, direction }),
    placeholderData: keepPreviousData,
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { file: File; tags?: string[]; onProgress?: (p: number) => void }) =>
      assetService.create(payload.file, payload.tags, payload.onProgress),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['asset-stats'] });
    },
  });
}

export function useCreateAssets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { files: File[]; tags?: string[] }) => assetService.createMany(payload.files, payload.tags),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['asset-stats'] });
    },
  });
}

export function useUpdateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { id: number; data: { filename?: string; tags?: string[] } }) =>
      assetService.update(payload.id, payload.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { id: number; force?: boolean }) =>
      assetService.deleteById(payload.id, payload.force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['asset-stats'] });
    },
  });
}

export function useBatchDelete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { ids: number[]; force?: boolean }) => assetService.batchDelete(payload.ids, payload.force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['asset-stats'] });
    },
  });
}

export function useBatchUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { ids: number[]; filename_prefix?: string; filename_suffix?: string; tags?: string[] }) => assetService.batchUpdate(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useBatchTags() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { ids: number[]; add?: string[]; remove?: string[]; replace?: string[] }) => assetService.batchTags(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}


