import { request } from './client.js';

export const authApi = {
    async getMe() {
        const res = await request('/auth/me');
        if (res._fallback || res._status >= 400) return null;
        return res;
    },

    async login(email, password) {
        return request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },

    async register(name, email, password) {
        return request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password }),
        });
    },

    async changePassword(oldPassword, newPassword) {
        return request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
        });
    },

    async getAdminUsers() {
        return request('/auth/admin/users');
    },

    async updateUserRole(userId, role) {
        return request(`/auth/admin/users/${encodeURIComponent(userId)}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role }),
        });
    },

    async logout() {
        return request('/auth/logout', { method: 'POST' });
    },
};
