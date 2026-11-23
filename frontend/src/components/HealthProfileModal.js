/**
 * Modals: Медкарта (Health Profile) и добавление редкого препарата
 */

import { store } from '../state/store.js';
import { kitApi } from '../api/kit.api.js';

export const ALLERGIES_LIST = [
  'Пенициллины',
  'НПВП (Аспирин/Ибупрофен)',
  'Лактоза',
  'Сульфаниламиды',
  'Местные анестетики',
  'Йодсодержащие препараты'
];

export const CHRONIC_LIST = [
  'Язвенная болезнь ЖКТ',
  'Бронхиальная астма',
  'Артериальная гипертензия',
  'Сахарный диабет',
  'Хроническая почечная недостаточность',
  'Гастрит'
];

export class HealthProfileModal {
  constructor(overlayElement) {
    this.overlay = overlayElement;
  }

  open() {
    const state = store.getState();
    const currentAllergies = state.healthProfile.allergies || [];
    const currentChronic = state.healthProfile.chronic || [];

    this.overlay.innerHTML = `
      <div class="modal-card-box spring-transition" style="max-width: 540px; background: #fff; border-radius: var(--radius-xl); padding: 28px; box-shadow: var(--shadow-lg); width: 90%;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 20px; font-weight: 700; color: var(--brand-dark);">Профиль здоровья и медкарта</h3>
            <p style="font-size: 13px; color: var(--text-muted); margin-top: 2px;">Учитывается ассистентом при проверке противопоказаний</p>
          </div>
          <button id="closeHealthModal" style="background: none; border: none; font-size: 22px; cursor: pointer; color: var(--text-muted);">&times;</button>
        </div>

        <div style="margin-bottom: 20px;">
          <label style="font-size: 13px; font-weight: 700; color: var(--text-main); text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 8px;">
            ⚠️ Аллергии и непереносимости:
          </label>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            ${ALLERGIES_LIST.map(a => `
              <label class="tag-toggle-chip ${currentAllergies.includes(a) ? 'checked' : ''}" style="
                border: 1px solid var(--border); padding: 7px 13px; border-radius: var(--radius-full); font-size: 12.5px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; user-select: none;
              ">
                <input type="checkbox" name="allergies" value="${a}" ${currentAllergies.includes(a) ? 'checked' : ''} style="display: none;">
                <span>${a}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <div style="margin-bottom: 24px;">
          <label style="font-size: 13px; font-weight: 700; color: var(--text-main); text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 8px;">
            🩺 Хронические заболевания:
          </label>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            ${CHRONIC_LIST.map(c => `
              <label class="tag-toggle-chip ${currentChronic.includes(c) ? 'checked' : ''}" style="
                border: 1px solid var(--border); padding: 7px 13px; border-radius: var(--radius-full); font-size: 12.5px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; user-select: none;
              ">
                <input type="checkbox" name="chronic" value="${c}" ${currentChronic.includes(c) ? 'checked' : ''} style="display: none;">
                <span>${c}</span>
              </label>
            `).join('')}
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button id="cancelHealthModal" style="padding: 10px 18px; border: 1px solid var(--border); background: #fff; border-radius: var(--radius-md); font-weight: 600; cursor: pointer;">Отмена</button>
          <button id="saveHealthModal" style="padding: 10px 22px; border: none; background: var(--brand); color: #fff; border-radius: var(--radius-md); font-weight: 600; cursor: pointer; box-shadow: var(--shadow-sm);">Сохранить</button>
        </div>
      </div>
    `;

    this.overlay.style.display = 'flex';

    // Интерактивное переключение чипсов
    this.overlay.querySelectorAll('.tag-toggle-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const checkbox = chip.querySelector('input');
        checkbox.checked = !checkbox.checked;
        chip.style.background = checkbox.checked ? 'var(--brand-light)' : '#fff';
        chip.style.borderColor = checkbox.checked ? 'var(--brand)' : 'var(--border)';
        chip.style.color = checkbox.checked ? 'var(--brand-hover)' : 'inherit';
      });
    });

    const close = () => { this.overlay.style.display = 'none'; };
    this.overlay.querySelector('#closeHealthModal').onclick = close;
    this.overlay.querySelector('#cancelHealthModal').onclick = close;
    this.overlay.onclick = (e) => { if (e.target === this.overlay) close(); };

    this.overlay.querySelector('#saveHealthModal').onclick = () => {
      const selectedAllergies = Array.from(this.overlay.querySelectorAll('input[name="allergies"]:checked')).map(i => i.value);
      const selectedChronic = Array.from(this.overlay.querySelectorAll('input[name="chronic"]:checked')).map(i => i.value);

      store.setHealthProfile({
        allergies: selectedAllergies,
        chronic: selectedChronic
      });
      close();
    };
  }
}

export class CustomMedicineModal {
  constructor(overlayElement) {
    this.overlay = overlayElement;
  }

  open() {
    this.overlay.innerHTML = `
      <div class="modal-card-box" style="max-width: 480px; background: #fff; border-radius: var(--radius-xl); padding: 26px; box-shadow: var(--shadow-lg); width: 90%;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
          <h3 style="font-size: 19px; font-weight: 700; color: var(--brand-dark);">Добавить свой препарат</h3>
          <button id="closeCustomModal" style="background: none; border: none; font-size: 22px; cursor: pointer; color: var(--text-muted);">&times;</button>
        </div>

        <form id="customMedForm">
          <div style="margin-bottom: 14px;">
            <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Название препарата *</label>
            <input type="text" id="custName" required placeholder="Например, Амоксиклав" style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-md); font-size: 14px;">
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
            <div>
              <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Дозировка</label>
              <input type="text" id="custDosage" placeholder="500 мг" style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-md); font-size: 14px;">
            </div>
            <div>
              <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Форма выпуска</label>
              <select id="custForm" style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-md); font-size: 14px; background: #fff;">
                <option value="таблетки">Таблетки</option>
                <option value="капсулы">Капсулы</option>
                <option value="спрей">Спрей</option>
                <option value="порошок">Порошок</option>
                <option value="мазь">Мазь</option>
                <option value="капли">Капли</option>
              </select>
            </div>
          </div>

          <div style="margin-bottom: 18px;">
            <label style="display: block; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Симптомы / Теги (через запятую)</label>
            <input type="text" id="custTags" placeholder="боль, воспаление, антибиотик" style="width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-md); font-size: 14px;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" id="cancelCustomModal" style="padding: 10px 18px; border: 1px solid var(--border); background: #fff; border-radius: var(--radius-md); font-weight: 600; cursor: pointer;">Отмена</button>
            <button type="submit" style="padding: 10px 22px; border: none; background: var(--brand); color: #fff; border-radius: var(--radius-md); font-weight: 600; cursor: pointer; box-shadow: var(--shadow-sm);">Добавить</button>
          </div>
        </form>
      </div>
    `;

    this.overlay.style.display = 'flex';

    const close = () => { this.overlay.style.display = 'none'; };
    this.overlay.querySelector('#closeCustomModal').onclick = close;
    this.overlay.querySelector('#cancelCustomModal').onclick = close;
    this.overlay.onclick = (e) => { if (e.target === this.overlay) close(); };

    this.overlay.querySelector('#customMedForm').onsubmit = async (e) => {
      e.preventDefault();
      const name = this.overlay.querySelector('#custName').value.trim();
      const dosage = this.overlay.querySelector('#custDosage').value.trim() || 'стандартная';
      const form = this.overlay.querySelector('#custForm').value;
      const tagsRaw = this.overlay.querySelector('#custTags').value;
      const tags = tagsRaw.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);

      const newItem = {
        id: `kit_${Date.now()}`,
        name,
        dosage,
        form,
        category: 'Пользовательские',
        tags: tags.length ? tags : ['общее'],
        expiry: '2028-01-01'
      };

      await kitApi.addItem(newItem);
      store.addKitItem(newItem);
      close();
    };
  }
}
