/**
 * HTTP Client with Seamless Fallback support for MedAI / Аптечка
 */

export function getApiBase() {
  if (typeof window !== 'undefined' && window.location.origin) {
    if (window.location.port === '8090' || window.location.port === '80' || window.location.port === '') {
      return '/api/v1';
    }
  }
  return 'http://localhost:8000/api/v1';
}

export const API_BASE = getApiBase();

export async function request(endpoint, options = {}) {
  const url = `${getApiBase()}${endpoint}`;
  const token = localStorage.getItem('medai_token') || '';

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };

  try {
    const res = await fetch(url, { credentials: 'include', ...options, headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    // Сетевой сбой или сервер не запущен — перехватываем для автономного демо-режима
    return { _fallback: true, error: error.message };
  }
}
