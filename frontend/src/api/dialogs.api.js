import { getApiBase, request } from './client.js';

export const dialogsApi = {
    async listDialogs() {
        const res = await request('/dialogs');
        if (res._fallback || res._status >= 400) return res;
        return Array.isArray(res.dialogs) ? res.dialogs : [];
    },

    async createDialog(title = null) {
        return request('/dialogs', {
            method: 'POST',
            body: JSON.stringify(title ? { title } : {}),
        });
    },

    async getMessages(dialogId) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages`);
    },

    async deleteDialog(dialogId) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}`, {
            method: 'DELETE',
        });
    },

    async sendMessage(dialogId, {
        content,
        include_kit_context = true,
        selected_pills = [],
        response_depth = 'detailed',
    }) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages`, {
            method: 'POST',
            body: JSON.stringify({
                content,
                include_kit_context,
                selected_pills,
                response_depth,
            }),
        });
    },

    /**
     * Подписывается на SSE-стрим GET /api/v1/dialogs/{dialogId}/events.
     * Возвращает функцию отписки close().
     */
    subscribeEvents(dialogId, handlers = {}) {
        const base = getApiBase();
        const url = `${base}/dialogs/${encodeURIComponent(dialogId)}/events`;
        if (typeof EventSource === 'undefined') {
            return () => {};
        }
        const es = new EventSource(url, { withCredentials: true });
        const parseEvent = (evt) => {
            try {
                return evt.data ? JSON.parse(evt.data) : {};
            } catch {
                return { raw: evt.data };
            }
        };

        es.addEventListener('ready', (evt) => handlers.onReady?.(parseEvent(evt)));
        es.addEventListener('message_start', (evt) => handlers.onStart?.(parseEvent(evt)));
        es.addEventListener('message_delta', (evt) => handlers.onDelta?.(parseEvent(evt)));
        es.addEventListener('message_end', (evt) => handlers.onEnd?.(parseEvent(evt)));
        es.addEventListener('message_error', (evt) => handlers.onError?.(parseEvent(evt)));
        es.onerror = (err) => {
            handlers.onStreamError?.(err);
        };

        return () => es.close();
    },

    async setFeedback(dialogId, messageId, score) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages/${encodeURIComponent(messageId)}/feedback`, {
            method: 'PUT',
            body: JSON.stringify({ score }),
        });
    },

    async deleteFeedback(dialogId, messageId) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages/${encodeURIComponent(messageId)}/feedback`, {
            method: 'DELETE',
        });
    },

    async reportMessage(dialogId, messageId, reason, comment = null) {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages/${encodeURIComponent(messageId)}/report`, {
            method: 'POST',
            body: JSON.stringify({ reason, comment }),
        });
    },

    async getReportNews() {
        const res = await request('/reports/news');
        if (res._fallback || res._status >= 400) return [];
        return Array.isArray(res.news) ? res.news : [];
    },

    async markReportNewsSeen(reportIds) {
        if (!Array.isArray(reportIds) || reportIds.length === 0) return { _ok: true };
        return request('/reports/news/seen', {
            method: 'POST',
            body: JSON.stringify({ report_ids: reportIds }),
        });
    },

    async requestAudio(dialogId, messageId, voice = 'baya') {
        return request(`/dialogs/${encodeURIComponent(dialogId)}/messages/${encodeURIComponent(messageId)}/audio`, {
            method: 'POST',
            body: JSON.stringify({ voice }),
        });
    },

    async synthesizeSpeech(text, voice = 'baya') {
        const base = getApiBase();
        try {
            const resp = await fetch(`${base}/speech/synthesize`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice }),
            });
            if (!resp.ok) return null;
            const blob = await resp.blob();
            return URL.createObjectURL(blob);
        } catch {
            return null;
        }
    },
};
