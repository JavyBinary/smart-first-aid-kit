/**
 * MedicalCatalogModal: Обширный справочник нозологий, заболеваний и аллергенов
 * Шелковистое модальное окно с мгновенным поиском, фильтрами и выбором без мерцаний
 */

import { store } from '../state/store.js';
import { profileApi } from '../api/profile.api.js';

export const MEDICAL_CATALOG_DATA = {
  chronic: [
    { id: 'c1', name: 'Гастрит (хронический)', category: 'ЖКТ' },
    { id: 'c2', name: 'Язвенная болезнь желудка / ДПК', category: 'ЖКТ' },
    { id: 'c3', name: 'ГЭРБ (рефлюкс-эзофагит)', category: 'ЖКТ' },
    { id: 'c4', name: 'Хронический панкреатит', category: 'ЖКТ' },
    { id: 'c5', name: 'Синдром раздраженного кишечника (СРК)', category: 'ЖКТ' },
    { id: 'c6', name: 'Хронический холецистит', category: 'ЖКТ' },
    { id: 'c7', name: 'Артериальная гипертензия (гипертония)', category: 'Кардиология' },
    { id: 'c8', name: 'Ишемическая болезнь сердца (ИБС)', category: 'Кардиология' },
    { id: 'c9', name: 'Аритмия / тахикардия', category: 'Кардиология' },
    { id: 'c10', name: 'Хроническая сердечная недостаточность (ХСН)', category: 'Кардиология' },
    { id: 'c11', name: 'Бронхиальная астма', category: 'Пульмонология' },
    { id: 'c12', name: 'ХОБЛ (обструктивная болезнь легких)', category: 'Пульмонология' },
    { id: 'c13', name: 'Хронический бронхит', category: 'Пульмонология' },
    { id: 'c14', name: 'Сахарный диабет 1 типа', category: 'Эндокринология' },
    { id: 'c15', name: 'Сахарный диабет 2 типа', category: 'Эндокринология' },
    { id: 'c16', name: 'Гипотиреоз', category: 'Эндокринология' },
    { id: 'c17', name: 'Подагра (гиперурикемия)', category: 'Эндокринология' },
    { id: 'c18', name: 'Мигрень / кластерные головные боли', category: 'Неврология' },
    { id: 'c19', name: 'Остеохондроз позвоночника', category: 'Опорно-двигательный' },
    { id: 'c20', name: 'Ревматоидный артрит', category: 'Опорно-двигательный' },
    { id: 'c21', name: 'Хронический пиелонефрит', category: 'Нефрология' },
    { id: 'c22', name: 'Мочекаменная болезнь', category: 'Нефрология' }
  ],
  allergies: [
    { id: 'a1', name: 'Пенициллины (Амоксициллин, Аугментин)', category: 'Лекарственные' },
    { id: 'a2', name: 'Цефалоспорины', category: 'Лекарственные' },
    { id: 'a3', name: 'Аспирин и НПВП (Ибупрофен, Диклофенак)', category: 'Лекарственные' },
    { id: 'a4', name: 'Сульфаниламиды (Бисептол)', category: 'Лекарственные' },
    { id: 'a5', name: 'Лидокаин / Новокаин', category: 'Лекарственные' },
    { id: 'a6', name: 'Йодсодержащие препараты', category: 'Лекарственные' },
    { id: 'a7', name: 'Непереносимость лактозы', category: 'Пищевые' },
    { id: 'a8', name: 'Глютен (целиакия)', category: 'Пищевые' },
    { id: 'a9', name: 'Арахис и древесные орехи', category: 'Пищевые' },
    { id: 'a10', name: 'Цитрусовые', category: 'Пищевые' },
    { id: 'a11', name: 'Рыба и морепродукты', category: 'Пищевые' },
    { id: 'a12', name: 'Куриный белок (яйца)', category: 'Пищевые' },
    { id: 'a13', name: 'Пыльца березы / ольхи (поллиноз)', category: 'Сезонные' },
    { id: 'a14', name: 'Цветение злаковых и луговых трав', category: 'Сезонные' },
    { id: 'a15', name: 'Полынь и амброзия', category: 'Сезонные' },
    { id: 'a16', name: 'Домашняя пыль и клещи', category: 'Бытовые' },
    { id: 'a17', name: 'Эпителий и шерсть животных', category: 'Бытовые' }
  ]
};

export class MedicalCatalogModal {
  constructor() {
    this.overlay = null;
    this.type = 'chronic'; // 'chronic' | 'allergies'
    this.searchQuery = '';
    this.activeCategory = 'Все';
    this.hasChanges = false;
    this.init();
  }

  init() {
    this.overlay = document.createElement('div');
    this.overlay.className = 'med-catalog-overlay';
    this.overlay.style.display = 'none';
    document.body.appendChild(this.overlay);

    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) this.close();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.overlay.style.display === 'flex') {
        this.close();
      }
    });
  }

  open(type = 'chronic') {
    this.type = type;
    this.searchQuery = '';
    this.activeCategory = 'Все';
    this.hasChanges = false;
    this.buildShell();
    this.renderGrid();
    this.overlay.style.display = 'flex';
  }

  close() {
    this.overlay.style.display = 'none';
    if (this.hasChanges) {
      const profile = store.getState().healthProfile;
      store.notify('health:updated', profile);
      if (store.isAuthenticated()) {
        profileApi.updateProfile(profile).catch(() => {});
      }
    }
  }

  buildShell() {
    const isChronic = this.type === 'chronic';
    const title = isChronic ? 'Справочник заболеваний и диагнозов' : 'Справочник аллергий и непереносимостей';
    const allItems = MEDICAL_CATALOG_DATA[this.type] || [];
    const categories = ['Все', ...new Set(allItems.map(i => i.category))];

    this.overlay.innerHTML = `
      <div class="med-catalog-card">
        <div class="med-catalog-header">
          <div class="med-catalog-title-wrap">
            <div class="med-catalog-icon ${isChronic ? 'green' : 'red'}">
              ${isChronic ? `
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <path d="M12 2v20M2 12h20"></path>
                </svg>
              ` : `
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                  <line x1="12" y1="9" x2="12" y2="13"></line>
                  <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
              `}
            </div>
            <div>
              <h3 class="med-catalog-title">${title}</h3>
              <p class="med-catalog-subtitle">Выберите параметры для проверки совместимости и дозировок лекарств</p>
            </div>
          </div>
          <button class="med-catalog-close-btn" id="closeMedCatalogBtn">&times;</button>
        </div>

        <div class="med-catalog-toolbar">
          <div class="med-catalog-search-wrap">
            <svg class="med-catalog-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input type="text" id="medCatalogSearchInput" class="med-catalog-search-input" placeholder="Поиск по справочнику..." value="${this.searchQuery}">
          </div>

          <div class="med-catalog-categories" id="medCatalogCatContainer">
            ${categories.map(cat => `
              <button class="med-catalog-cat-pill tap-effect ${this.activeCategory === cat ? 'active' : ''}" data-cat="${cat}">
                ${cat}
              </button>
            `).join('')}
          </div>
        </div>

        <div class="med-catalog-body">
          <div class="med-catalog-grid" id="medCatalogGrid"></div>
        </div>

        <div class="med-catalog-footer">
          <div class="med-catalog-custom-wrap">
            <input type="text" id="medCatalogCustomInput" class="med-catalog-custom-input" placeholder="Добавить свой вариант...">
            <button class="med-catalog-custom-add-btn tap-effect" id="medCatalogCustomAddBtn">+ Добавить</button>
          </div>
          <button class="btn-brand-primary tap-effect" id="medCatalogDoneBtn" style="padding: 10px 24px; border-radius: var(--radius-md); font-weight: 600; cursor: pointer; flex-shrink: 0; box-shadow: var(--shadow-brand);">Готово</button>
        </div>
      </div>
    `;

    // Закрытие и кнопка Готово
    this.overlay.querySelector('#closeMedCatalogBtn').onclick = () => this.close();
    this.overlay.querySelector('#medCatalogDoneBtn').onclick = () => this.close();

    // Поиск
    const searchInp = this.overlay.querySelector('#medCatalogSearchInput');
    if (searchInp) {
      searchInp.oninput = (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderGrid();
      };
    }

    // Категории: мягкое переключение без пересоздания каркаса
    const catContainer = this.overlay.querySelector('#medCatalogCatContainer');
    if (catContainer) {
      catContainer.onclick = (e) => {
        const btn = e.target.closest('.med-catalog-cat-pill');
        if (!btn) return;
        catContainer.querySelectorAll('.med-catalog-cat-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeCategory = btn.dataset.cat;
        this.renderGrid();
      };
    }

    // Добавление своего варианта
    const addCustom = () => {
      const inp = this.overlay.querySelector('#medCatalogCustomInput');
      const val = inp ? inp.value.trim() : '';
      if (!val) return;
      const isChronic = this.type === 'chronic';
      const key = isChronic ? 'chronic' : 'allergies';
      const curProfile = { ...store.getState().healthProfile };
      if (!curProfile[key]) curProfile[key] = [];
      if (!curProfile[key].includes(val)) {
        curProfile[key].push(val);
        store.setHealthProfile(curProfile, true);
        this.hasChanges = true;
        this.renderGrid();
      }
      inp.value = '';
    };

    const addBtn = this.overlay.querySelector('#medCatalogCustomAddBtn');
    if (addBtn) addBtn.onclick = addCustom;

    const customInput = this.overlay.querySelector('#medCatalogCustomInput');
    if (customInput) {
      customInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addCustom();
        }
      };
    }
  }

  renderGrid() {
    const grid = this.overlay.querySelector('#medCatalogGrid');
    if (!grid) return;

    const isChronic = this.type === 'chronic';
    const allItems = MEDICAL_CATALOG_DATA[this.type] || [];
    const profile = store.getState().healthProfile || {};
    const selectedList = isChronic ? (profile.chronic || []) : (profile.allergies || []);

    const filtered = allItems.filter(item => {
      const matchCat = this.activeCategory === 'Все' || item.category === this.activeCategory;
      const matchQuery = !this.searchQuery || item.name.toLowerCase().includes(this.searchQuery) || item.category.toLowerCase().includes(this.searchQuery);
      return matchCat && matchQuery;
    });

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div class="med-catalog-empty">
          Ничего не найдено. Нажмите «+ Добавить свой вариант» ниже.
        </div>
      `;
      return;
    }

    grid.innerHTML = filtered.map(item => {
      const isSelected = selectedList.includes(item.name);
      return `
        <div class="med-catalog-item-card tap-effect ${isSelected ? 'selected' : ''}" data-name="${item.name}">
          <div class="item-card-checkbox">
            ${isSelected ? '✓' : ''}
          </div>
          <div class="item-card-info">
            <span class="item-card-category">${item.category}</span>
            <span class="item-card-name">${item.name}</span>
          </div>
        </div>
      `;
    }).join('');

    // Мгновенный тоггл без перезагрузки всей сетки
    grid.querySelectorAll('.med-catalog-item-card').forEach(card => {
      card.onclick = () => {
        const val = card.dataset.name;
        const curProfile = { ...store.getState().healthProfile };
        const key = isChronic ? 'chronic' : 'allergies';
        if (!curProfile[key]) curProfile[key] = [];

        const checkbox = card.querySelector('.item-card-checkbox');
        if (curProfile[key].includes(val)) {
          curProfile[key] = curProfile[key].filter(item => item !== val);
          card.classList.remove('selected');
          if (checkbox) checkbox.textContent = '';
        } else {
          curProfile[key].push(val);
          card.classList.add('selected');
          if (checkbox) checkbox.textContent = '✓';
        }

        store.setHealthProfile(curProfile, true); // silent update
        this.hasChanges = true;
      };
    });
  }
}

export const medicalCatalogModal = new MedicalCatalogModal();
