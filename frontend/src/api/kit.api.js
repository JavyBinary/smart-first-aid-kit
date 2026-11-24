import { request } from './client.js';

const KIT_STORAGE_KEY = 'medai_kit';

export const kitApi = {
  async getItems() {
    const res = await request('/kit');
    if (!res._fallback && Array.isArray(res.items)) {
      return res.items;
    }
    // Fallback на localStorage
    const saved = localStorage.getItem(KIT_STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // pass
      }
    }
    return [];
  },

  async addItem(item) {
    const newItem = {
      id: item.id || `kit_${Date.now()}`,
      expiry: item.expiry || '2027-12-31',
      ...item
    };
    // Синхронизация с бэкендом
    request('/kit/items', {
      method: 'POST',
      body: JSON.stringify(newItem)
    }).catch(() => {});

    // Локальное обновление
    const items = await this.getItems();
    items.unshift(newItem);
    localStorage.setItem(KIT_STORAGE_KEY, JSON.stringify(items));
    return newItem;
  },

  async deleteItem(id) {
    request(`/kit/items/${id}`, { method: 'DELETE' }).catch(() => {});
    const items = await this.getItems();
    const updated = items.filter(item => item.id !== id);
    localStorage.setItem(KIT_STORAGE_KEY, JSON.stringify(updated));
    return true;
  }
};
