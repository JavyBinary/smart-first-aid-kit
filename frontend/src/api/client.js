/**
 * Базовый HTTP-клиент MedAI SPA (cookie-first, auto-refresh на 401, честные 4xx ошибки).
 */

export function getApiBase() {
    if (typeof window !== 'undefined') {
        if (window.MEDAI_API_BASE) return window.MEDAI_API_BASE.replace(/\/+$/, '');
        const { protocol, hostname, port } = window.location;
        if (port === '3000' || port === '5173' || port === '8080') {
            return `${protocol}//${hostname}:8000/api/v1`;
        }
    }
    return '/api/v1';
}

let _refreshPromise = null;

async function tryRefreshSession(base) {
    if (_refreshPromise) return _refreshPromise;
    _refreshPromise = (async () => {
        try {
            const resp = await fetch(`${base}/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
            });
            return resp.ok;
        } catch {
            return false;
        } finally {
            _refreshPromise = null;
        }
    })();
    return _refreshPromise;
}

export async function request(endpoint, options = {}, _retried = false) {
    const base = getApiBase();
    const url = endpoint.startsWith('http') ? endpoint : `${base}${endpoint}`;
    const config = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        ...options,
    };

    try {
        const response = await fetch(url, config);

        if (response.status === 401 && !_retried && !endpoint.includes('/auth/')) {
            const refreshed = await tryRefreshSession(base);
            if (refreshed) {
                return request(endpoint, options, true);
            }
        }

        if (response.status === 204) {
            return { _ok: true, _status: 204 };
        }

        const text = await response.text();
        let data = {};
        if (text) {
            try {
                data = JSON.parse(text);
            } catch {
                data = { detail: text };
            }
        }

        if (!response.ok) {
            // Сетевой или серверный 5xx сбой — разрешаем fallback только для 502/503/504
            if (response.status >= 502 && response.status <= 504) {
                return { _fallback: true, _status: response.status, _error: data.detail || 'Сервер недоступен' };
            }
            return {
                _ok: false,
                _status: response.status,
                _error: data.detail || data.message || `HTTP ${response.status}`,
                detail: data.detail,
            };
        }

        return data;
    } catch (error) {
        return {
            _fallback: true,
            _status: 0,
            _error: error?.message || 'Сетевая ошибка',
        };
    }
}
