/**
 * HTTP Client with Seamless Fallback support for MedAI / Аптечка
 */

export const API_BASE = 'http://localhost:8000/api/v1';

export async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = localStorage.getItem('medai_token') || '';

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    // Сетевой сбой или сервер не запущен — перехватываем для автономного демо-режима
    return { _fallback: true, error: error.message };
  }
}
