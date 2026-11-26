/**
 * Catalog: Витрина популярных лекарств (стиль Яндекс Лавка / Еда)
 * Содержит карусель категорий, живой поиск и анимацию «полета» в аптечку
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';

export const CATALOG_DATABASE = [
  // Обезболивающие и жаропонижающие
  {
    id: 'cat_1',
    name: 'Нурофен Экспресс',
    dosage: 'капсулы 200 мг · 16 шт.',
    form: 'капсулы',
    category: 'Обезболивающие',
    tags: ['боль', 'головная боль', 'жар', 'воспаление'],
    status: 'otc',
    expiry: '2027-08-01',
    iconColor: '#E8F7F0'
  },
  {
    id: 'cat_2',
    name: 'Парацетамол',
    dosage: 'таблетки 500 мг · 20 шт.',
    form: 'таблетки',
    category: 'Обезболивающие',
    tags: ['жар', 'боль', 'простуда', 'головная боль'],
    status: 'otc',
    expiry: '2026-11-15',
    iconColor: '#FFF3E8'
  },
  {
    id: 'cat_3',
    name: 'Пенталгин',
    dosage: 'таблетки · 12 шт.',
    form: 'таблетки',
    category: 'Обезболивающие',
    tags: ['боль', 'спазм', 'мигрень', 'зубная боль'],
    status: 'otc',
    expiry: '2027-04-10',
    iconColor: '#E8F1FF'
  },
  {
    id: 'cat_4',
    name: 'Нимесил',
    dosage: 'порошок 100 мг · 9 пакетиков',
    form: 'порошок',
    category: 'Обезболивающие',
    tags: ['сильная боль', 'воспаление', 'зубная боль'],
    status: 'rx',
    expiry: '2027-09-01',
    iconColor: '#FFF0F0'
  },

  // Простуда и грипп
  {
    id: 'cat_5',
    name: 'Терафлю',
    dosage: 'порошок от простуды · 10 пак.',
    form: 'порошок',
    category: 'Простуда и грипп',
    tags: ['простуда', 'жар', 'насморк', 'озноб'],
    status: 'otc',
    expiry: '2026-12-30',
    iconColor: '#FFF8E6'
  },
  {
    id: 'cat_6',
    name: 'АЦЦ Лонг',
    dosage: 'шипучие таблетки 600 мг · 10 шт.',
    form: 'таблетки',
    category: 'Простуда и грипп',
    tags: ['кашель', 'мокрота', 'бронхит'],
    status: 'otc',
    expiry: '2027-03-20',
    iconColor: '#E8F7F0'
  },
  {
    id: 'cat_7',
    name: 'Снуп',
    dosage: 'спрей назальный 0.1% · 15 мл',
    form: 'спрей',
    category: 'Простуда и грипп',
    tags: ['насморк', 'заложенность носа'],
    status: 'otc',
    expiry: '2027-05-15',
    iconColor: '#EBF5FB'
  },

  // ЖКТ и пищеварение
  {
    id: 'cat_8',
    name: 'Мезим Форте',
    dosage: 'таблетки 10 000 ЕД · 20 шт.',
    form: 'таблетки',
    category: 'ЖКТ и пищеварение',
    tags: ['ЖКТ', 'тяжесть', 'переедание'],
    status: 'otc',
    expiry: '2027-10-01',
    iconColor: '#F5EEF8'
  },
  {
    id: 'cat_9',
    name: 'Омепразол',
    dosage: 'капсулы 20 мг · 30 шт.',
    form: 'капсулы',
    category: 'ЖКТ и пищеварение',
    tags: ['ЖКТ', 'изжога', 'желудок'],
    status: 'otc',
    expiry: '2028-01-10',
    iconColor: '#E8F7F0'
  },
  {
    id: 'cat_10',
    name: 'Полисорб МП',
    dosage: 'порошок банка 25 г',
    form: 'порошок',
    category: 'ЖКТ и пищеварение',
    tags: ['отравление', 'детокс', 'аллергия'],
    status: 'otc',
    expiry: '2028-06-01',
    iconColor: '#FFF3E8'
  },

  // Спазмолитики
  {
    id: 'cat_11',
    name: 'Но-Шпа',
    dosage: 'таблетки 40 мг · 24 шт.',
    form: 'таблетки',
    category: 'Спазмолитики',
    tags: ['спазм', 'боль', 'живот', 'ЖКТ'],
    status: 'otc',
    expiry: '2027-11-20',
    iconColor: '#FFF8E6'
  },
  {
    id: 'cat_12',
    name: 'Дротаверин',
    dosage: 'таблетки 40 мг · 20 шт.',
    form: 'таблетки',
    category: 'Спазмолитики',
    tags: ['спазм', 'боль', 'колики'],
    status: 'otc',
    expiry: '2027-07-15',
    iconColor: '#E8F7F0'
  },

  // Аллергия
  {
    id: 'cat_13',
    name: 'Цетрин',
    dosage: 'таблетки 10 мг · 20 шт.',
    form: 'таблетки',
    category: 'Аллергия',
    tags: ['аллергия', 'зуд', 'ринит', 'чихание'],
    status: 'otc',
    expiry: '2028-02-01',
    iconColor: '#E8F1FF'
  },
  {
    id: 'cat_14',
    name: 'Супрастин',
    dosage: 'таблетки 25 мг · 20 шт.',
    form: 'таблетки',
    category: 'Аллергия',
    tags: ['аллергия', 'отек', 'крапивница'],
    status: 'otc',
    expiry: '2027-04-01',
    iconColor: '#FFF3E8'
  },

  // Антисептики и ожоги
  {
    id: 'cat_15',
    name: 'Мирамистин',
    dosage: 'раствор 0.01% с насадкой · 150 мл',
    form: 'спрей',
    category: 'Антисептики',
    tags: ['антисептик', 'горло', 'раны'],
    status: 'otc',
    expiry: '2027-09-10',
    iconColor: '#EBF5FB'
  },
  {
    id: 'cat_16',
    name: 'Декспантенол',
    dosage: 'мазь 5% · 30 г',
    form: 'мазь',
    category: 'Антисептики',
    tags: ['ожоги', 'ссадины', 'кожа'],
    status: 'otc',
    expiry: '2026-10-25',
    iconColor: '#FFF0F0'
  }
];

export class Catalog {
  constructor(containerElement, onCustomAddClick) {
    this.container = containerElement;
    this.onCustomAddClick = onCustomAddClick;
    this.activeCategory = 'Все';
    this.searchQuery = '';
    this.categories = [
      'Все',
      'Обезболивающие',
      'Простуда и грипп',
      'ЖКТ и пищеварение',
      'Спазмолитики',
      'Аллергия',
      'Антисептики'
    ];

    this.render();
    this.attachEvents();

    store.subscribe('kit:updated', () => this.updateCardButtons());
  }

  attachEvents() {
    const searchInput = this.container.querySelector('.catalog-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderGrid();
      });
    }

    const chipsContainer = this.container.querySelector('.category-carousel');
    if (chipsContainer) {
      chipsContainer.addEventListener('click', (e) => {
        const chip = e.target.closest('.category-chip');
        if (!chip) return;
        chipsContainer.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.activeCategory = chip.dataset.cat;
        this.renderGrid();
      });
    }
  }

  triggerFlyAnimation(startBtn) {
    const startRect = startBtn.getBoundingClientRect();
    const targetElement = document.querySelector('.kit-header-title') || document.querySelector('.right-kit-column');
    if (!targetElement) return;
    const targetRect = targetElement.getBoundingClientRect();

    const particle = document.createElement('div');
    particle.className = 'flying-particle';
    particle.style.left = `${startRect.left + startRect.width / 2 - 7}px`;
    particle.style.top = `${startRect.top + startRect.height / 2 - 7}px`;
    document.body.appendChild(particle);

    // Запуск кривой Безье в правый сайдбар
    requestAnimationFrame(() => {
      particle.style.transform = `translate(${targetRect.left - startRect.left}px, ${targetRect.top - startRect.top}px) scale(0.6)`;
      particle.style.opacity = '0.3';
    });

    setTimeout(() => {
      particle.remove();
      // Эффект отскока иконки аптечки
      targetElement.classList.add('spring-transition');
      targetElement.style.transform = 'scale(1.08)';
      setTimeout(() => {
        targetElement.style.transform = 'scale(1)';
      }, 250);
    }, 650);
  }

  async handleToggleMedicine(med, btn) {
    const state = store.getState();
    const existing = state.kitItems.find(i => i.name.toLowerCase() === med.name.toLowerCase());
    
    if (existing) {
      // Уже в аптечке — удаляем из аптечки при повторном клике
      await kitApi.deleteItem(existing.id);
      store.removeKitItem(existing.id);
      this.updateCardButtons();
      return;
    }

    // Добавляем с анимацией полета в аптечку
    this.triggerFlyAnimation(btn);

    const newItem = {
      id: `kit_${Date.now()}`,
      name: med.name,
      dosage: med.dosage,
      form: med.form,
      category: med.category,
      tags: Array.isArray(med.tags) ? med.tags : [],
      quantity: 1,
      status: med.status === 'rx' || med.isPrescription ? 'rx' : 'otc',
      expiry: med.expiry || '2027-12-31'
    };

    const saved = await kitApi.addItem(newItem);
    store.addKitItem(saved && saved.id ? saved : newItem);
    store.setMascotState('happy');
    setTimeout(() => store.setMascotState('idle'), 2500);

    this.updateCardButtons();
  }

  updateCardButtons() {
    const state = store.getState();
    this.container.querySelectorAll('.med-card').forEach(card => {
      const name = card.dataset.name;
      const btn = card.querySelector('.med-card-add-btn');
      const inKitLabel = card.querySelector('.med-card-in-kit-label');
      if (!btn || !name) return;
      const inKit = state.kitItems.some(i => i.name.toLowerCase() === name.toLowerCase());
      if (inKit) {
        btn.classList.add('in-kit');
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        btn.title = 'В аптечке (нажмите, чтобы убрать)';
        if (inKitLabel) inKitLabel.style.visibility = 'visible';
      } else {
        btn.classList.remove('in-kit');
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;
        btn.title = 'Добавить в аптечку';
        if (inKitLabel) inKitLabel.style.visibility = 'hidden';
      }
    });
  }

  renderGrid() {
    const grid = this.container.querySelector('.medicine-grid');
    if (!grid) return;

    const filtered = CATALOG_DATABASE.filter(item => {
      const matchCat = this.activeCategory === 'Все' || item.category === this.activeCategory;
      const matchQuery = !this.searchQuery ||
        item.name.toLowerCase().includes(this.searchQuery) ||
        item.category.toLowerCase().includes(this.searchQuery) ||
        item.tags.some(t => t.toLowerCase().includes(this.searchQuery));
      return matchCat && matchQuery;
    });

    const state = store.getState();
    let html = '';

    filtered.forEach((med, index) => {
      const inKit = state.kitItems.some(i => i.name.toLowerCase() === med.name.toLowerCase());
      const delay = (index % 10) * 0.03;

      html += `
        <div class="med-card" data-name="${med.name}" style="animation-delay: ${delay}s">
          <div class="med-card-visual" style="background: ${med.iconColor}">
            <!-- Статусный бейдж надежно внутри визуала -->
            <div class="med-card-status-pill ${med.status}">
              ${med.status === 'otc' ? 'Без рецепта' : 'По рецепту'}
            </div>

            <!-- Векторная медицинская упаковка -->
            <svg class="med-card-icon-svg" viewBox="0 0 64 64" fill="none">
              <rect x="14" y="10" width="36" height="44" rx="8" fill="#FFFFFF" stroke="#00B074" stroke-width="2.5"/>
              <rect x="20" y="24" width="24" height="6" rx="3" fill="#00B074" fill-opacity="0.3"/>
              <circle cx="26" cy="38" r="4" fill="#00B074"/>
              <circle cx="38" cy="38" r="4" fill="#00B074"/>
            </svg>
          </div>

          <div class="med-card-category">${med.category}</div>
          <div class="med-card-title">${med.name}</div>
          <div class="med-card-dosage">${med.dosage}</div>

          <div class="med-card-footer">
            <div class="med-card-in-kit-label" style="visibility: ${inKit ? 'visible' : 'hidden'}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              В аптечке
            </div>

            <button class="med-card-add-btn tap-effect ${inKit ? 'in-kit' : ''}" data-name="${med.name}" title="${inKit ? 'В аптечке (нажмите, чтобы убрать)' : 'Добавить в аптечку'}">
              ${inKit ?
                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>` :
                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`
              }
            </button>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;

    // Навешивание кликов на переключатель (Toggle)
    grid.querySelectorAll('.med-card-add-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const medName = btn.dataset.name;
        const med = CATALOG_DATABASE.find(m => m.name === medName);
        if (med) this.handleToggleMedicine(med, btn);
      });
    });

    // Клик по тексту "В аптечке" также переключает
    grid.querySelectorAll('.med-card-in-kit-label').forEach(label => {
      label.addEventListener('click', (e) => {
        e.stopPropagation();
        const card = label.closest('.med-card');
        const medName = card ? card.dataset.name : null;
        const btn = card ? card.querySelector('.med-card-add-btn') : null;
        const med = CATALOG_DATABASE.find(m => m.name === medName);
        if (med && btn) this.handleToggleMedicine(med, btn);
      });
    });
  }

  render() {
    this.container.innerHTML = `
      <div class="catalog-view-wrap">
        <!-- Поиск по каталогу -->
        <div class="catalog-search-bar">
          <svg class="catalog-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input type="text" class="catalog-search-input" placeholder="Поиск лекарств, симптомов или категорий...">
        </div>

        <!-- Карусель категорий в стиле Яндекс Еды -->
        <div class="category-carousel">
          ${this.categories.map((cat, i) => `
            <button class="category-chip tap-effect ${i === 0 ? 'active' : ''}" data-cat="${cat}">
              ${cat}
            </button>
          `).join('')}
        </div>

        <!-- Сетка карточек -->
        <div class="medicine-grid"></div>
      </div>
    `;

    this.renderGrid();
  }
}
