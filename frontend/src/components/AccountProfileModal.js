/**
 * AccountProfileModal: Управление учетной записью пользователя
 * Редактирование имени, email, выбор цвета аватара/загрузка фото, смена пароля и выход.
 * Для гостевого режима отображает информационную карточку без редактирования.
 */

import { store, VOICE_OPTIONS } from '../state/store.js';
import { authApi } from '../api/auth.api.js';

export class AccountProfileModal {
  constructor(overlayElement) {
    this.overlay = overlayElement;
    this.selectedAvatar = '';
  }

  open() {
    const user = store.getState().user || { name: 'Гость', email: '', role: 'guest', avatar: '' };
    const isGuest = user.role === 'guest' || !user.email;

    // 1. Отображение карточки для гостя (без формы редактирования)
    if (isGuest) {
      this.overlay.innerHTML = `
        <div class="modal-card" style="max-width: 440px;">
          <div class="modal-header">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div class="user-avatar-circle" style="width: 48px; height: 48px; font-size: 20px; border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; background: #F1F5F9; color: var(--text-secondary);">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div>
                <div style="font-size: 16px; font-weight: 700; color: var(--brand-dark);">Гостевой профиль</div>
                <div style="font-size: 12px; color: var(--text-muted);">Ознакомительный режим работы</div>
              </div>
            </div>
            <button class="modal-close-btn" id="accountModalCloseBtn">&times;</button>
          </div>

          <div style="padding: 16px 0 8px; display: flex; flex-direction: column; gap: 14px;">
            <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px; font-size: 13.5px; line-height: 1.5; color: var(--text-secondary);">
              Вы используете сервис в ознакомительном режиме без постоянной учетной записи. Вся история консультаций и домашняя аптечка сохраняются локально только в этом браузере.
            </div>

            <div style="background: rgba(0, 176, 116, 0.08); border: 1px solid rgba(0, 176, 116, 0.2); border-radius: var(--radius-md); padding: 12px; font-size: 13px; color: var(--brand-dark);">
              Войдите или создайте аккаунт, чтобы сохранять историю диалогов, настраивать медкарту и иметь доступ к аптечке с любых устройств.
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 8px;">
              <a href="login.html" class="modal-btn-save tap-effect" style="text-decoration: none; text-align: center; padding: 12px 18px; font-size: 14.5px; display: block; box-sizing: border-box; width: 100%;">
                Войти или зарегистрироваться
              </a>
              <button type="button" class="modal-btn-cancel tap-effect" id="guestModalContinueBtn" style="padding: 11px; font-size: 13.5px; width: 100%;">
                Продолжить как гость
              </button>
              <button type="button" id="guestModalExitBtn" class="tap-effect" style="background: none; border: none; color: var(--danger, #DC2626); font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 6px 0; margin-top: 4px; width: 100%;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                <span>Завершить гостевой сеанс</span>
              </button>
            </div>
          </div>
        </div>
      `;

      this.overlay.style.display = 'flex';
      this.overlay.querySelector('#accountModalCloseBtn').onclick = () => this.close();
      this.overlay.querySelector('#guestModalContinueBtn').onclick = () => this.close();
      this.overlay.querySelector('#guestModalExitBtn').onclick = () => store.logout();
      return;
    }

    // 2. Отображение формы редактирования для авторизованного пользователя
    this.selectedAvatar = user.avatar || '';

    const avatarHtml = this.selectedAvatar ?
      `<img id="accAvatarPreview" src="${this.selectedAvatar}" alt="Аватар" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid var(--brand);">` :
      `<div id="accAvatarPreview" class="user-avatar-circle" style="width: 48px; height: 48px; font-size: 18px; border: 2px solid var(--brand);">
        ${(user.name || 'П')[0].toUpperCase()}
      </div>`;

    this.overlay.innerHTML = `
      <div class="modal-card" style="max-width: 460px;">
        <div class="modal-header">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div id="accAvatarPreviewWrap">
              ${avatarHtml}
            </div>
            <div>
              <div style="font-size: 16px; font-weight: 700; color: var(--brand-dark);">Профиль аккаунта</div>
              <div style="font-size: 12px; color: var(--text-muted);">Личные данные и безопасность</div>
            </div>
          </div>
          <button class="modal-close-btn" id="accountModalCloseBtn">&times;</button>
        </div>

        <form id="accountProfileForm" style="display: flex; flex-direction: column; gap: 14px;">
          <!-- Выбор стиля аватара -->
          <div>
            <label class="modal-label">Аватар профиля</label>
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px;">
              <button type="button" class="avatar-color-btn tap-effect" data-bg="#E8F0FE" data-color="#1A73E8" title="Синий" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px var(--border); background: #E8F0FE; cursor: pointer;"></button>
              <button type="button" class="avatar-color-btn tap-effect" data-bg="#E8F7F0" data-color="#00A86B" title="Изумрудный" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px var(--border); background: #E8F7F0; cursor: pointer;"></button>
              <button type="button" class="avatar-color-btn tap-effect" data-bg="#F3E8FF" data-color="#7E22CE" title="Фиолетовый" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px var(--border); background: #F3E8FF; cursor: pointer;"></button>
              <button type="button" class="avatar-color-btn tap-effect" data-bg="#F1F5F9" data-color="#475569" title="Серый" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px var(--border); background: #F1F5F9; cursor: pointer;"></button>
              <button type="button" class="avatar-color-btn tap-effect" data-bg="#FEF3C7" data-color="#D97706" title="Янтарный" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px var(--border); background: #FEF3C7; cursor: pointer;"></button>
              
              <label for="accAvatarUpload" class="tap-effect" style="font-size: 12.5px; font-weight: 600; padding: 6px 14px; border-radius: var(--radius-sm); border: 1px dashed var(--brand); color: var(--brand); cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                <span>Загрузить фото</span>
              </label>
              <input type="file" id="accAvatarUpload" accept="image/*" style="display: none;">
            </div>
          </div>

          <div>
            <label class="modal-label">Ваше имя</label>
            <input type="text" id="accUserName" class="modal-input" required value="${user.name || 'Пользователь'}" placeholder="Ваше имя">
          </div>

          <div>
            <label class="modal-label">Электронная почта</label>
            <input type="email" id="accUserEmail" class="modal-input" required value="${user.email || ''}" placeholder="name@example.com">
          </div>

          <div>
            <label class="modal-label">Голос озвучивания (TTS)</label>
            <select id="accVoiceSelect" class="modal-input">
              ${VOICE_OPTIONS.map(v => `
                <option value="${v.id}" ${store.getState().voice === v.id ? 'selected' : ''}>${v.label}</option>
              `).join('')}
            </select>
          </div>

          <div>
            <label class="modal-label">Текущий пароль (для смены пароля)</label>
            <input type="password" id="accOldPassword" class="modal-input" placeholder="Оставьте пустым, если пароль не меняется">
          </div>

          <div>
            <label class="modal-label">Новый пароль (минимум 8 символов)</label>
            <input type="password" id="accUserPassword" class="modal-input" placeholder="Новый пароль">
          </div>

          <div id="accountModalAlert" style="display: none; padding: 10px 14px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; background: #E8F7F0; color: #00875A;">
            Данные профиля успешно обновлены
          </div>

          ${(user.role === 'admin' || user.role === 'superadmin') ? `
            <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
              <div style="font-size: 12px; color: var(--text-muted);">
                Роль: <strong style="color: var(--brand-dark);">${user.role === 'superadmin' ? 'Суперадминистратор' : 'Администратор'}</strong>
              </div>
              <a href="./admin.html" class="modal-btn-cancel tap-effect" style="text-decoration: none; font-size: 12px; padding: 6px 14px; display: inline-flex; align-items: center; gap: 6px;">
                <span>Панель админа</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </a>
            </div>
          ` : ''}

          <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
            <button type="button" id="profileLogoutBtn" class="tap-effect" style="background: none; border: none; color: var(--danger, #DC2626); font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; padding: 6px 0;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
              <span>Выйти из аккаунта</span>
            </button>
          </div>

          <div style="display: flex; gap: 10px; margin-top: 6px;">
            <button type="button" class="modal-btn-cancel tap-effect" id="accountModalCancelBtn" style="flex: 1;">Отмена</button>
            <button type="submit" class="modal-btn-save tap-effect" style="flex: 1.4;">Сохранить изменения</button>
          </div>
        </form>
      </div>
    `;

    this.overlay.style.display = 'flex';

    this.overlay.querySelector('#accountModalCloseBtn').onclick = () => this.close();
    this.overlay.querySelector('#accountModalCancelBtn').onclick = () => this.close();

    // Кнопка выхода из профиля
    const logoutBtn = this.overlay.querySelector('#profileLogoutBtn');
    if (logoutBtn) {
      logoutBtn.onclick = () => store.logout();
    }

    // Выбор палитры для аватара
    const previewWrap = this.overlay.querySelector('#accAvatarPreviewWrap');
    this.overlay.querySelectorAll('.avatar-color-btn').forEach(btn => {
      btn.onclick = () => {
        const bg = btn.dataset.bg;
        const color = btn.dataset.color;
        const currentName = this.overlay.querySelector('#accUserName').value.trim() || 'П';
        const letter = currentName[0].toUpperCase();
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="${bg}"/><text x="50%" y="54%" font-family="system-ui, sans-serif" font-weight="700" font-size="28" fill="${color}" text-anchor="middle" dominant-baseline="middle">${letter}</text></svg>`;
        this.selectedAvatar = 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
        previewWrap.innerHTML = `<img src="${this.selectedAvatar}" alt="Аватар" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid var(--brand);">`;
      };
    });

    // Загрузка своего файла фото
    const fileInput = this.overlay.querySelector('#accAvatarUpload');
    if (fileInput) {
      fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (loadEvent) => {
            this.selectedAvatar = loadEvent.target.result;
            previewWrap.innerHTML = `<img src="${this.selectedAvatar}" alt="Аватар" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid var(--brand);">`;
          };
          reader.readAsDataURL(file);
        }
      };
    }

    const form = this.overlay.querySelector('#accountProfileForm');
    form.onsubmit = async (e) => {
      e.preventDefault();
      const newName = this.overlay.querySelector('#accUserName').value.trim();
      const newEmail = this.overlay.querySelector('#accUserEmail').value.trim();
      const oldPwd = (this.overlay.querySelector('#accOldPassword')?.value || '').trim();
      const newPwd = (this.overlay.querySelector('#accUserPassword')?.value || '').trim();
      const voiceSel = this.overlay.querySelector('#accVoiceSelect')?.value || 'baya';
      const alertBox = this.overlay.querySelector('#accountModalAlert');

      store.setVoice(voiceSel);

      if (newPwd) {
        if (!oldPwd) {
          if (alertBox) {
            alertBox.style.display = 'block';
            alertBox.style.background = '#FEF2F2';
            alertBox.style.color = '#B91C1C';
            alertBox.textContent = 'Укажите текущий пароль для смены пароля';
          }
          return;
        }
        const pwdRes = await authApi.changePassword(oldPwd, newPwd);
        if (pwdRes._status >= 400 || pwdRes._error) {
          if (alertBox) {
            alertBox.style.display = 'block';
            alertBox.style.background = '#FEF2F2';
            alertBox.style.color = '#B91C1C';
            alertBox.textContent = pwdRes._error || 'Не удалось сменить пароль';
          }
          return;
        }
        if (alertBox) {
          alertBox.style.display = 'block';
          alertBox.style.background = '#E8F7F0';
          alertBox.style.color = '#00875A';
          alertBox.textContent = 'Пароль обновлён. Требуется повторный вход...';
        }
        setTimeout(() => store.logout(), 900);
        return;
      }

      if (newName) {
        if (store.isAuthenticated()) {
          const updated = await authApi.updateMe({ name: newName });
          if (updated && updated.id) {
            store.setUser({
              name: updated.name,
              email: updated.email,
              avatar: this.selectedAvatar,
            });
          } else {
            store.setUser({
              name: newName,
              email: newEmail,
              avatar: this.selectedAvatar,
            });
          }
        } else {
          store.setUser({
            name: newName,
            email: newEmail,
            avatar: this.selectedAvatar
          });
        }

        if (alertBox) {
          alertBox.style.display = 'block';
          alertBox.style.background = '#E8F7F0';
          alertBox.style.color = '#00875A';
          alertBox.textContent = 'Данные профиля успешно обновлены';
        }

        setTimeout(() => this.close(), 700);
      }
    };
  }

  close() {
    this.overlay.style.display = 'none';
  }
}
