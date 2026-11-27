/**
 * Централизованный реактивный Store приложения MedAI
 */
import { authApi } from '../api/auth.api.js';

export const VOICE_OPTIONS = [
  { id: 'baya', label: 'Baya (женский, мягкий)', short: 'Baya' },
  { id: 'kseniya', label: 'Kseniya (женский, чёткий)', short: 'Kseniya' },
  { id: 'xenia', label: 'Xenia (женский, тёплый)', short: 'Xenia' },
  { id: 'aidar', label: 'Aidar (мужской, спокойный)', short: 'Aidar' },
  { id: 'eugene', label: 'Eugene (мужской, низкий)', short: 'Eugene' },
];

class AppStore {
  constructor() {
    this.subscribers = new Map();

    const savedSessions = localStorage.getItem('medai_sessions');
    let initialSessions = [];
    if (savedSessions) {
      try {
        initialSessions = JSON.parse(savedSessions);
      } catch (e) {}
    }
    if (!initialSessions.length) {
      initialSessions = [
        { id: 'sess_default', title: 'Новый диалог', date: 'Сегодня', messages: [], serverBacked: false }
      ];
    }

    const savedHealth = localStorage.getItem('medai_health_profile');
    let healthProfile = { age: 25, weight: 65, allergies: [], chronic: [], notes: [] };
    if (savedHealth) {
      try {
        const parsed = JSON.parse(savedHealth);
        healthProfile = {
          age: parsed.age ?? 25,
          weight: parsed.weight ?? 65,
          allergies: Array.isArray(parsed.allergies) ? parsed.allergies : [],
          chronic: Array.isArray(parsed.chronic) ? parsed.chronic : [],
          notes: Array.isArray(parsed.notes) ? parsed.notes : [],
        };
      } catch (e) {}
    }

    const savedRole = localStorage.getItem('medai_role') || 'guest';
    const isGuest = savedRole === 'guest';
    const savedName = localStorage.getItem('medai_name');
    const savedUser = localStorage.getItem('medai_user');

    this.state = {
      user: {
        id: null,
        name: isGuest ? 'Гость' : (savedName || 'Пользователь'),
        email: isGuest ? '' : (savedUser || ''),
        role: savedRole,
        avatar: isGuest ? '' : (localStorage.getItem('medai_avatar') || '')
      },
      activeTab: 'chat', // 'chat' | 'catalog'
      kitItems: [],
      selectedPills: [],
      sessions: initialSessions,
      activeSessionId: initialSessions[0].id,
      healthProfile,
      mascotState: 'idle', // 'idle' | 'thinking' | 'happy' | 'emergency'
      leftSidebarCollapsed: false,
      rightSidebarCollapsed: false,
      rightActiveTab: 'kit', // 'kit' | 'medcard'
      responseDepth: localStorage.getItem('medai_depth') || 'detailed',
      voice: localStorage.getItem('medai_voice') || 'baya',
      reportNews: [],
    };
  }

  getState() {
    return this.state;
  }

  isAuthenticated() {
    return this.state.user.role !== 'guest' && Boolean(this.state.user.email);
  }

  subscribe(event, callback) {
    if (!this.subscribers.has(event)) {
      this.subscribers.set(event, new Set());
    }
    this.subscribers.get(event).add(callback);
    return () => this.subscribers.get(event).delete(callback);
  }

  notify(event, payload) {
    if (this.subscribers.has(event)) {
      this.subscribers.get(event).forEach(cb => cb(payload, this.state));
    }
  }

  setKitItems(items) {
    this.state.kitItems = Array.isArray(items) ? items : [];
    this.notify('kit:updated', this.state.kitItems);
  }

  addKitItem(item) {
    this.state.kitItems.unshift(item);
    this.notify('kit:updated', this.state.kitItems);
  }

  updateKitItem(updatedItem) {
    if (!updatedItem || !updatedItem.id) return;
    const idx = this.state.kitItems.findIndex(i => String(i.id) === String(updatedItem.id));
    if (idx !== -1) {
      this.state.kitItems[idx] = { ...this.state.kitItems[idx], ...updatedItem };
    }
    const selIdx = this.state.selectedPills.findIndex(p => String(p.id) === String(updatedItem.id));
    if (selIdx !== -1) {
      this.state.selectedPills[selIdx] = { ...this.state.selectedPills[selIdx], ...updatedItem };
      this.notify('selectedPills:updated', this.state.selectedPills);
    }
    this.notify('kit:updated', this.state.kitItems);
  }

  removeKitItem(id) {
    this.state.kitItems = this.state.kitItems.filter(i => i.id !== id);
    this.state.selectedPills = this.state.selectedPills.filter(i => i.id !== id);
    this.notify('kit:updated', this.state.kitItems);
    this.notify('selectedPills:updated', this.state.selectedPills);
  }

  togglePillSelection(item) {
    const exists = this.state.selectedPills.some(p => p.id === item.id);
    if (exists) {
      this.state.selectedPills = this.state.selectedPills.filter(p => p.id !== item.id);
    } else {
      this.state.selectedPills.push(item);
    }
    this.notify('selectedPills:updated', this.state.selectedPills);
  }

  setActiveTab(tabName) {
    this.state.activeTab = tabName;
    this.notify('tab:changed', tabName);
  }

  setMascotState(state) {
    this.state.mascotState = state;
    this.notify('mascot:stateChanged', state);
  }

  setResponseDepth(depth) {
    this.state.responseDepth = depth === 'brief' ? 'brief' : 'detailed';
    localStorage.setItem('medai_depth', this.state.responseDepth);
    this.notify('depth:changed', this.state.responseDepth);
  }

  setVoice(voice) {
    this.state.voice = voice || 'baya';
    localStorage.setItem('medai_voice', this.state.voice);
    this.notify('voice:changed', this.state.voice);
  }

  setReportNews(news) {
    this.state.reportNews = Array.isArray(news) ? news : [];
    this.notify('reportNews:updated', this.state.reportNews);
  }

  setSessions(sessions, activeSessionId = null) {
    const list = Array.isArray(sessions) && sessions.length
      ? sessions
      : [{ id: 'sess_default', title: 'Новый диалог', date: 'Сегодня', messages: [], serverBacked: false }];
    this.state.sessions = list;
    this.state.activeSessionId = activeSessionId && list.some(s => s.id === activeSessionId)
      ? activeSessionId
      : list[0].id;
    this.persistSessions();
    this.notify('sessions:updated', this.state.sessions);
    this.notify('session:switched', this.state.sessions.find(s => s.id === this.state.activeSessionId));
  }

  createSession(title = 'Новый диалог', serverId = null) {
    const newSession = {
      id: serverId || `sess_${Date.now()}`,
      title,
      date: 'Сегодня',
      messages: [],
      serverBacked: Boolean(serverId),
    };
    this.state.sessions.unshift(newSession);
    this.state.activeSessionId = newSession.id;
    this.persistSessions();
    this.notify('sessions:updated', this.state.sessions);
    this.notify('session:switched', newSession);
    return newSession;
  }

  replaceSessionId(oldId, newId, newTitle = null) {
    const session = this.state.sessions.find(s => s.id === oldId);
    if (!session) return;
    session.id = newId;
    session.serverBacked = true;
    if (newTitle) session.title = newTitle;
    if (this.state.activeSessionId === oldId) {
      this.state.activeSessionId = newId;
    }
    this.persistSessions();
    this.notify('sessions:updated', this.state.sessions);
  }

  switchSession(sessionId) {
    this.state.activeSessionId = sessionId;
    const session = this.state.sessions.find(s => s.id === sessionId);
    this.notify('session:switched', session);
  }

  setSessionMessages(sessionId, messages) {
    const session = this.state.sessions.find(s => s.id === sessionId);
    if (!session) return;
    session.messages = Array.isArray(messages) ? messages : [];
    session.loadedFromServer = true;
    this.persistSessions();
    if (this.state.activeSessionId === sessionId) {
      this.notify('messages:updated', session.messages);
    }
  }

  deleteSession(sessionId) {
    this.state.sessions = this.state.sessions.filter(s => s.id !== sessionId);
    if (!this.state.sessions.length) {
      this.createSession();
      return;
    }
    if (this.state.activeSessionId === sessionId) {
      this.state.activeSessionId = this.state.sessions[0].id;
    }
    this.persistSessions();
    this.notify('sessions:updated', this.state.sessions);
    this.notify('session:switched', this.state.sessions[0]);
  }

  addMessageToActiveSession(msg) {
    const session = this.state.sessions.find(s => s.id === this.state.activeSessionId);
    if (session) {
      session.messages.push(msg);
      if (session.messages.length === 1 && msg.sender === 'user') {
        session.title = msg.text.slice(0, 36) + (msg.text.length > 36 ? '…' : '');
      }
      this.persistSessions();
      this.notify('messages:updated', session.messages);
      this.notify('sessions:updated', this.state.sessions);
    }
    return msg;
  }

  updateMessageInSession(sessionId, messageId, updater) {
    const session = this.state.sessions.find(s => String(s.id) === String(sessionId));
    if (!session) return;
    const idx = session.messages.findIndex(m => String(m.id) === String(messageId));
    if (idx === -1) return;
    const current = session.messages[idx];
    session.messages[idx] = typeof updater === 'function' ? updater(current) : { ...current, ...updater };
    this.persistSessions();
    if (this.state.activeSessionId === sessionId) {
      this.notify('messages:updated', session.messages);
    }
  }

  setUser(userData) {
    this.state.user = { ...this.state.user, ...userData };
    if (userData.name !== undefined) localStorage.setItem('medai_name', userData.name || '');
    if (userData.email !== undefined) localStorage.setItem('medai_user', userData.email || '');
    if (userData.role !== undefined) localStorage.setItem('medai_role', userData.role || 'guest');
    if (userData.avatar !== undefined) localStorage.setItem('medai_avatar', userData.avatar || '');
    this.notify('user:updated', this.state.user);
  }

  async logout() {
    try {
      await authApi.logout();
    } catch {}
    localStorage.removeItem('medai_token');
    localStorage.removeItem('medai_user');
    localStorage.removeItem('medai_name');
    localStorage.removeItem('medai_role');
    localStorage.removeItem('medai_avatar');
    localStorage.removeItem('medai_sessions');
    localStorage.removeItem('medai_health_profile');
    this.state.user = { id: null, name: 'Гость', email: '', role: 'guest', avatar: '' };
    this.state.kitItems = [];
    this.state.selectedPills = [];
    this.state.healthProfile = { age: 25, weight: 65, allergies: [], chronic: [], notes: [] };
    this.notify('user:updated', this.state.user);
    window.location.href = 'login.html';
  }

  setRightActiveTab(tab) {
    this.state.rightActiveTab = tab;
    this.notify('rightTab:changed', tab);
  }

  toggleLeftSidebar() {
    this.state.leftSidebarCollapsed = !this.state.leftSidebarCollapsed;
    this.notify('sidebar:toggled', { side: 'left', collapsed: this.state.leftSidebarCollapsed });
    return this.state.leftSidebarCollapsed;
  }

  toggleRightSidebar() {
    this.state.rightSidebarCollapsed = !this.state.rightSidebarCollapsed;
    this.notify('sidebar:toggled', { side: 'right', collapsed: this.state.rightSidebarCollapsed });
    return this.state.rightSidebarCollapsed;
  }

  setHealthProfile(profile, silent = false) {
    this.state.healthProfile = profile;
    localStorage.setItem('medai_health_profile', JSON.stringify(profile));
    if (!silent) {
      this.notify('health:updated', profile);
    }
  }

  persistSessions() {
    localStorage.setItem('medai_sessions', JSON.stringify(this.state.sessions));
  }
}

export const store = new AppStore();
