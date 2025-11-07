/**
 * Track mapping management service.
 * Handles CRUD operations for track-to-video mappings.
 */

import api from './api';

export interface TrackMapping {
  id: number;
  artist: string;
  title: string;
  video_loop: string;
  azuracast_song_id?: string | null;
  notes?: string | null;
  created_at: string;
  play_count: number;
  last_played_at?: string | null;
}

export interface MappingsResponse {
  mappings: TrackMapping[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface MappingCreateData {
  artist: string;
  title: string;
  video_loop: string;
  azuracast_song_id?: string;
  notes?: string;
}

export interface MappingStats {
  total_mappings: number;
  most_played: Array<{
    artist: string;
    title: string;
    play_count: number;
  }>;
  recently_added: Array<{
    artist: string;
    title: string;
    created_at: string;
  }>;
}

export const mappingService = {
  /**
   * Get all mappings with pagination and filtering.
   */
  async getAll(params?: {
    page?: number;
    limit?: number;
    search?: string;
    filter_by?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }): Promise<MappingsResponse> {
    const response = await api.get<MappingsResponse>('/mappings/', { params });
    return response.data;
  },

  /**
   * Get a single mapping by ID.
   */
  async getById(id: number): Promise<TrackMapping> {
    const response = await api.get<TrackMapping>(`/mappings/${id}`);
    return response.data;
  },

  /**
   * Create a new mapping.
   */
  async create(data: MappingCreateData): Promise<TrackMapping> {
    const response = await api.post<TrackMapping>('/mappings/', data);
    return response.data;
  },

  /**
   * Update an existing mapping.
   */
  async update(id: number, data: MappingCreateData): Promise<TrackMapping> {
    const response = await api.put<TrackMapping>(`/mappings/${id}`, data);
    return response.data;
  },

  /**
   * Delete a mapping.
   */
  async delete(id: number): Promise<void> {
    await api.delete(`/mappings/${id}`);
  },

  /**
   * Bulk import mappings from file.
   */
  async bulkImport(file: File): Promise<{
    success: boolean;
    imported: number[];
    imported_count: number;
    errors: string[];
    error_count: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/mappings/bulk-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Bulk delete mappings.
   */
  async bulkDelete(ids: number[]): Promise<{
    success: boolean;
    deleted_count: number;
  }> {
    const response = await api.post('/mappings/bulk-delete', ids);
    return response.data;
  },

  /**
   * Get mapping statistics.
   */
  async getStats(): Promise<MappingStats> {
    const response = await api.get<MappingStats>('/mappings/stats');
    return response.data;
  },

  /**
   * Export mappings to CSV.
   */
  async export(): Promise<{
    csv_data: string;
    row_count: number;
  }> {
    const response = await api.get('/mappings/export');
    return response.data;
  },
};

export default mappingService;

