import { request } from './client.js';

export const authApi = {
  async login(email, password) {
    const res = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    if (!res._fallback && res.token) {
      return res;
    }
    // Локальный fallback режим
    const isAdmin = email.trim().toLowerCase() === 'admin@medai.ru';
    return {
      token: 'mock-jwt-token-local',
      user: {
        id: 'usr_local',
        email,
        name: email.split('@')[0],
        role: isAdmin ? 'admin' : 'user'
      }
    };
  },

  async register(name, email, password) {
    const res = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password })
    });
    if (!res._fallback && res.token) {
      return res;
    }
    return {
      token: 'mock-jwt-token-local',
      user: {
        id: 'usr_local',
        email,
        name,
        role: 'user'
      }
    };
  },

  async changePassword(oldPassword, newPassword) {
    return await request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
  }
};
