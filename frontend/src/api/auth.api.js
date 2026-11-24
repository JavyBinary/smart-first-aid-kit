import { request } from './client.js';

export const authApi = {
  async getMe() {
    const res = await request('/auth/me');
    if (!res._fallback && res.id) {
      return res;
    }
    return null;
  },

  async getAdminUsers() {
    const res = await request('/auth/admin/users');
    if (!res._fallback && Array.isArray(res)) {
      return res;
    }
    return null;
  },

  async login(email, password) {
    const res = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    if (!res._fallback && (res.id || res.user || res.token)) {
      const user = res.user || res;
      return { token: 'session-cookie', user };
    }
    // Локальный fallback режим с поддержкой superadmin и admin
    const cleanEmail = email.trim().toLowerCase();
    let role = 'user';
    let name = cleanEmail.split('@')[0];

    if (cleanEmail === 'admin@medai.ru' || cleanEmail === 'superadmin@medai.ru' || cleanEmail === 'luka@medai.ru') {
      role = 'superadmin';
      name = cleanEmail === 'luka@medai.ru' ? 'Лука' : 'Главный администратор';
    } else if (cleanEmail.endsWith('@medai.ru') || cleanEmail.includes('admin')) {
      role = 'admin';
    }

    return {
      token: 'mock-jwt-token-local',
      user: {
        id: 'usr_local',
        email,
        name,
        role
      }
    };
  },

  async register(name, email, password) {
    const res = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password })
    });
    if (!res._fallback && (res.id || res.user || res.token)) {
      const user = res.user || res;
      return { token: 'session-cookie', user };
    }
    const cleanEmail = email.trim().toLowerCase();
    let role = 'user';
    if (cleanEmail === 'admin@medai.ru' || cleanEmail === 'superadmin@medai.ru' || cleanEmail === 'luka@medai.ru') {
      role = 'superadmin';
    } else if (cleanEmail.endsWith('@medai.ru') || cleanEmail.includes('admin')) {
      role = 'admin';
    }
    return {
      token: 'mock-jwt-token-local',
      user: {
        id: 'usr_local',
        email,
        name: name || cleanEmail.split('@')[0],
        role
      }
    };
  },

  async changePassword(oldPassword, newPassword) {
    return await request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
  },

  logout() {
    localStorage.removeItem('medai_token');
    localStorage.removeItem('medai_user');
    localStorage.removeItem('medai_name');
    localStorage.removeItem('medai_role');
    localStorage.removeItem('medai_avatar');
    window.location.href = 'login.html';
  }
};
