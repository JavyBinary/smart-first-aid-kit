import { request } from './client.js';

const KIT_STORAGE_KEY = 'medai_kit';

// Стартовый набор лекарств при первой инициализации
const DEFAULT_KIT = [
  { id: 'kit_1', name: 'Ибупрофен', dosage: '200 мг', form: 'таблетки', category: 'Обезболивающие', tags: ['боль', 'воспаление', 'жар', 'головная боль'], expiry: '2027-05-01' },
  { id: 'kit_2', name: 'Парацетамол', dosage: '500 мг', form: 'таблетки', category: 'Обезболивающие', tags: ['жар', 'боль', 'простуда', 'головная боль'], expiry: '2026-12-01' },
  { id: 'kit_3', name: 'Дротаверин', dosage: '40 мг', form: 'таблетки', category: 'Спазмолитики', tags: ['спазм', 'боль', 'ЖКТ'], expiry: '2028-02-15' },
  { id: 'kit_4', name: 'Амоксициллин', dosage: '500 мг', form: 'капсулы', category: 'Антибиотики', tags: ['антибиотик', 'инфекция'], expiry: '2027-10-10' },
  { id: 'kit_5', name: 'Пантенол', dosage: '5%', form: 'спрей', category: 'Антисептики', tags: ['ожоги', 'кожа'], expiry: '2026-08-20' },
  { id: 'kit_6', name: 'Омепразол', dosage: '20 мг', form: 'капсулы', category: 'ЖКТ', tags: ['ЖКТ', 'изжога', 'желудок'], expiry: '2027-03-30' },
  { id: 'kit_7', name: 'Цетиризин', dosage: '10 мг', form: 'таблетки', category: 'Аллергия', tags: ['аллергия', 'зуд', 'ринит'], expiry: '2028-01-01' }
];

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
    localStorage.setItem(KIT_STORAGE_KEY, JSON.stringify(DEFAULT_KIT));
    return DEFAULT_KIT;
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
