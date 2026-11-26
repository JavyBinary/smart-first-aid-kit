import { request } from './client.js';

export const adminApi = {
    async getStats(period = 30) {
        return request(`/admin/stats?period=${encodeURIComponent(period)}`);
    },

    async getReports(statusFilter = 'new') {
        return request(`/admin/reports?status_filter=${encodeURIComponent(statusFilter)}`);
    },

    async updateReportStatus(reportId, status) {
        return request(`/admin/reports/${encodeURIComponent(reportId)}`, {
            method: 'PATCH',
            body: JSON.stringify({ status }),
        });
    },

    async listMedicines() {
        return request('/admin/medicines');
    },

    async upsertMedicine(doc) {
        return request('/admin/medicines', {
            method: 'POST',
            body: JSON.stringify(doc),
        });
    },

    async deleteMedicine(docId) {
        return request(`/admin/medicines/${encodeURIComponent(docId)}`, {
            method: 'DELETE',
        });
    },

    async getBenchmark(dataset = 'extended') {
        return request(`/admin/benchmark?dataset=${encodeURIComponent(dataset)}`);
    },

    async getUsers() {
        return request('/auth/admin/users');
    },

    async updateUserRole(userId, role) {
        return request(`/auth/admin/users/${encodeURIComponent(userId)}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role }),
        });
    },
};
