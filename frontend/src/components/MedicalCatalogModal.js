/**
 * MedicalCatalogModal: Обширный справочник нозологий, заболеваний и аллергенов
 * Шелковистое модальное окно с мгновенным поиском, фильтрами и выбором без мерцаний
 */

import { store } from '../state/store.js';
import { profileApi } from '../api/profile.api.js';

export const MEDICAL_CATALOG_DATA = {
  chronic: [
    // ЖКТ
    { id: 'c1', name: 'Гастрит (хронический)', category: 'ЖКТ' },
    { id: 'c2', name: 'Язвенная болезнь желудка и ДПК', category: 'ЖКТ' },
    { id: 'c3', name: 'ГЭРБ (рефлюкс-эзофагит)', category: 'ЖКТ' },
    { id: 'c4', name: 'Хронический панкреатит', category: 'ЖКТ' },
    { id: 'c5', name: 'Синдром раздраженного кишечника (СРК)', category: 'ЖКТ' },
    { id: 'c6', name: 'Хронический холецистит', category: 'ЖКТ' },
    { id: 'c7', name: 'Желчнокаменная болезнь', category: 'ЖКТ' },
    { id: 'c8', name: 'Язвенный колит / болезнь Крона', category: 'ЖКТ' },
    { id: 'c9', name: 'Дисбактериоз / хроническая диарея', category: 'ЖКТ' },
    // Кардиология и сосуды
    { id: 'c10', name: 'Артериальная гипертензия (гипертония)', category: 'Кардиология' },
    { id: 'c11', name: 'Артериальная гипотензия (низкое давление)', category: 'Кардиология' },
    { id: 'c12', name: 'Ишемическая болезнь сердца (ИБС)', category: 'Кардиология' },
    { id: 'c13', name: 'Стенокардия напряжения', category: 'Кардиология' },
    { id: 'c14', name: 'Аритмия / тахикардия / экстрасистолия', category: 'Кардиология' },
    { id: 'c15', name: 'Хроническая сердечная недостаточность (ХСН)', category: 'Кардиология' },
    { id: 'c16', name: 'Варикозное расширение вен / тромбофлебит', category: 'Кардиология' },
    { id: 'c17', name: 'Атеросклероз сосудов', category: 'Кардиология' },
    // Пульмонология и ЛОР
    { id: 'c18', name: 'Бронхиальная астма', category: 'Пульмонология' },
    { id: 'c19', name: 'Аспириновая астма (непереносимость НПВП)', category: 'Пульмонология' },
    { id: 'c20', name: 'ХОБЛ (обструктивная болезнь легких)', category: 'Пульмонология' },
    { id: 'c21', name: 'Хронический бронхит', category: 'Пульмонология' },
    { id: 'c22', name: 'Хронический синусит / гайморит', category: 'Пульмонология' },
    { id: 'c23', name: 'Хронический тонзиллит / фарингит', category: 'Пульмонология' },
    { id: 'c24', name: 'Аллергический ринит (круглогодичный)', category: 'Пульмонология' },
    // Эндокринология и обмен веществ
    { id: 'c25', name: 'Сахарный диабет 1 типа', category: 'Эндокринология' },
    { id: 'c26', name: 'Сахарный диабет 2 типа', category: 'Эндокринология' },
    { id: 'c27', name: 'Инсулинорезистентность / предиабет', category: 'Эндокринология' },
    { id: 'c28', name: 'Гипотиреоз', category: 'Эндокринология' },
    { id: 'c29', name: 'Тиреотоксикоз (гипертиреоз)', category: 'Эндокринология' },
    { id: 'c30', name: 'Аутоиммунный тиреоидит', category: 'Эндокринология' },
    { id: 'c31', name: 'Подагра (гиперурикемия)', category: 'Эндокринология' },
    // Печень и почки
    { id: 'c32', name: 'Хронический гепатит / печеночная недостаточность', category: 'Печень и почки' },
    { id: 'c33', name: 'Жировой гепатоз печени', category: 'Печень и почки' },
    { id: 'c34', name: 'Синдром Жильбера', category: 'Печень и почки' },
    { id: 'c35', name: 'Хронический пиелонефрит', category: 'Печень и почки' },
    { id: 'c36', name: 'Хроническая болезнь почек (ХБП / ХПН)', category: 'Печень и почки' },
    { id: 'c37', name: 'Мочекаменная болезнь', category: 'Печень и почки' },
    { id: 'c38', name: 'Хронический цистит', category: 'Печень и почки' },
    // Неврология
    { id: 'c39', name: 'Мигрень (с аурой / без ауры)', category: 'Неврология' },
    { id: 'c40', name: 'Головная боль напряжения', category: 'Неврология' },
    { id: 'c41', name: 'Эпилепсия / судорожный синдром', category: 'Неврология' },
    { id: 'c42', name: 'Хроническая бессонница / нарушения сна', category: 'Неврология' },
    { id: 'c43', name: 'Тревожное расстройство / панические атаки', category: 'Неврология' },
    { id: 'c44', name: 'Вегетососудистая дистония (ВСД)', category: 'Неврология' },
    { id: 'c45', name: 'Невралгия тройничного нерва / ишиас', category: 'Неврология' },
    // Опорно-двигательный аппарат
    { id: 'c46', name: 'Остеохондроз позвоночника', category: 'Опорно-двигательный' },
    { id: 'c47', name: 'Остеоартроз суставов', category: 'Опорно-двигательный' },
    { id: 'c48', name: 'Ревматоидный артрит', category: 'Опорно-двигательный' },
    { id: 'c49', name: 'Межпозвоночная грыжа / радикулит', category: 'Опорно-двигательный' },
    { id: 'c50', name: 'Остеопороз', category: 'Опорно-двигательный' },
    // Офтальмология и кожа
    { id: 'c51', name: 'Закрытоугольная глаукома', category: 'Офтальмология и кожа' },
    { id: 'c52', name: 'Синдром сухого глаза', category: 'Офтальмология и кожа' },
    { id: 'c53', name: 'Атопический дерматит / экзема', category: 'Офтальмология и кожа' },
    { id: 'c54', name: 'Псориаз', category: 'Офтальмология и кожа' },
    { id: 'c55', name: 'Хроническая крапивница', category: 'Офтальмология и кожа' },
    // Кровь и особые состояния
    { id: 'c56', name: 'Железодефицитная анемия', category: 'Кровь и особые' },
    { id: 'c57', name: 'Нарушения свертываемости крови / тромбофилия', category: 'Кровь и особые' },
    { id: 'c58', name: 'Дефицит Г6ФД', category: 'Кровь и особые' },
    { id: 'c59', name: 'Беременность (I триместр)', category: 'Кровь и особые' },
    { id: 'c60', name: 'Беременность (II триместр)', category: 'Кровь и особые' },
    { id: 'c61', name: 'Беременность (III триместр)', category: 'Кровь и особые' },
    { id: 'c62', name: 'Грудное вскармливание (лактация)', category: 'Кровь и особые' }
  ],
  allergies: [
    // Лекарственные
    { id: 'a1', name: 'Пенициллины (Амоксициллин, Аугментин)', category: 'Лекарственные' },
    { id: 'a2', name: 'Цефалоспорины (Цефтриаксон, Супракс)', category: 'Лекарственные' },
    { id: 'a3', name: 'Макролиды (Азитромицин, Кларитромицин)', category: 'Лекарственные' },
    { id: 'a4', name: 'Тетрациклины (Доксициклин)', category: 'Лекарственные' },
    { id: 'a5', name: 'Фторхинолоны (Ципрофлоксацин, Левофлоксацин)', category: 'Лекарственные' },
    { id: 'a6', name: 'Аспирин и салицилаты', category: 'Лекарственные' },
    { id: 'a7', name: 'НПВП (Ибупрофен, Нимесулид, Кеторолак, Диклофенак)', category: 'Лекарственные' },
    { id: 'a8', name: 'Парацетамол', category: 'Лекарственные' },
    { id: 'a9', name: 'Метамизол натрия (Анальгин, Спазмалгон)', category: 'Лекарственные' },
    { id: 'a10', name: 'Сульфаниламиды (Альбуцид, Бисептол)', category: 'Лекарственные' },
    { id: 'a11', name: 'Лидокаин / Новокаин (местные анестетики)', category: 'Лекарственные' },
    { id: 'a12', name: 'Йодсодержащие препараты и контрасты', category: 'Лекарственные' },
    { id: 'a13', name: 'Хлоргексидин / антисептики', category: 'Лекарственные' },
    { id: 'a14', name: 'Барбитураты / Фенобарбитал (Корвалол)', category: 'Лекарственные' },
    { id: 'a15', name: 'Дротаверин / Но-шпа', category: 'Лекарственные' },
    { id: 'a16', name: 'Витамины группы B (B1, B6, B12)', category: 'Лекарственные' },
    { id: 'a17', name: 'Антигистаминные 1 поколения', category: 'Лекарственные' },
    // Пищевые
    { id: 'a18', name: 'Непереносимость лактозы', category: 'Пищевые' },
    { id: 'a19', name: 'Белок коровьего молока', category: 'Пищевые' },
    { id: 'a20', name: 'Непереносимость фруктозы', category: 'Пищевые' },
    { id: 'a21', name: 'Глютен (целиакия / пшеница)', category: 'Пищевые' },
    { id: 'a22', name: 'Арахис', category: 'Пищевые' },
    { id: 'a23', name: 'Древесные орехи (грецкий, фундук, миндаль)', category: 'Пищевые' },
    { id: 'a24', name: 'Цитрусовые (лимон, апельсин, грейпфрут)', category: 'Пищевые' },
    { id: 'a25', name: 'Рыба и рыбий жир', category: 'Пищевые' },
    { id: 'a26', name: 'Морепродукты (креветки, мидии, кальмары)', category: 'Пищевые' },
    { id: 'a27', name: 'Куриный белок / яйца', category: 'Пищевые' },
    { id: 'a28', name: 'Соя и соевый лецитин', category: 'Пищевые' },
    { id: 'a29', name: 'Мед и продукты пчеловодства (прополис)', category: 'Пищевые' },
    { id: 'a30', name: 'Клубника / красные ягоды', category: 'Пищевые' },
    { id: 'a31', name: 'Шоколад / какао', category: 'Пищевые' },
    { id: 'a32', name: 'Пищевые красители и консерванты (сульфиты, бензоаты)', category: 'Пищевые' },
    // Сезонные
    { id: 'a33', name: 'Пыльца березы / ольхи / орешника', category: 'Сезонные' },
    { id: 'a34', name: 'Цветение злаковых трав (тимофеевка, рожь)', category: 'Сезонные' },
    { id: 'a35', name: 'Полынь и амброзия', category: 'Сезонные' },
    { id: 'a36', name: 'Тополиный пух и одуванчик', category: 'Сезонные' },
    { id: 'a37', name: 'Споры плесневых грибков (Alternaria, Aspergillus)', category: 'Сезонные' },
    // Бытовые и прочие
    { id: 'a38', name: 'Домашняя пыль и пылевые клещи', category: 'Бытовые' },
    { id: 'a39', name: 'Шерсть и эпителий кошек', category: 'Бытовые' },
    { id: 'a40', name: 'Шерсть и эпителий собак', category: 'Бытовые' },
    { id: 'a41', name: 'Укусы насекомых (пчелы, осы, комары)', category: 'Бытовые' },
    { id: 'a42', name: 'Латекс и медицинские пластыри', category: 'Бытовые' },
    { id: 'a43', name: 'Ментол и эфирные масла (мята, эвкалипт)', category: 'Бытовые' },
    { id: 'a44', name: 'Никель и металлы', category: 'Бытовые' },
    { id: 'a45', name: 'Холодовая крапивница (аллергия на холод)', category: 'Бытовые' }
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
