/**
 * AddMedicineModal: Модальное окно добавления и редактирования препарата в домашней аптечке
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';

const CATEGORY_OPTIONS = [
  'Обезболивающие',
  'Простуда и грипп',
  'Горло и кашель',
  'Нос и глаза',
  'ЖКТ и пищеварение',
  'Спазмолитики',
  'Аллергия',
  'Антибиотики',
  'Антисептики и кожа',
  'Сердце и давление',
  'Другое',
];

const FORM_OPTIONS = [
  'таблетки',
  'капсулы',
  'порошок',
  'спрей',
  'капли',
  'сироп',
  'мазь',
  'раствор',
  'пастилки',
];

function defaultFutureExpiry() {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 2);
  return d.toISOString().slice(0, 10);
}

export class AddMedicineModal {
  constructor() {
    this.overlay = null;
    this.isPrescription = false;
    this.editingItemId = null;
    this.init();
  }

  init() {
    this.overlay = document.createElement('div');
    this.overlay.className = 'custom-med-modal-overlay';
    this.overlay.style.display = 'none';

    this.overlay.innerHTML = `
      <div class="custom-med-modal-card">
        <div class="modal-header">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="custom-med-icon-box" style="display: flex; align-items: center; justify-content: center;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
            </div>
            <div>
              <div class="modal-title" id="customMedModalTitle" style="font-size: 16px; font-weight: 700; color: var(--brand-dark);">Добавить свой препарат</div>
              <div class="modal-subtitle" id="customMedModalSubtitle" style="font-size: 12px; color: var(--text-muted); margin-top: 1px;">Лекарство появится в вашей домашней аптечке</div>
            </div>
          </div>
          <button class="modal-close-btn" id="closeAddMedModalBtn">&times;</button>
        </div>

        <form id="addCustomMedForm" style="display: flex; flex-direction: column; gap: 12px; margin-top: 6px;">
          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Название препарата *</label>
            <input type="text" id="customMedNameInput" class="modal-input" placeholder="Например: Ибупрофен, Парацетамол, Нимесил..." required style="width: 100%; box-sizing: border-box;">
          </div>

          <div style="display: grid; grid-template-columns: 1.4fr 1fr; gap: 10px;">
            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Дозировка</label>
              <input type="text" id="customMedDosageInput" class="modal-input" placeholder="Например: 500 мг · 20 шт." style="width: 100%; box-sizing: border-box;">
            </div>
            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Форма выпуска</label>
              <select id="customMedFormSelect" class="modal-input" style="width: 100%; box-sizing: border-box; background: #FFFFFF; cursor: pointer;">
                ${FORM_OPTIONS.map(f => `<option value="${f}">${f}</option>`).join('')}
              </select>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1.2fr 1fr 0.7fr; gap: 10px;">
            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Категория</label>
              <select id="customMedCategorySelect" class="modal-input" style="width: 100%; box-sizing: border-box; background: #FFFFFF; cursor: pointer;">
                ${CATEGORY_OPTIONS.map(c => `<option value="${c}">${c}</option>`).join('')}
              </select>
            </div>

            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Срок годности</label>
              <input type="date" id="customMedExpiryInput" class="modal-input" value="${defaultFutureExpiry()}" style="width: 100%; box-sizing: border-box; background: #FFFFFF; cursor: pointer;">
            </div>

            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Упаковок</label>
              <input type="number" id="customMedQuantityInput" class="modal-input" min="1" max="99" value="1" style="width: 100%; box-sizing: border-box; background: #FFFFFF;">
            </div>
          </div>

          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Симптомы / теги (через запятую)</label>
            <input type="text" id="customMedTagsInput" class="modal-input" placeholder="жар, боль, головная боль" style="width: 100%; box-sizing: border-box;">
          </div>

          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 5px;">Отпуск из аптек</label>
            <div class="rx-toggle-row">
              <button type="button" class="rx-toggle-btn active tap-effect" data-rx="otc" id="rxToggleOtcBtn">Без рецепта</button>
              <button type="button" class="rx-toggle-btn tap-effect" data-rx="rx" id="rxToggleRxBtn">По рецепту</button>
            </div>
          </div>

          <div style="display: flex; gap: 10px; margin-top: 8px; justify-content: flex-end;">
            <button type="button" class="modal-btn-cancel tap-effect" id="cancelAddMedBtn" style="padding: 10px 18px;">Отмена</button>
            <button type="submit" id="customMedSubmitBtn" class="btn-brand-primary tap-effect" style="padding: 10px 22px;">Добавить в аптечку</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(this.overlay);

    this.overlay.querySelector('#closeAddMedModalBtn').onclick = () => this.close();
    this.overlay.querySelector('#cancelAddMedBtn').onclick = () => this.close();
    this.overlay.onclick = (e) => {
      if (e.target === this.overlay) this.close();
    };

    const otcBtn = this.overlay.querySelector('#rxToggleOtcBtn');
    const rxBtn = this.overlay.querySelector('#rxToggleRxBtn');

    otcBtn.onclick = () => {
      this.isPrescription = false;
      otcBtn.classList.add('active');
      rxBtn.classList.remove('active');
    };

    rxBtn.onclick = () => {
      this.isPrescription = true;
      rxBtn.classList.add('active');
      otcBtn.classList.remove('active');
    };

    const form = this.overlay.querySelector('#addCustomMedForm');
    form.onsubmit = async (e) => {
      e.preventDefault();
      const name = this.overlay.querySelector('#customMedNameInput').value.trim();
      if (!name) return;

      const dosage = this.overlay.querySelector('#customMedDosageInput').value.trim() || 'по инструкции';
      const formType = this.overlay.querySelector('#customMedFormSelect').value || 'таблетки';
      const category = this.overlay.querySelector('#customMedCategorySelect').value || 'Другое';
      const expiry = this.overlay.querySelector('#customMedExpiryInput').value || defaultFutureExpiry();
      const quantity = Math.max(1, Number.parseInt(this.overlay.querySelector('#customMedQuantityInput').value, 10) || 1);
      const tagsRaw = this.overlay.querySelector('#customMedTagsInput').value || '';
      const parsedTags = tagsRaw.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
      const tags = parsedTags.length ? parsedTags : [category.toLowerCase(), name.toLowerCase()];
      const status = this.isPrescription ? 'rx' : 'otc';

      if (this.editingItemId) {
        const updates = {
          name,
          dosage,
          form: formType,
          category,
          expiry,
          quantity,
          status,
          tags,
        };
        const res = await kitApi.updateItem(this.editingItemId, updates);
        const merged = res && res.id ? res : { id: this.editingItemId, ...updates };
        store.updateKitItem(merged);
        this.close();
        return;
      }

      const newItem = {
        id: `custom_${Date.now()}`,
        name,
        dosage,
        form: formType,
        category,
        expiry,
        quantity,
        status,
        tags,
      };

      const saved = await kitApi.addItem(newItem);
      const itemToStore = saved && saved.id ? saved : newItem;
      store.addKitItem(itemToStore);
      this.close();
    };
  }

  _setRxToggle(isRx) {
    this.isPrescription = Boolean(isRx);
    const otcBtn = this.overlay.querySelector('#rxToggleOtcBtn');
    const rxBtn = this.overlay.querySelector('#rxToggleRxBtn');
    if (otcBtn) otcBtn.classList.toggle('active', !this.isPrescription);
    if (rxBtn) rxBtn.classList.toggle('active', this.isPrescription);
  }

  open() {
    if (!this.overlay) this.init();
    this.editingItemId = null;
    const form = this.overlay.querySelector('#addCustomMedForm');
    if (form) form.reset();

    this.overlay.querySelector('#customMedModalTitle').textContent = 'Добавить свой препарат';
    this.overlay.querySelector('#customMedModalSubtitle').textContent = 'Лекарство появится в вашей домашней аптечке';
    this.overlay.querySelector('#customMedSubmitBtn').textContent = 'Добавить в аптечку';
    this.overlay.querySelector('#customMedExpiryInput').value = defaultFutureExpiry();
    this.overlay.querySelector('#customMedQuantityInput').value = '1';
    this._setRxToggle(false);

    this.overlay.style.display = 'flex';
    const nameInput = this.overlay.querySelector('#customMedNameInput');
    if (nameInput) setTimeout(() => nameInput.focus(), 80);
  }

  openEdit(item) {
    if (!item) return;
    if (!this.overlay) this.init();
    this.editingItemId = item.id;

    this.overlay.querySelector('#customMedModalTitle').textContent = 'Редактировать препарат';
    this.overlay.querySelector('#customMedModalSubtitle').textContent = 'Измените дозировку, срок годности, количество или категорию';
    this.overlay.querySelector('#customMedSubmitBtn').textContent = 'Сохранить изменения';

    this.overlay.querySelector('#customMedNameInput').value = item.name || '';
    this.overlay.querySelector('#customMedDosageInput').value = item.dosage || '';
    this.overlay.querySelector('#customMedExpiryInput').value = item.expiry || defaultFutureExpiry();
    this.overlay.querySelector('#customMedQuantityInput').value = String(item.quantity || 1);
    this.overlay.querySelector('#customMedTagsInput').value = Array.isArray(item.tags) ? item.tags.join(', ') : '';

    const formSel = this.overlay.querySelector('#customMedFormSelect');
    if (formSel) {
      formSel.value = FORM_OPTIONS.includes(item.form) ? item.form : 'таблетки';
    }
    const catSel = this.overlay.querySelector('#customMedCategorySelect');
    if (catSel) {
      catSel.value = CATEGORY_OPTIONS.includes(item.category) ? item.category : 'Другое';
    }

    const isRx = item.status === 'rx' || item.isPrescription || item.is_prescription;
    this._setRxToggle(isRx);

    this.overlay.style.display = 'flex';
    const nameInput = this.overlay.querySelector('#customMedNameInput');
    if (nameInput) setTimeout(() => nameInput.focus(), 80);
  }

  close() {
    if (this.overlay) {
      this.overlay.style.display = 'none';
    }
    this.editingItemId = null;
  }
}

export const addMedicineModal = new AddMedicineModal();
