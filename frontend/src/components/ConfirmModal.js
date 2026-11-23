/**
 * ConfirmModal: Современный внутрисистемный диалог подтверждения
 * Заменяет устаревший нативный window.confirm() браузера
 */

export class ConfirmModal {
  static confirm({ title = 'Подтверждение', message = 'Вы уверены?', confirmText = 'Удалить', cancelText = 'Отмена', danger = true }) {
    return new Promise((resolve) => {
      // Ищем или создаем контейнер
      let overlay = document.getElementById('confirmModalOverlay');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'confirmModalOverlay';
        overlay.className = 'confirm-modal-overlay';
        document.body.appendChild(overlay);
      }

      overlay.innerHTML = `
        <div class="confirm-modal-card">
          <div class="confirm-modal-icon ${danger ? 'danger' : ''}">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
          </div>
          <div class="confirm-modal-title">${title}</div>
          <div class="confirm-modal-message">${message}</div>
          <div class="confirm-modal-actions">
            <button class="confirm-modal-btn cancel tap-effect" id="confirmCancelBtn">${cancelText}</button>
            <button class="confirm-modal-btn ${danger ? 'danger' : 'primary'} tap-effect" id="confirmOkBtn">${confirmText}</button>
          </div>
        </div>
      `;

      overlay.style.display = 'flex';

      const cleanup = (result) => {
        overlay.style.display = 'none';
        window.removeEventListener('keydown', onKeyDown);
        resolve(result);
      };

      const onKeyDown = (e) => {
        if (e.key === 'Escape') cleanup(false);
      };

      window.addEventListener('keydown', onKeyDown);

      overlay.querySelector('#confirmCancelBtn').onclick = () => cleanup(false);
      overlay.querySelector('#confirmOkBtn').onclick = () => cleanup(true);

      overlay.onclick = (e) => {
        if (e.target === overlay) cleanup(false);
      };
    });
  }
}
