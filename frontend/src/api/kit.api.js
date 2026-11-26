import { request } from './client.js';

/**
 * Приводит объект препарата из UI к строгой Pydantic-схеме CreateKitItemRequest (extra="forbid").
 */
export function serializeCreateKitItem(item) {
    const rawStatus = item.status || (item.isPrescription || item.is_prescription ? 'rx' : 'otc');
    const tags = Array.isArray(item.tags)
        ? item.tags.map((t) => String(t).trim()).filter(Boolean)
        : [];
    const payload = {
        name: String(item.name || '').trim(),
        dosage: String(item.dosage || '').trim(),
        form: String(item.form || 'таблетки').trim() || 'таблетки',
        category: String(item.category || 'Пользовательское').trim() || 'Пользовательское',
        tags,
        quantity: Math.max(1, Number.parseInt(item.quantity, 10) || 1),
        expiry: String(item.expiry || '').trim() || '2027-12-31',
        status: rawStatus === 'rx' ? 'rx' : 'otc',
    };
    if (item.id && !String(item.id).startsWith('local-')) {
        payload.id = String(item.id);
    }
    return payload;
}

export function serializeUpdateKitItem(updates) {
    const payload = {};
    if (updates.dosage !== undefined) payload.dosage = String(updates.dosage).trim();
    if (updates.quantity !== undefined) payload.quantity = Math.max(1, Number.parseInt(updates.quantity, 10) || 1);
    if (updates.expiry !== undefined) payload.expiry = String(updates.expiry).trim();
    if (updates.status !== undefined) {
        payload.status = updates.status === 'rx' ? 'rx' : 'otc';
    } else if (updates.isPrescription !== undefined || updates.is_prescription !== undefined) {
        payload.status = updates.isPrescription || updates.is_prescription ? 'rx' : 'otc';
    }
    return payload;
}

export const kitApi = {
    async getItems() {
        const res = await request('/kit');
        if (res._fallback || res._status >= 400) return res;
        return Array.isArray(res.items) ? res.items : [];
    },

    async addItem(item) {
        const payload = serializeCreateKitItem(item);
        return request('/kit/items', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    },

    async updateItem(id, updates) {
        const payload = serializeUpdateKitItem(updates);
        return request(`/kit/items/${encodeURIComponent(id)}`, {
            method: 'PUT',
            body: JSON.stringify(payload),
        });
    },

    async deleteItem(id) {
        return request(`/kit/items/${encodeURIComponent(id)}`, {
            method: 'DELETE',
        });
    },
};
