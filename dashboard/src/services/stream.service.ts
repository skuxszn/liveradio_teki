import api from './api';
import type { StreamStatus } from '@/types';

export const streamService = {
  async getStatus(): Promise<StreamStatus> {
    const response = await api.get<StreamStatus>('/stream/status');
    return response.data;
  },

  async start(): Promise<any> {
    const response = await api.post('/stream/start');
    return response.data;
  },

  async stop(): Promise<any> {
    const response = await api.post('/stream/stop');
    return response.data;
  },

  async restart(): Promise<any> {
    const response = await api.post('/stream/restart');
    return response.data;
  },

  async manualSwitch(artist: string, title: string): Promise<any> {
    const response = await api.post('/stream/switch', { artist, title });
    return response.data;
  },
};


