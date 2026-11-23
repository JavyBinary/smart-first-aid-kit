/**
 * AccountProfileModal: Управление учетной записью пользователя (КТ1)
 * Редактирование имени, email и смена пароля
 */

import { store } from '../state/store.js';

export class AccountProfileModal {
  constructor(overlayElement) {
    this.overlay = overlayElement;
  }

  open() {
    const user = store.getState().user || { name: 'Лука', email: 'luka@medai.ru' };

    this.overlay.innerHTML = `
      <div class="modal-card" style="max-width: 440px;">
        <div class="modal-header">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="user-avatar-circle" style="width: 40px; height: 40px; font-size: 16px;">
              ${(user.name || 'Л')[0].toUpperCase()}
            </div>
            <div>
              <div style="font-size: 16px; font-weight: 700; color: var(--brand-dark);">Профиль аккаунта</div>
              <div style="font-size: 12px; color: var(--text-muted);">Личные данные и безопасность</div>
            </div>
          </div>
          <button class="modal-close-btn" id="accountModalCloseBtn">&times;</button>
        </div>

        <form id="accountProfileForm" style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label class="modal-label">Ваше имя</label>
            <input type="text" id="accUserName" class="modal-input" required value="${user.name || 'Лука'}" placeholder="Лука">
          </div>

          <div>
            <label class="modal-label">Электронная почта</label>
            <input type="email" id="accUserEmail" class="modal-input" required value="${user.email || 'luka@medai.ru'}" placeholder="luka@medai.ru">
          </div>

          <div>
            <label class="modal-label">Новый пароль (оставьте пустым, если не меняете)</label>
            <input type="password" id="accUserPassword" class="modal-input" placeholder="••••••••">
          </div>

          <div id="accountModalAlert" style="display: none; padding: 10px 14px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; background: #E8F7F0; color: #00875A;">
            Данные профиля успешно обновлены
          </div>

          ${user.role === 'admin' ? `
            <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
              <div style="font-size: 12px; color: var(--text-muted);">Управление сервисом:</div>
              <a href="./admin.html" class="modal-btn-cancel tap-effect" style="text-decoration: none; font-size: 12px; padding: 6px 14px; display: inline-flex; align-items: center; gap: 6px;">
                <span>🛡️</span>
                <span>Панель админа</span>
              </a>
            </div>
          ` : ''}

          <div style="display: flex; gap: 10px; margin-top: 10px;">
            <button type="button" class="modal-btn-cancel tap-effect" id="accountModalCancelBtn" style="flex: 1;">Отмена</button>
            <button type="submit" class="modal-btn-save tap-effect" style="flex: 1.4;">Сохранить изменения</button>
          </div>
        </form>
      </div>
    `;

    this.overlay.style.display = 'flex';

    this.overlay.querySelector('#accountModalCloseBtn').onclick = () => this.close();
    this.overlay.querySelector('#accountModalCancelBtn').onclick = () => this.close();

    const form = this.overlay.querySelector('#accountProfileForm');
    form.onsubmit = (e) => {
      e.preventDefault();
      const newName = this.overlay.querySelector('#accUserName').value.trim();
      const newEmail = this.overlay.querySelector('#accUserEmail').value.trim();

      if (newName) {
        store.setUser({ name: newName, email: newEmail });

        // Обновляем плашку в UI
        const nameEl = document.querySelector('.user-meta-name');
        if (nameEl) nameEl.textContent = newName;
        const avatarEl = document.querySelector('.user-avatar-circle');
        if (avatarEl) avatarEl.textContent = newName[0].toUpperCase();

        const alertBox = this.overlay.querySelector('#accountModalAlert');
        if (alertBox) alertBox.style.display = 'block';

        setTimeout(() => this.close(), 700);
      }
    };
  }

  close() {
    this.overlay.style.display = 'none';
  }
}
