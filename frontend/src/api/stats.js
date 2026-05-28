/**
 * Statistics API service.
 *
 * Security:
 *  - Date params validated by useStats hook before reaching here
 *  - Export uses Axios blob response to avoid eval-based data parsing
 *
 * Place: frontend/src/api/stats.js
 */

import { get } from './client';
import client from './client';

export const statsApi = {
  /**
   * GET /api/v1/stats/
   * @param {object} params  { from, to, granularity, domain, compare }
   */
  get: (params) => get('/stats/', params),

  /**
   * GET /api/v1/stats/export/
   * Returns a Blob (CSV file) — caller must create an object URL.
   */
  export: async (params) => {
    const response = await client.get('/stats/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;   // Blob
  },
};