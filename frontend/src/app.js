/**
 * App: Главная точка входа клиентского приложения Аптечка
 */

import { store } from './state/store.js';
import { kitApi } from './api/kit.api.js';
import { AmbientBackground } from './components/AmbientBackground.js';
import { Catalog } from './components/Catalog.js';
import { Chat } from './components/Chat.js';
import { Kit } from './components/Kit.js';
import { AccountProfileModal } from './components/AccountProfileModal.js';
import { ConfirmModal } from './components/ConfirmModal.js';
import { ColabRunner } from './components/ColabRunner.js';

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Инициализация атмосферного зимнего фона
  const canvas = document.getElementById('ambientCanvas');
  if (canvas) {
    new AmbientBackground(canvas);
  }

  // 2. Инициализация новогодней гирлянды с дугами-фестонами
  const garlandBulbs = document.getElementById('garlandBulbs');
  if (garlandBulbs) {
    const bulbColors = ['#FF3B30', '#FFB300', '#00B074', '#4EA8DE', '#AF52DE', '#FF9500'];
    const count = 32;
    for (let i = 0; i < count; i++) {
      const node = document.createElement('div');
      node.className = 'garland-bulb-node';
      const col = bulbColors[i % bulbColors.length];
      node.innerHTML = `
        <div class="garland-bulb-socket"></div>
        <div class="garland-bulb-lamp" style="background: ${col}; color: ${col}; animation-delay: ${(i * 0.12) % 1.8}s;"></div>
      `;
      garlandBulbs.appendChild(node);
    }
  }

  // 3. Интерактивная «Пилюля на прогулке» в стиле Google Colab
  const colabRunner = new ColabRunner(document.body);

  const treeTrigger = document.getElementById('brandTreeTrigger');
  if (treeTrigger) {
    treeTrigger.addEventListener('click', () => colabRunner.runAcross());
  }

  // 4. Инициализация модальных окон
  const modalOverlay = document.getElementById('modalOverlay');
  const accountModal = new AccountProfileModal(modalOverlay);

  // 5. Монтирование компонентов
  const catalogMount = document.getElementById('catalogViewMount');
  const chatMount = document.getElementById('chatViewMount');
  const kitMount = document.getElementById('kitColumnMount');

  const catalog = new Catalog(catalogMount);
  const chat = new Chat(chatMount);
  const kit = new Kit(kitMount);

  // 6. Загрузка стартовых медикаментов
  const initialItems = await kitApi.getItems();
  store.setKitItems(initialItems);

  // 7. Переключение центральных табов (Умная консультация <-> Аптека)
  const tabChatBtn = document.getElementById('tabChatBtn');
  const tabCatalogBtn = document.getElementById('tabCatalogBtn');

  function switchTab(tab) {
    store.setActiveTab(tab);
    if (tab === 'chat') {
      tabChatBtn.classList.add('active');
      tabCatalogBtn.classList.remove('active');
      chatMount.style.display = 'flex';
      catalogMount.style.display = 'none';
    } else {
      tabChatBtn.classList.remove('active');
      tabCatalogBtn.classList.add('active');
      chatMount.style.display = 'none';
      catalogMount.style.display = 'flex';
      catalogMount.style.flexDirection = 'column';
      catalog.renderGrid();
    }
  }

  tabChatBtn.addEventListener('click', () => switchTab('chat'));
  tabCatalogBtn.addEventListener('click', () => switchTab('catalog'));

  // 8. Симметричное управление сайдбарами
  const appContainer = document.getElementById('appContainer');
  const leftRail = document.getElementById('leftRail');
  const kitColumn = document.getElementById('kitColumnMount');
  const toggleLeftBtn = document.getElementById('toggleLeftRailBtn');
  const toggleRightBtn = document.getElementById('toggleRightRailBtn');

  if (toggleLeftBtn) {
    toggleLeftBtn.addEventListener('click', () => {
      const isCollapsed = store.toggleLeftSidebar();
      appContainer.classList.toggle('left-collapsed', isCollapsed);
      leftRail.classList.toggle('collapsed', isCollapsed);
    });
  }

  if (toggleRightBtn) {
    toggleRightBtn.addEventListener('click', () => {
      const isCollapsed = store.toggleRightSidebar();
      appContainer.classList.toggle('right-collapsed', isCollapsed);
      kitColumn.classList.toggle('collapsed', isCollapsed);
    });
  }

  // 9. Мультичат: рендеринг списка сессий в левом рейле
  const sessionsList = document.getElementById('chatSessionsList');
  const newChatBtn = document.getElementById('newChatBtn');

  function getSessionBadge(title) {
    if (!title) return 'Д';
    const words = title.trim().split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return title.slice(0, 2).toUpperCase();
  }

  function renderSessions() {
    if (!sessionsList) return;
    const state = store.getState();

    sessionsList.innerHTML = `
      <div class="session-group-title">Диалоги</div>
      ${state.sessions.map(s => {
        let lastMsgText = '';
        if (s.messages && s.messages.length > 0) {
          const lastMsg = s.messages[s.messages.length - 1];
          lastMsgText = (lastMsg.text || '').replace(/\s+/g, ' ').trim();
        }
        const snippet = lastMsgText ? (lastMsgText.slice(0, 36) + (lastMsgText.length > 36 ? '…' : '')) : '';
        const hoverTooltip = `${s.title}${lastMsgText ? '\nПоследнее: ' + lastMsgText.slice(0, 100) : ''}`;
        const badgeText = getSessionBadge(s.title);

        return `
          <div class="session-item tap-effect ${s.id === state.activeSessionId ? 'active' : ''}" data-id="${s.id}" title="${hoverTooltip}">
            <span class="session-badge-initials">${badgeText}</span>
            <div class="session-text-block">
              <span class="session-title-text">${s.title}</span>
              ${snippet ? `<span class="session-snippet-text">${snippet}</span>` : ''}
            </div>
            <button class="session-delete-btn" data-id="${s.id}" title="Удалить диалог">&times;</button>
          </div>
        `;
      }).join('')}
    `;

    sessionsList.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.session-delete-btn')) return;
        const id = item.dataset.id;
        store.switchSession(id);
        switchTab('chat');
        renderSessions();
      });
    });

    sessionsList.querySelectorAll('.session-delete-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const confirmed = await ConfirmModal.confirm({
          title: 'Удаление диалога',
          message: 'Вы уверены, что хотите удалить эту консультацию?',
          confirmText: 'Удалить',
          cancelText: 'Отмена',
          danger: true
        });

        if (confirmed) {
          store.deleteSession(id);
          renderSessions();
        }
      });
    });
  }

  newChatBtn.addEventListener('click', () => {
    store.createSession();
    switchTab('chat');
    renderSessions();
  });

  renderSessions();
  store.subscribe('sessions:updated', () => renderSessions());

  // 10. Профиль пользователя (Аккаунт КТ1) и RBAC для панели администратора
  const userBadgeBtn = document.getElementById('userProfileBadge');
  if (userBadgeBtn) {
    userBadgeBtn.addEventListener('click', () => accountModal.open());
  }

  const profileSettingsBtn = document.getElementById('profileSettingsBtn');
  if (profileSettingsBtn) {
    profileSettingsBtn.addEventListener('click', () => accountModal.open());
  }

  const railLogoutBtn = document.getElementById('railLogoutBtn');
  if (railLogoutBtn) {
    railLogoutBtn.addEventListener('click', () => {
      store.logout();
    });
  }

  const adminBtn = document.getElementById('adminQuickSwitchBtn');
  function syncAdminVisibility(user) {
    if (adminBtn) {
      const isAdmin = user && (user.role === 'admin' || user.role === 'superadmin');
      adminBtn.style.display = isAdmin ? 'flex' : 'none';
    }
  }
  
  function applyUserProfile(user) {
    const isGuest = user.role === 'guest' || !user.email;
    const nameEl = document.querySelector('.user-meta-name');
    if (nameEl) nameEl.textContent = isGuest ? 'Гость' : (user.name || 'Пользователь');

    const statusEl = document.querySelector('.user-meta-status');
    if (statusEl) {
      if (isGuest) {
        statusEl.textContent = 'Гостевой режим';
      } else if (user.role === 'superadmin') {
        statusEl.textContent = 'Суперадминистратор';
      } else if (user.role === 'admin') {
        statusEl.textContent = 'Администратор';
      } else {
        statusEl.textContent = 'Личный профиль';
      }
    }
    
    const avatarEl = document.querySelector('.user-avatar-circle');
    if (avatarEl) {
      if (user.avatar) {
        avatarEl.innerHTML = `<img src="${user.avatar}" alt="${user.name || 'Аватар'}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
      } else if (isGuest) {
        avatarEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
      } else {
        avatarEl.textContent = (user.name || 'П')[0].toUpperCase();
      }
    }
    syncAdminVisibility(user);
  }

  // Применяем профиль немедленно при загрузке
  applyUserProfile(store.getState().user);

  store.subscribe('user:updated', (user) => {
    applyUserProfile(user);
  });
});
