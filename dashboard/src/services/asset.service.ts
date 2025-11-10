/**
 * Video asset management service.
 */

import api from './api';

export interface VideoAsset {
  id: number;
  filename: string;
  file_path: string;
  file_size: number | null;
  duration: number | null;
  resolution: string | null;
  frame_rate: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  bitrate: number | null;
  pixel_format: string | null;
  is_valid: boolean;
  validation_errors: any;
  thumbnail_path: string | null;
  tags?: string[] | null;
  created_at?: string;
  updated_at?: string;
  usage_count: number;
}

export interface AssetStats {
  total_assets: number;
  valid_assets: number;
  invalid_assets: number;
  total_storage_bytes: number;
  total_storage_mb: number;
}

export const assetService = {
  /**
   * List assets with pagination and optional search.
   */
  async list(params: { page?: number; limit?: number; search?: string; sort?: 'filename' | 'created_at' | 'file_size' | 'duration'; direction?: 'asc' | 'desc' } = {}): Promise<{
    items: VideoAsset[];
    pagination: { page: number; limit: number; total: number; pages: number };
  }> {
    const { page = 1, limit = 25, search, sort = 'created_at', direction = 'desc' } = params;
    const response = await api.get('/assets', { params: { page, limit, search, sort, direction } });
    return response.data;
  },

  /**
   * Get all assets.
   */
  async getAll(): Promise<VideoAsset[]> {
    const response = await api.get<VideoAsset[]>('/assets');
    return response.data;
  },

  /**
   * Upload a video file.
   */
  async upload(file: File, arg2?: string[] | ((progress: number) => void), arg3?: (progress: number) => void): Promise<VideoAsset> {
    // Backwards-compatible signature:
    // - upload(file, onProgress?)
    // - upload(file, tags?, onProgress?)
    let tags: string[] | undefined;
    let onProgress: ((progress: number) => void) | undefined;
    if (typeof arg2 === 'function') {
      onProgress = arg2;
    } else {
      tags = arg2;
      onProgress = arg3;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (tags && tags.length) formData.append('tags', JSON.stringify(tags));

    const response = await api.post<VideoAsset>('/assets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  /**
   * Create (upload) using canonical endpoint.
   */
  async create(file: File, tags?: string[], onProgress?: (progress: number) => void): Promise<VideoAsset> {
    const formData = new FormData();
    formData.append('file', file);
    if (tags && tags.length) {
      formData.append('tags', JSON.stringify(tags));
    }
    const response = await api.post<VideoAsset>('/assets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
    return response.data;
  },

  /**
   * Create multiple assets. Sends a single multipart when supported; otherwise falls back to sequential single uploads.
   */
  async createMany(files: File[], tags?: string[]): Promise<{ items: VideoAsset[] }> {
    const formData = new FormData();
    for (const f of files) {
      formData.append('files', f);
    }
    if (tags && tags.length) {
      formData.append('tags', JSON.stringify(tags));
    }
    const response = await api.post<{ items: VideoAsset[] }>('/assets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * Get asset by id.
   */
  async getById(id: number): Promise<VideoAsset> {
    const response = await api.get<VideoAsset>(`/assets/${id}`);
    return response.data;
    },

  /**
   * Update asset by id.
   */
  async update(id: number, data: { filename?: string; tags?: string[] }): Promise<VideoAsset> {
    const response = await api.put<VideoAsset>(`/assets/${id}`, data);
    return response.data;
  },

  /**
   * Delete an asset.
   */
  async delete(filename: string): Promise<void> {
    await api.delete(`/assets/${filename}`);
  },

  /**
   * Delete by id.
   */
  async deleteById(id: number, force = false): Promise<void> {
    await api.delete(`/assets/id/${id}`, { params: { force } });
  },

  /**
   * Batch delete by ids.
   */
  async batchDelete(ids: number[], force = false): Promise<{ results: Array<{ id: number; success: boolean; error?: string }> }> {
    const response = await api.post('/assets/batch/delete', { ids, force });
    return response.data;
  },

  /**
   * Batch update filename prefix/suffix and optionally replace tags.
   */
  async batchUpdate(payload: { ids: number[]; filename_prefix?: string; filename_suffix?: string; tags?: string[] }): Promise<{ results: any[] }> {
    const response = await api.post('/assets/batch/update', payload);
    return response.data;
  },

  /**
   * Batch tag operations: add/remove or replace.
   */
  async batchTags(payload: { ids: number[]; add?: string[]; remove?: string[]; replace?: string[] }): Promise<{ results: any[] }> {
    const response = await api.post('/assets/batch/tags', payload);
    return response.data;
  },

  /**
   * Validate an asset.
   */
  async validate(filename: string): Promise<{
    filename: string;
    is_valid: boolean;
    metadata: any;
    validation_errors: any;
  }> {
    const response = await api.post(`/assets/${filename}/validate`);
    return response.data;
  },

  /**
   * Get thumbnail URL.
   */
  getThumbnailUrl(filename: string): string {
    return `${api.defaults.baseURL}/assets/${filename}/thumbnail`;
  },

  /**
   * Get raw video URL for preview streaming by id or filename.
   */
  getVideoUrlById(id: number): string {
    const token = localStorage.getItem('access_token');
    const qs = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${api.defaults.baseURL}/assets/file/${id}${qs}`;
  },
  getVideoUrlByFilename(filename: string): string {
    const token = localStorage.getItem('access_token');
    const qs = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${api.defaults.baseURL}/assets/file/by-filename/${encodeURIComponent(filename)}${qs}`;
  },

  /**
   * Get asset statistics.
   */
  async getStats(): Promise<AssetStats> {
    const response = await api.get<AssetStats>('/assets/stats');
    return response.data;
  },

  /**
   * Increment usage count for an asset.
   */
  async incrementUsage(filename: string): Promise<{ success: boolean; usage_count: number; last_used_at: string }>{
    const response = await api.post(`/assets/${filename}/increment_usage`);
    return response.data;
  },

  /**
   * Get where an asset is used in mappings.
   */
  async getUsage(filename: string): Promise<{ filename: string; usage: Array<{ id: number; artist: string; title: string; play_count: number; last_played_at?: string }>; count: number }>{
    const response = await api.get(`/assets/${filename}/usage`);
    return response.data;
  },

  /**
   * Search assets for typeahead selection.
   */
  async search(q: string, page = 1, limit = 20): Promise<{
    results: Array<{ id: number; filename: string; is_valid: boolean; resolution?: string | null; duration?: number | null; file_size?: number | null }>;
    pagination: { page: number; limit: number; total: number; pages: number };
  }> {
    const response = await api.get('/assets/search', { params: { q, page, limit } });
    return response.data;
  },
};

export default assetService;


