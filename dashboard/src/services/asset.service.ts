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
  uploaded_at: string;
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
   * Get all assets.
   */
  async getAll(): Promise<VideoAsset[]> {
    const response = await api.get<VideoAsset[]>('/assets');
    return response.data;
  },

  /**
   * Upload a video file.
   */
  async upload(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<VideoAsset> {
    const formData = new FormData();
    formData.append('file', file);

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
   * Delete an asset.
   */
  async delete(filename: string): Promise<void> {
    await api.delete(`/assets/${filename}`);
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
   * Get asset statistics.
   */
  async getStats(): Promise<AssetStats> {
    const response = await api.get<AssetStats>('/assets/stats');
    return response.data;
  },
};

export default assetService;


