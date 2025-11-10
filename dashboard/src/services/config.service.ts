/**
 * Configuration management service.
 * Handles fetching, updating, and testing configuration settings.
 */

import api from './api';

export interface Setting {
  id: number;
  category: string;
  key: string;
  value: string | null;
  value_type: string;
  default_value: string | null;
  description: string | null;
  is_secret: boolean;
  is_required: boolean;
  requires_restart: boolean;
  validation_regex: string | null;
  validation_min: number | null;
  validation_max: number | null;
  allowed_values: any;
}

export interface SettingsUpdatePayload {
  updates: Record<string, string>;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  azuracast_version?: string;
  online?: boolean;
  tested_at: string;
}

export interface TokenGenerationResult {
  success: boolean;
  token: string;
  token_type: string;
  generated_at: string;
  message: string;
}

export const configService = {
  /**
   * Get all settings, optionally filtered by category.
   */
  async getAll(category?: string): Promise<Setting[]> {
    const params = category ? { category } : {};
    const response = await api.get<Setting[]>('/config', { params });
    return response.data;
  },

  /**
   * Get settings by category.
   */
  async getByCategory(category: string): Promise<Setting[]> {
    const response = await api.get<Setting[]>(`/config/${category}`);
    return response.data;
  },

  /**
   * Update a single setting.
   */
  async updateSetting(
    category: string,
    key: string,
    value: string
  ): Promise<Setting> {
    const response = await api.put<Setting>(`/config/${category}/${key}`, {
      value,
    });
    return response.data;
  },

  /**
   * Bulk update multiple settings.
   */
  async bulkUpdate(
    updates: Record<string, string>
  ): Promise<{ updated: string[]; errors: string[]; success_count: number; error_count: number }> {
    const response = await api.post('/config/bulk-update', { updates });
    return response.data;
  },

  /**
   * Export all configuration settings.
   */
  async export(): Promise<{
    settings: Record<string, Record<string, string>>;
    exported_at: string;
    version: string;
  }> {
    const response = await api.get('/config/export');
    return response.data;
  },

  /**
   * Test connection to AzuraCast instance.
   */
  async testAzuraCastConnection(): Promise<ConnectionTestResult> {
    const response = await api.post<ConnectionTestResult>('/config/test-azuracast');
    return response.data;
  },

  /**
   * Generate a new security token.
   */
  async generateToken(tokenType: 'webhook_secret' | 'api_token' | 'jwt_secret'): Promise<TokenGenerationResult> {
    const response = await api.post<TokenGenerationResult>(
      `/config/generate-token?token_type=${tokenType}`
    );
    return response.data;
  },
};

export default configService;



