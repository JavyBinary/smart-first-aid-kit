/**
 * App: Главная точка входа клиентского приложения MedAI (синхронизирована с PostgreSQL/SSE)
 */

import { store } from './state/store.js';
import { kitApi } from './api/kit.api.js';
import { authApi } from './api/auth.api.js';
import { profileApi } from './api/profile.api.js';
import { dialogsApi } from './api/dialogs.api.js';
import { AmbientBackground } from './components/AmbientBackground.js';
import { Catalog } from './components/Catalog.js';
import { Chat } from './components/Chat.js';
import { Kit } from './components/Kit.js';
import { AccountProfileModal } from './components/AccountProfileModal.js';
import { ConfirmModal } from './components/ConfirmModal.js';
import { ColabRunner } from './components/ColabRunner.js';

function mapServerMessages(serverMessages) {
  if (!Array.isArray(serverMessages)) return [];
  return serverMessages.map((m) => {
    const rag = m.rag_payload || {};
    if (m.role === 'user') {
      return {
        id: m.id,
        serverMessageId: m.id,
        sender: 'user',
        text: m.content,
        attachedPills: [],
      };
    }
    return {
      id: m.id,
      serverMessageId: m.id,
      sender: 'bot',
      text: m.content,
      isEmergency: Boolean(rag.emergency_mode),
      feedback: m.feedback ?? null,
      reported: Boolean(m.reported),
      data: {
        message: m.content,
        emergency_mode: Boolean(rag.emergency_mode),
        first_aid_steps: rag.first_aid_steps || [],
        recommendation: rag.recommendation || null,
        safety_warnings: rag.safety_warnings || [],
        sources: rag.sources || [],
        used_llm: Boolean(rag.used_llm),
      },
    };
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Атмосферный фон
  const canvas = document.getElementById('ambientCanvas');
  if (canvas) new AmbientBackground(canvas);

  // 2. Новогодняя гирлянда
  const garlandBulbs = document.getElementById('garlandBulbs');
  if (garlandBulbs) {
    const bulbColors = ['#FF3B30', '#FFB300', '#00B074', '#4EA8DE', '#AF52DE', '#FF9500'];
    for (let i = 0; i < 32; i++) {
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

  // 3. Маскот-пилюля
  const colabRunner = new ColabRunner(document.body);
  const treeTrigger = document.getElementById('brandTreeTrigger');
  if (treeTrigger) treeTrigger.addEventListener('click', () => colabRunner.runAcross());

  // 4. Модальные окна и основные компоненты
  const modalOverlay = document.getElementById('modalOverlay');
  const accountModal = new AccountProfileModal(modalOverlay);
  const catalogMount = document.getElementById('catalogViewMount');
  const chatMount = document.getElementById('chatViewMount');
  const kitMount = document.getElementById('kitColumnMount');

  const catalog = new Catalog(catalogMount);
  new Chat(chatMount);
  new Kit(kitMount);

  // 5. Переключение вкладок
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

  // 6. Управление боковыми панелями
  const appContainer = document.getElementById('appContainer');
  const leftRail = document.getElementById('leftRail');
  const kitColumn = document.getElementById('kitColumnMount');
  document.getElementById('toggleLeftRailBtn')?.addEventListener('click', () => {
    const isCollapsed = store.toggleLeftSidebar();
    appContainer.classList.toggle('left-collapsed', isCollapsed);
    leftRail.classList.toggle('collapsed', isCollapsed);
  });
  document.getElementById('toggleRightRailBtn')?.addEventListener('click', () => {
    const isCollapsed = store.toggleRightSidebar();
    appContainer.classList.toggle('right-collapsed', isCollapsed);
    kitColumn.classList.toggle('collapsed', isCollapsed);
  });

  // 7. Диалоги в левом рейле
  const sessionsList = document.getElementById('chatSessionsList');
  const newChatBtn = document.getElementById('newChatBtn');

  function getSessionBadge(title) {
    if (!title) return 'Д';
    const words = title.trim().split(/\s+/).filter(Boolean);
    return words.length >= 2 ? (words[0][0] + words[1][0]).toUpperCase() : title.slice(0, 2).toUpperCase();
  }

  async function ensureDialogLoaded(session) {
    if (!session || !store.isAuthenticated() || !session.serverBacked || session.loadedFromServer) return;
    const res = await dialogsApi.getMessages(session.id);
    if (res && !res._fallback && !res._status && Array.isArray(res.messages)) {
      store.setSessionMessages(session.id, mapServerMessages(res.messages));
    }
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
        const badgeText = getSessionBadge(s.title);
        return `
          <div class="session-item tap-effect ${s.id === state.activeSessionId ? 'active' : ''}" data-id="${s.id}">
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
      item.addEventListener('click', async (e) => {
        if (e.target.closest('.session-delete-btn')) return;
        const id = item.dataset.id;
        store.switchSession(id);
        switchTab('chat');
        renderSessions();
        const session = store.getState().sessions.find((s) => s.id === id);
        await ensureDialogLoaded(session);
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
          const target = store.getState().sessions.find((s) => s.id === id);
          if (store.isAuthenticated() && target && target.serverBacked) {
            await dialogsApi.deleteDialog(id);
          }
          store.deleteSession(id);
          renderSessions();
        }
      });
    });
  }

  newChatBtn.addEventListener('click', async () => {
    if (store.isAuthenticated()) {
      const created = await dialogsApi.createDialog('Новый диалог');
      if (created && created.dialog_id) {
        store.createSession('Новый диалог', created.dialog_id);
        switchTab('chat');
        renderSessions();
        return;
      }
    }
    store.createSession();
    switchTab('chat');
    renderSessions();
  });

  renderSessions();
  store.subscribe('sessions:updated', () => renderSessions());

  // 8. Профиль и RBAC
  document.getElementById('userProfileBadge')?.addEventListener('click', () => accountModal.open());
  document.getElementById('profileSettingsBtn')?.addEventListener('click', () => accountModal.open());
  document.getElementById('railLogoutBtn')?.addEventListener('click', () => store.logout());

  const adminBtn = document.getElementById('adminQuickSwitchBtn');
  function applyUserProfile(user) {
    const isGuest = user.role === 'guest' || !user.email;
    const nameEl = document.querySelector('.user-meta-name');
    if (nameEl) nameEl.textContent = isGuest ? 'Гость' : (user.name || 'Пользователь');

    const statusEl = document.querySelector('.user-meta-status');
    if (statusEl) {
      if (isGuest) statusEl.textContent = 'Гостевой режим';
      else if (user.role === 'superadmin') statusEl.textContent = 'Суперадминистратор';
      else if (user.role === 'admin') statusEl.textContent = 'Администратор';
      else statusEl.textContent = 'Личный профиль';
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
    if (adminBtn) {
      adminBtn.style.display = (user.role === 'admin' || user.role === 'superadmin') ? 'flex' : 'none';
    }
  }

  // 9. Проверка реальной cookie-сессии и гидратация данных из PostgreSQL
  const me = await authApi.getMe();
  if (me && me.id) {
    store.setUser({ id: me.id, name: me.name, email: me.email, role: me.role });
    const [kitItems, profileData, serverDialogs, reportNews] = await Promise.all([
      kitApi.getItems(),
      profileApi.getProfile(),
      dialogsApi.listDialogs(),
      dialogsApi.getReportNews(),
    ]);
    if (Array.isArray(kitItems)) {
      store.setKitItems(kitItems);
      catalog.updateCardButtons();
    }
    if (profileData) {
      store.setHealthProfile(profileData);
    } else {
      store.setHealthProfile({ age: 25, weight: 65, allergies: [], chronic: [], notes: [] });
    }
    if (Array.isArray(serverDialogs) && serverDialogs.length > 0) {
      const mapped = serverDialogs.map((d) => ({
        id: d.dialog_id,
        title: d.title || 'Консультация',
        date: 'История',
        messages: [],
        serverBacked: true,
        loadedFromServer: false,
      }));
      store.setSessions(mapped, mapped[0].id);
      await ensureDialogLoaded(mapped[0]);
    } else {
      store.setSessions([{ id: 'sess_default', title: 'Новый диалог', date: 'Сегодня', messages: [], serverBacked: false }]);
    }
    store.setReportNews(reportNews);
  } else {
    store.setUser({ id: null, name: 'Гость', email: '', role: 'guest', avatar: '' });
    store.setKitItems([]);
    applyUserProfile(store.getState().user);
  }

  store.subscribe('user:updated', (user) => applyUserProfile(user));
});
