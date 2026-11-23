/**
 * Централизованный реактивный Store приложения Аптечка
 */

class AppStore {
  constructor() {
    this.subscribers = new Map();

    // Загрузка сохраненных сессий чата
    const savedSessions = localStorage.getItem('medai_sessions');
    let initialSessions = [];
    if (savedSessions) {
      try {
        initialSessions = JSON.parse(savedSessions);
      } catch (e) {}
    }
    if (!initialSessions.length) {
      initialSessions = [
        { id: 'sess_default', title: 'Консультация по симптомам', date: 'Сегодня', messages: [] }
      ];
    }

    // Загрузка медкарты
    const savedHealth = localStorage.getItem('medai_health_profile');
    let healthProfile = { allergies: ['Пенициллин'], chronic: ['Гастрит'] };
    if (savedHealth) {
      try {
        healthProfile = JSON.parse(savedHealth);
      } catch (e) {}
    }

    const savedRole = localStorage.getItem('medai_role') || 'user';
    const isGuest = savedRole === 'guest';
    const savedName = localStorage.getItem('medai_name');
    const savedUser = localStorage.getItem('medai_user');

    this.state = {
      user: {
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
      rightActiveTab: 'kit' // 'kit' | 'medcard'
    };
  }

  getState() {
    return this.state;
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
    this.state.kitItems = items;
    this.notify('kit:updated', items);
  }

  addKitItem(item) {
    this.state.kitItems.unshift(item);
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

  createSession(title = 'Новый диалог') {
    const newSession = {
      id: `sess_${Date.now()}`,
      title,
      date: 'Сегодня',
      messages: []
    };
    this.state.sessions.unshift(newSession);
    this.state.activeSessionId = newSession.id;
    this.persistSessions();
    this.notify('sessions:updated', this.state.sessions);
    this.notify('session:switched', newSession);
    return newSession;
  }

  switchSession(sessionId) {
    this.state.activeSessionId = sessionId;
    const session = this.state.sessions.find(s => s.id === sessionId);
    this.notify('session:switched', session);
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
      // Авто-генерация заголовка первого сообщения
      if (session.messages.length === 1 && msg.sender === 'user') {
        session.title = msg.text.slice(0, 32) + (msg.text.length > 32 ? '…' : '');
      }
      this.persistSessions();
      this.notify('messages:updated', session.messages);
      this.notify('sessions:updated', this.state.sessions);
    }
  }

  setUser(userData) {
    this.state.user = { ...this.state.user, ...userData };
    if (userData.name) localStorage.setItem('medai_name', userData.name);
    if (userData.email) localStorage.setItem('medai_user', userData.email);
    if (userData.role) localStorage.setItem('medai_role', userData.role);
    if (userData.avatar) localStorage.setItem('medai_avatar', userData.avatar);
    this.notify('user:updated', this.state.user);
  }

  logout() {
    localStorage.removeItem('medai_token');
    localStorage.removeItem('medai_user');
    localStorage.removeItem('medai_name');
    localStorage.removeItem('medai_role');
    localStorage.removeItem('medai_avatar');
    this.state.user = { name: 'Гость', email: '', role: 'guest', avatar: '' };
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
