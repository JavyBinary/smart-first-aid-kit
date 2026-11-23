/**
 * Kit: Правая колонка управления Домашней аптечкой и Интеллектуальной медкартой
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';
import { ConfirmModal } from './ConfirmModal.js';
import { medicalCatalogModal } from './MedicalCatalogModal.js';
import { addMedicineModal } from './AddMedicineModal.js';

export const ALLERGY_PRESETS = ['Пенициллин', 'Аспирин', 'Сульфаниламиды', 'Цитрусовые', 'Пыльца', 'Лидокаин'];
export const CHRONIC_PRESETS = ['Гастрит', 'Гипертония', 'Астма', 'Сахарный диабет', 'Язва желудка', 'Мигрень'];
export const AGE_PRESETS = ['Взрослый', 'Пожилой (65+)', 'Ребенок (до 12)', 'Подросток'];

export class Kit {
  constructor(containerElement) {
    this.container = containerElement;
    this.searchQuery = '';
    this.selectedTags = [];
    this.allTags = ['жар', 'боль', 'головная боль', 'воспаление', 'спазм', 'ЖКТ', 'антибиотик', 'аллергия', 'ожоги'];
    this.activeTab = 'kit'; // 'kit' | 'medcard'

    this.render();
    this.attachEvents();

    store.subscribe('kit:updated', () => this.renderList());
    store.subscribe('selectedPills:updated', () => this.updateSelectionStyles());
    store.subscribe('health:updated', () => {
      // Предотвращаем потерю фокуса при вводе в текстовые инпуты
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.id === 'newNoteInput' || activeEl.id === 'newAllergyInput' || activeEl.id === 'newChronicInput')) {
        return;
      }
      const medcardMount = this.container.querySelector('#medcardTabContent');
      const savedScroll = medcardMount ? medcardMount.scrollTop : 0;
      this.renderMedcard();
      if (medcardMount) medcardMount.scrollTop = savedScroll;
    });
  }

  attachEvents() {
    // 1. Переключение табов [ Моя аптечка | Медкарта ]
    const kitTabBtn = this.container.querySelector('#rightTabKitBtn');
    const medcardTabBtn = this.container.querySelector('#rightTabMedcardBtn');
    const kitContent = this.container.querySelector('#kitTabContent');
    const medcardContent = this.container.querySelector('#medcardTabContent');

    if (kitTabBtn && medcardTabBtn) {
      kitTabBtn.addEventListener('click', () => {
        this.activeTab = 'kit';
        kitTabBtn.classList.add('active');
        medcardTabBtn.classList.remove('active');
        if (kitContent) kitContent.style.display = 'flex';
        if (medcardContent) medcardContent.style.display = 'none';
      });

      medcardTabBtn.addEventListener('click', () => {
        this.activeTab = 'medcard';
        medcardTabBtn.classList.add('active');
        kitTabBtn.classList.remove('active');
        if (kitContent) kitContent.style.display = 'none';
        if (medcardContent) {
          medcardContent.style.display = 'flex';
          this.renderMedcard();
        }
      });
    }

    // 2. Кнопка добавления своего лекарства над поиском
    const openAddMedBtn = this.container.querySelector('#openAddMedicineBtn');
    if (openAddMedBtn) {
      openAddMedBtn.onclick = () => addMedicineModal.open();
    }

    // 3. Поиск по аптечке
    const searchInput = this.container.querySelector('#kitSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderList();
      });
    }

    // 3. Теги-симптомы
    const tagsContainer = this.container.querySelector('#kitTagsContainer');
    if (tagsContainer) {
      tagsContainer.addEventListener('click', (e) => {
        const chip = e.target.closest('.kit-tag-chip');
        if (!chip) return;
        const tag = chip.dataset.tag;
        if (this.selectedTags.includes(tag)) {
          this.selectedTags = this.selectedTags.filter(t => t !== tag);
          chip.classList.remove('active');
        } else {
          this.selectedTags.push(tag);
          chip.classList.add('active');
        }
        this.renderList();
      });
    }
  }

  async handleDeleteItem(id, name) {
    const confirmed = await ConfirmModal.confirm({
      title: 'Удаление из аптечки',
      message: `Удалить «${name}» из домашней аптечки?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      danger: true
    });

    if (confirmed) {
      store.removeKitItem(id);
      kitApi.deleteItem(id);
    }
  }

  updateSelectionStyles() {
    const selected = store.getState().selectedPills;
    this.container.querySelectorAll('.kit-item-card').forEach(card => {
      const id = card.dataset.id;
      const isSelected = selected.some(p => p.id === id);
      card.classList.toggle('selected-for-chat', isSelected);
    });
  }

  getExpiryStatus(item) {
    if (!item) return 'safe';
    const cat = item.category || '';
    if (cat.includes('Антибиот') || cat.includes('Спец') || item.isSpecial) {
      return 'blue';
    }
    const expiryDateStr = typeof item === 'string' ? item : item.expiry;
    if (!expiryDateStr) return 'safe';
    const now = new Date();
    const expiry = new Date(expiryDateStr);
    const diffDays = (expiry - now) / (1000 * 60 * 60 * 24);

    if (diffDays < 0) return 'expired';
    if (diffDays <= 60) return 'warning';
    return 'safe';
  }

  formatAge(ageVal) {
    const n = parseInt(ageVal, 10);
    if (isNaN(n) || n === 0) return 'Младенец (< 1 года)';
    const lastTwo = n % 100;
    const lastOne = n % 10;
    if (lastTwo >= 11 && lastTwo <= 19) return `${n} лет`;
    if (lastOne === 1) return `${n} год`;
    if (lastOne >= 2 && lastOne <= 4) return `${n} года`;
    return `${n} лет`;
  }

  renderList() {
    const list = this.container.querySelector('#kitItemsList');
    const summaryCount = this.container.querySelector('#kitSummaryCount');
    if (!list) return;

    let items = store.getState().kitItems;

    if (summaryCount) {
      summaryCount.textContent = `${items.length} препаратов`;
    }

    // Фильтрация по поиску
    if (this.searchQuery) {
      items = items.filter(item => {
        const inName = item.name.toLowerCase().includes(this.searchQuery);
        const inCategory = item.category ? item.category.toLowerCase().includes(this.searchQuery) : false;
        const inTags = item.tags ? item.tags.some(t => t.toLowerCase().includes(this.searchQuery)) : false;
        return inName || inCategory || inTags;
      });
    }

    // Фильтрация по тегам
    if (this.selectedTags.length > 0) {
      items = items.filter(item => {
        if (!item.tags) return false;
        return this.selectedTags.every(st => item.tags.includes(st));
      });
    }

    if (items.length === 0) {
      list.innerHTML = `
        <div class="kit-empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="6" width="18" height="15" rx="3"></rect>
            <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"></path>
          </svg>
          <p>В аптечке нет подходящих препаратов</p>
        </div>
      `;
      return;
    }

    const selectedPills = store.getState().selectedPills;

    // Восстановленный красивый исходный дизайн карточек аптечки с цветными точками и рецептурным статусом
    list.innerHTML = items.map(item => {
      const isSelected = selectedPills.some(p => p.id === item.id);
      const expiryStatus = this.getExpiryStatus(item);
      const isRx = item.is_prescription || item.isPrescription || (item.category && item.category.includes('Антибиот'));

      return `
        <div class="kit-item-card tap-effect ${isSelected ? 'selected-for-chat' : ''}" data-id="${item.id}">
          <div class="kit-item-meta">
            <div class="kit-item-name">${item.name}</div>
            <div class="kit-item-details">
              ${item.dosage || ''}${item.dosage && item.form ? ' · ' : ''}${item.form || ''}
              <span class="kit-rx-tag ${isRx ? 'rx' : 'otc'}">${isRx ? 'По рецепту' : 'Без рецепта'}</span>
            </div>
          </div>
          <div class="kit-item-right">
            <span class="expiry-dot ${expiryStatus}"></span>
            <button class="kit-item-delete tap-effect" data-id="${item.id}" data-name="${item.name}" title="Удалить из аптечки">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Клик по карточке — выбор в чат
    list.querySelectorAll('.kit-item-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.kit-item-delete')) return;
        const id = card.dataset.id;
        const item = store.getState().kitItems.find(i => i.id === id);
        if (item) store.togglePillSelection(item);
      });
    });

    // Клик по удалению через ConfirmModal
    list.querySelectorAll('.kit-item-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleDeleteItem(btn.dataset.id, btn.dataset.name);
      });
    });
  }

  renderMedcard() {
    const medcardMount = this.container.querySelector('#medcardTabContent');
    if (!medcardMount) return;

    const profile = store.getState().healthProfile || {
      allergies: ['Пенициллин'],
      chronic: ['Гастрит'],
      age: 'Взрослый',
      weight: 70,
      notes: []
    };

    // Нормализация заметок в массив
    let notesList = [];
    if (Array.isArray(profile.notes)) {
      notesList = profile.notes;
    } else if (typeof profile.notes === 'string' && profile.notes.trim()) {
      notesList = [profile.notes.trim()];
    }

    let currentAge = parseInt(profile.age, 10);
    if (isNaN(currentAge)) {
      if (typeof profile.age === 'string' && profile.age.includes('Пожилой')) currentAge = 68;
      else if (typeof profile.age === 'string' && profile.age.includes('Ребенок')) currentAge = 10;
      else currentAge = 24;
    }

    const currentWeight = Number(profile.weight) || 70;

    medcardMount.innerHTML = `
      <div class="medcard-panel-wrap">
        <!-- 1. Аллергии и непереносимости -->
        <div class="medcard-section">
          <div class="medcard-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FF3B30" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            Аллергии и непереносимости
          </div>

          <!-- Выбранные аллергены карточками в стиле аптечки -->
          <div class="medcard-items-group" id="medcardAllergiesList">
            ${(profile.allergies || []).map(a => `
              <div class="medcard-item-card">
                <div class="medcard-item-title">
                  <span class="medcard-item-dot red"></span>
                  <span>${a}</span>
                </div>
                <button class="medcard-item-del-btn tap-effect" data-type="allergy" data-val="${a}" title="Удалить">&times;</button>
              </div>
            `).join('')}
            ${(!profile.allergies || profile.allergies.length === 0) ? `
              <div style="font-size: 12px; color: var(--text-muted); padding: 4px 2px;">Аллергены не указаны</div>
            ` : ''}
          </div>

          <!-- Кнопка каталога -->
          <button class="medcard-action-btn tap-effect" id="openAllergyCatalogBtn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            + Справочник аллергенов
          </button>

          <!-- Быстрые пресеты -->
          <div class="medcard-presets-wrap">
            <span class="presets-label">Быстрый выбор:</span>
            <div class="presets-row">
              ${ALLERGY_PRESETS.map(p => {
                const active = (profile.allergies || []).includes(p);
                return `
                  <button class="preset-pill tap-effect ${active ? 'active' : ''}" data-type="allergy" data-val="${p}">
                    ${active ? '✓ ' : '+ '}${p}
                  </button>
                `;
              }).join('')}
            </div>
          </div>

          <div class="medcard-add-row">
            <input type="text" id="newAllergyInput" class="medcard-add-input" placeholder="Другой аллерген...">
            <button class="medcard-add-btn tap-effect" id="addAllergyBtn">+</button>
          </div>
        </div>

        <!-- 2. Хронические заболевания -->
        <div class="medcard-section">
          <div class="medcard-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00B074" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            Хронические заболевания
          </div>

          <!-- Выбранные диагнозы карточками в стиле аптечки -->
          <div class="medcard-items-group" id="medcardChronicList">
            ${(profile.chronic || []).map(c => `
              <div class="medcard-item-card">
                <div class="medcard-item-title">
                  <span class="medcard-item-dot green"></span>
                  <span>${c}</span>
                </div>
                <button class="medcard-item-del-btn tap-effect" data-type="chronic" data-val="${c}" title="Удалить">&times;</button>
              </div>
            `).join('')}
            ${(!profile.chronic || profile.chronic.length === 0) ? `
              <div style="font-size: 12px; color: var(--text-muted); padding: 4px 2px;">Диагнозы не указаны</div>
            ` : ''}
          </div>

          <!-- Кнопка каталога -->
          <button class="medcard-action-btn tap-effect" id="openChronicCatalogBtn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            + Справочник диагнозов
          </button>

          <!-- Быстрые пресеты заболеваний -->
          <div class="medcard-presets-wrap">
            <span class="presets-label">Быстрый выбор:</span>
            <div class="presets-row">
              ${CHRONIC_PRESETS.map(p => {
                const active = (profile.chronic || []).includes(p);
                return `
                  <button class="preset-pill tap-effect ${active ? 'active' : ''}" data-type="chronic" data-val="${p}">
                    ${active ? '✓ ' : '+ '}${p}
                  </button>
                `;
              }).join('')}
            </div>
          </div>

          <div class="medcard-add-row">
            <input type="text" id="newChronicInput" class="medcard-add-input" placeholder="Другой диагноз...">
            <button class="medcard-add-btn tap-effect" id="addChronicBtn">+</button>
          </div>
        </div>

        <!-- 3. Основные физиологические параметры -->
        <div class="medcard-section">
          <div class="medcard-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#4EA8DE" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle></svg>
            Физиологические параметры
          </div>

          <!-- Слайдер возраста -->
          <div class="age-slider-wrap" style="margin-bottom: 10px;">
            <div class="slider-header-row">
              <span class="slider-title">Возраст:</span>
              <span class="slider-badge" id="ageBadge">${this.formatAge(currentAge)}</span>
            </div>
            <input type="range" min="0" max="110" step="1" value="${currentAge}" class="custom-range-slider" id="ageRangeSlider">
          </div>

          <!-- Слайдер веса (палочка с точкой от 1 до 300 кг) -->
          <div class="weight-slider-wrap">
            <div class="slider-header-row">
              <span class="slider-title">Масса тела:</span>
              <span class="slider-badge" id="weightBadge">${currentWeight} кг</span>
            </div>
            <input type="range" min="1" max="300" step="1" value="${currentWeight}" class="custom-range-slider" id="weightRangeSlider">
          </div>
        </div>

        <!-- 4. Особые примечания карточками -->
        <div class="medcard-section">
          <div class="medcard-section-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path></svg>
            Особые примечания
          </div>

          <!-- Список заметок карточками -->
          <div class="medcard-notes-list" id="medcardNotesList">
            ${notesList.map((note, idx) => `
              <div class="medcard-item-card">
                <div class="medcard-item-title">
                  <span class="medcard-item-dot blue"></span>
                  <span>${note}</span>
                </div>
                <button class="medcard-item-del-btn tap-effect" data-note-idx="${idx}" title="Удалить">&times;</button>
              </div>
            `).join('')}
            ${notesList.length === 0 ? `
              <div style="font-size: 12px; color: var(--text-muted); padding: 4px 2px;">Примечания отсутствуют</div>
            ` : ''}
          </div>

          <div class="medcard-add-row">
            <input type="text" id="newNoteInput" class="medcard-add-input" placeholder="Добавить примечание (режим, давление)...">
            <button class="medcard-add-btn tap-effect" id="addNoteBtn">+</button>
          </div>
        </div>
      </div>
    `;

    // 1. Открытие модальных каталогов
    const openAllergyBtn = medcardMount.querySelector('#openAllergyCatalogBtn');
    if (openAllergyBtn) openAllergyBtn.onclick = () => medicalCatalogModal.open('allergies');

    const openChronicBtn = medcardMount.querySelector('#openChronicCatalogBtn');
    if (openChronicBtn) openChronicBtn.onclick = () => medicalCatalogModal.open('chronic');

    // Хелпер тихого обновления с сохранением точного скролла
    const updateProfileAndStay = (updater) => {
      const scrollContainer = this.container.querySelector('.medcard-panel-wrap');
      const scrollPos = scrollContainer ? scrollContainer.scrollTop : 0;
      const curProfile = { ...store.getState().healthProfile };
      updater(curProfile);
      store.setHealthProfile(curProfile, true);
      this.renderMedcard();
      const newScrollContainer = this.container.querySelector('.medcard-panel-wrap');
      if (newScrollContainer) {
        newScrollContainer.scrollTop = scrollPos;
        requestAnimationFrame(() => {
          newScrollContainer.scrollTop = scrollPos;
        });
      }
    };

    // 2. Клики по пресетам аллергий и болезней
    medcardMount.querySelectorAll('.preset-pill[data-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.type;
        const val = btn.dataset.val;
        updateProfileAndStay((cur) => {
          if (type === 'allergy') {
            if (!cur.allergies) cur.allergies = [];
            if (cur.allergies.includes(val)) {
              cur.allergies = cur.allergies.filter(a => a !== val);
            } else {
              cur.allergies.push(val);
            }
          } else if (type === 'chronic') {
            if (!cur.chronic) cur.chronic = [];
            if (cur.chronic.includes(val)) {
              cur.chronic = cur.chronic.filter(c => c !== val);
            } else {
              cur.chronic.push(val);
            }
          }
        });
      });
    });

    // 3. Удаление карточек аллергий и диагнозов
    medcardMount.querySelectorAll('.medcard-item-del-btn[data-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.type;
        const val = btn.dataset.val;
        updateProfileAndStay((cur) => {
          if (type === 'allergy') {
            cur.allergies = (cur.allergies || []).filter(a => a !== val);
          } else if (type === 'chronic') {
            cur.chronic = (cur.chronic || []).filter(c => c !== val);
          }
        });
      });
    });

    // 4. Ползунок возраста
    const ageSlider = medcardMount.querySelector('#ageRangeSlider');
    const ageBadge = medcardMount.querySelector('#ageBadge');
    if (ageSlider && ageBadge) {
      ageSlider.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        ageBadge.textContent = this.formatAge(val);
      });
      ageSlider.addEventListener('change', (e) => {
        const val = Number(e.target.value);
        const curProfile = { ...store.getState().healthProfile, age: val };
        store.setHealthProfile(curProfile, true);
      });
    }

    // 5. Ползунок веса (палочка с точкой от 1 до 300 кг)
    const weightSlider = medcardMount.querySelector('#weightRangeSlider');
    const weightBadge = medcardMount.querySelector('#weightBadge');
    if (weightSlider && weightBadge) {
      weightSlider.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        weightBadge.textContent = `${val} кг`;
      });
      weightSlider.addEventListener('change', (e) => {
        const val = Number(e.target.value);
        const curProfile = { ...store.getState().healthProfile, weight: val };
        store.setHealthProfile(curProfile, true);
      });
    }

    // 6. Удаление заметки
    medcardMount.querySelectorAll('.medcard-item-del-btn[data-note-idx]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.noteIdx);
        updateProfileAndStay((cur) => {
          let list = Array.isArray(cur.notes) ? [...cur.notes] : [];
          list.splice(idx, 1);
          cur.notes = list;
        });
      });
    });

    // 7. Добавление заметки карточкой
    const addNote = () => {
      const inp = medcardMount.querySelector('#newNoteInput');
      const val = inp ? inp.value.trim() : '';
      if (!val) return;
      updateProfileAndStay((cur) => {
        let list = Array.isArray(cur.notes) ? [...cur.notes] : (cur.notes ? [cur.notes] : []);
        if (!list.includes(val)) {
          list.push(val);
        }
        cur.notes = list;
      });
      inp.value = '';
    };

    const addNoteBtn = medcardMount.querySelector('#addNoteBtn');
    if (addNoteBtn) addNoteBtn.addEventListener('click', addNote);
    const newNoteInput = medcardMount.querySelector('#newNoteInput');
    if (newNoteInput) {
      newNoteInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addNote();
        }
      });
    }

    // 8. Добавление своего аллергена
    const addAllergy = () => {
      const inp = medcardMount.querySelector('#newAllergyInput');
      const val = inp ? inp.value.trim() : '';
      if (!val) return;
      updateProfileAndStay((cur) => {
        if (!cur.allergies) cur.allergies = [];
        if (!cur.allergies.includes(val)) cur.allergies.push(val);
      });
      inp.value = '';
    };
    const addAllergyBtn = medcardMount.querySelector('#addAllergyBtn');
    if (addAllergyBtn) addAllergyBtn.addEventListener('click', addAllergy);
    const newAllergyInput = medcardMount.querySelector('#newAllergyInput');
    if (newAllergyInput) {
      newAllergyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addAllergy();
        }
      });
    }

    // 9. Добавление своего диагноза
    const addChronic = () => {
      const inp = medcardMount.querySelector('#newChronicInput');
      const val = inp ? inp.value.trim() : '';
      if (!val) return;
      updateProfileAndStay((cur) => {
        if (!cur.chronic) cur.chronic = [];
        if (!cur.chronic.includes(val)) cur.chronic.push(val);
      });
      inp.value = '';
    };
    const addChronicBtn = medcardMount.querySelector('#addChronicBtn');
    if (addChronicBtn) addChronicBtn.addEventListener('click', addChronic);
    const newChronicInput = medcardMount.querySelector('#newChronicInput');
    if (newChronicInput) {
      newChronicInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addChronic();
        }
      });
    }
  }

  render() {
    this.container.innerHTML = `
      <!-- Сегментированная шапка правой панели: чистые табы [ Моя аптечка | Медкарта ] -->
      <div class="right-panel-header">
        <div class="right-tab-switcher">
          <button class="right-tab-btn active" id="rightTabKitBtn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <rect x="3" y="6" width="18" height="15" rx="3"></rect>
              <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"></path>
            </svg>
            <span>Моя аптечка</span>
          </button>

          <button class="right-tab-btn" id="rightTabMedcardBtn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            <span>Медкарта</span>
          </button>
        </div>
      </div>

      <!-- Контент вкладки «Моя аптечка» -->
      <div id="kitTabContent" class="kit-tab-body">
        <!-- Отдельная строка количества лекарств в аптечке -->
        <div class="kit-summary-row">
          <div class="kit-summary-text">
            <span>В наличии:</span>
            <strong id="kitSummaryCount">0 препаратов</strong>
          </div>
        </div>

        <!-- Отдельная кнопка добавления своего лекарства над поиском -->
        <div class="kit-add-action-wrap">
          <button class="kit-add-custom-btn tap-effect" id="openAddMedicineBtn" title="Добавить препарат, которого нет в каталоге">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>Добавить препарат в аптечку</span>
          </button>
        </div>

        <div class="kit-search-wrap">
          <input type="text" id="kitSearchInput" class="kit-search-field" placeholder="Поиск в аптечке...">
        </div>

        <div class="kit-tags-wrap" id="kitTagsContainer">
          ${this.allTags.map(tag => `
            <button class="kit-tag-chip tap-effect" data-tag="${tag}">${tag}</button>
          `).join('')}
        </div>

        <div class="kit-items-list" id="kitItemsList"></div>
      </div>

      <!-- Контент вкладки «Медкарта» -->
      <div id="medcardTabContent" class="kit-tab-body" style="display: none;"></div>
    `;

    this.renderList();
  }
}
