/**
 * AddMedicineModal: Модальное окно для добавления пользовательского препарата в домашнюю аптечку
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';

export class AddMedicineModal {
  constructor() {
    this.overlay = null;
    this.isPrescription = false;
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
              <div class="modal-title" style="font-size: 16px; font-weight: 700; color: var(--brand-dark);">Добавить свой препарат</div>
              <div class="modal-subtitle" style="font-size: 12px; color: var(--text-muted); margin-top: 1px;">Лекарство появится в вашей домашней аптечке</div>
            </div>
          </div>
          <button class="modal-close-btn" id="closeAddMedModalBtn">&times;</button>
        </div>

        <form id="addCustomMedForm" style="display: flex; flex-direction: column; gap: 14px; margin-top: 6px;">
          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Название препарата *</label>
            <input type="text" id="customMedNameInput" class="modal-input" placeholder="Например: Ибупрофен, Нимесил, Дюфастон..." required style="width: 100%; box-sizing: border-box;">
          </div>

          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Дозировка и форма выпуска</label>
            <input type="text" id="customMedDosageInput" class="modal-input" placeholder="Например: таблетки 200 мг · 20 шт. или спрей 50 мл" style="width: 100%; box-sizing: border-box;">
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Категория</label>
              <select id="customMedCategorySelect" class="modal-input" style="width: 100%; box-sizing: border-box; background: #FFFFFF; cursor: pointer;">
                <option value="Обезболивающие">Обезболивающие</option>
                <option value="Простуда и грипп">Простуда и грипп</option>
                <option value="ЖКТ и пищеварение">ЖКТ и пищеварение</option>
                <option value="Спазмолитики">Спазмолитики</option>
                <option value="Аллергия">Аллергия</option>
                <option value="Антибиотики">Антибиотики</option>
                <option value="Антисептики">Антисептики</option>
                <option value="Другое">Другое</option>
              </select>
            </div>

            <div>
              <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Срок годности</label>
              <input type="date" id="customMedExpiryInput" class="modal-input" value="2027-12-31" style="width: 100%; box-sizing: border-box; background: #FFFFFF; cursor: pointer;">
            </div>
          </div>

          <div>
            <label class="modal-label" style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Отпуск из аптек</label>
            <div class="rx-toggle-row">
              <button type="button" class="rx-toggle-btn active tap-effect" data-rx="otc" id="rxToggleOtcBtn">Без рецепта</button>
              <button type="button" class="rx-toggle-btn tap-effect" data-rx="rx" id="rxToggleRxBtn">По рецепту</button>
            </div>
          </div>

          <div style="display: flex; gap: 10px; margin-top: 10px; justify-content: flex-end;">
            <button type="button" class="modal-btn-cancel tap-effect" id="cancelAddMedBtn" style="padding: 10px 18px;">Отмена</button>
            <button type="submit" class="btn-brand-primary tap-effect" style="padding: 10px 22px;">Добавить в аптечку</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(this.overlay);

    // Закрытие по крестику и отмене
    this.overlay.querySelector('#closeAddMedModalBtn').onclick = () => this.close();
    this.overlay.querySelector('#cancelAddMedBtn').onclick = () => this.close();

    // Закрытие по клику вне карточки
    this.overlay.onclick = (e) => {
      if (e.target === this.overlay) this.close();
    };

    // Переключатель рецепта
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

    // Обработка отправки формы
    const form = this.overlay.querySelector('#addCustomMedForm');
    form.onsubmit = async (e) => {
      e.preventDefault();
      const name = this.overlay.querySelector('#customMedNameInput').value.trim();
      if (!name) return;

      const dosage = this.overlay.querySelector('#customMedDosageInput').value.trim();
      const category = this.overlay.querySelector('#customMedCategorySelect').value;
      const expiry = this.overlay.querySelector('#customMedExpiryInput').value || '2027-12-31';

      let formType = 'таблетки';
      const lowDosage = dosage.toLowerCase();
      if (lowDosage.includes('капс')) formType = 'капсулы';
      else if (lowDosage.includes('спрей')) formType = 'спрей';
      else if (lowDosage.includes('мазь') || lowDosage.includes('крем')) formType = 'мазь';
      else if (lowDosage.includes('порошок')) formType = 'порошок';
      else if (lowDosage.includes('раствор') || lowDosage.includes('капли')) formType = 'раствор';

      const newItem = {
        id: `custom_${Date.now()}`,
        name,
        dosage: dosage || 'по инструкции',
        form: formType,
        category,
        expiry,
        is_prescription: this.isPrescription,
        isPrescription: this.isPrescription,
        tags: [category.toLowerCase(), name.toLowerCase()]
      };

      store.addKitItem(newItem);
      kitApi.addItem(newItem);

      this.close();
    };
  }

  open() {
    if (!this.overlay) this.init();
    const form = this.overlay.querySelector('#addCustomMedForm');
    if (form) form.reset();

    this.isPrescription = false;
    const otcBtn = this.overlay.querySelector('#rxToggleOtcBtn');
    const rxBtn = this.overlay.querySelector('#rxToggleRxBtn');
    if (otcBtn) otcBtn.classList.add('active');
    if (rxBtn) rxBtn.classList.remove('active');

    this.overlay.style.display = 'flex';
    const nameInput = this.overlay.querySelector('#customMedNameInput');
    if (nameInput) {
      setTimeout(() => nameInput.focus(), 80);
    }
  }

  close() {
    if (this.overlay) {
      this.overlay.style.display = 'none';
    }
  }
}

export const addMedicineModal = new AddMedicineModal();
