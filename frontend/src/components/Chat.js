/**
 * Chat: Интеллектуальный медицинский диалог
 */

import { store } from '../state/store.js';
import { chatApi } from '../api/chat.api.js';
import { Mascot } from './Mascot.js';

export class Chat {
  constructor(containerElement) {
    this.container = containerElement;
    this.emptyMascot = null;

    this.render();
    this.attachEvents();

    store.subscribe('messages:updated', () => this.renderMessages());
    store.subscribe('session:switched', () => this.renderMessages());
    store.subscribe('selectedPills:updated', () => this.renderSelectedPills());
    store.subscribe('user:updated', () => this.renderMessages());
    store.subscribe('mascot:stateChanged', (state) => this.handleMascotState(state));
  }

  handleMascotState(state) {
    if (this.emptyMascot) this.emptyMascot.setState(state);
  }

  attachEvents() {
    const input = this.container.querySelector('#chatTextarea');
    const sendBtn = this.container.querySelector('#chatSendBtn');

    if (input && sendBtn) {
      input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
        sendBtn.disabled = !input.value.trim() && !store.getState().selectedPills.length;
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });

      sendBtn.addEventListener('click', () => this.handleSendMessage());
    }
  }

  async handleSendMessage() {
    const input = this.container.querySelector('#chatTextarea');
    const text = input ? input.value.trim() : '';
    const state = store.getState();
    const selectedPills = [...state.selectedPills];

    if (!text && !selectedPills.length) return;

    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }
    const sendBtn = this.container.querySelector('#chatSendBtn');
    if (sendBtn) sendBtn.disabled = true;

    // 1. Сообщение пользователя
    store.addMessageToActiveSession({
      id: `msg_${Date.now()}`,
      sender: 'user',
      text: text || 'Посоветуйте применение для выбранных препаратов',
      attachedPills: selectedPills
    });

    state.selectedPills = [];
    store.notify('selectedPills:updated', []);

    // 2. Статус маскота «думает»
    store.setMascotState('thinking');

    // 3. Запрос
    const response = await chatApi.sendQuery(text, state.kitItems, selectedPills);

    // 4. Проверка Red Flags
    if (response.emergency_mode) {
      store.setMascotState('emergency');
      store.addMessageToActiveSession({
        id: `msg_${Date.now()}_bot`,
        sender: 'bot',
        isEmergency: true,
        data: response
      });
      return;
    }

    // 5. Обычный RAG-ответ
    store.setMascotState('idle');
    store.addMessageToActiveSession({
      id: `msg_${Date.now()}_bot`,
      sender: 'bot',
      isEmergency: false,
      data: response
    });
  }

  renderSelectedPills() {
    const bar = this.container.querySelector('#selectedMedicinesBar');
    if (!bar) return;

    const pills = store.getState().selectedPills;
    if (!pills.length) {
      bar.innerHTML = '';
      bar.style.display = 'none';
      return;
    }

    bar.style.display = 'flex';
    bar.innerHTML = pills.map(p => `
      <div class="selected-med-pill">
        <span>💊 ${p.name} (${p.dosage})</span>
        <button class="selected-med-pill-remove" data-id="${p.id}">&times;</button>
      </div>
    `).join('');

    bar.querySelectorAll('.selected-med-pill-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const item = store.getState().kitItems.find(i => i.id === id);
        if (item) store.togglePillSelection(item);
      });
    });

    const sendBtn = this.container.querySelector('#chatSendBtn');
    if (sendBtn) sendBtn.disabled = false;
  }

  renderMessages() {
    const list = this.container.querySelector('#chatMessagesList');
    if (!list) return;

    const state = store.getState();
    const session = state.sessions.find(s => s.id === state.activeSessionId);
    const messages = session ? session.messages : [];
    const userName = (state.user && state.user.name) ? state.user.name : 'Лука';

    if (!messages.length) {
      list.className = 'chat-messages-container empty';
      list.innerHTML = `
        <div class="chat-empty-state">
          <div class="empty-mascot-wrapper" id="emptyMascotMount"></div>
          <h2 class="empty-state-greeting">Чем могу помочь сегодня, ${userName}?</h2>
        </div>
      `;

      const mount = list.querySelector('#emptyMascotMount');
      if (mount) {
        this.emptyMascot = new Mascot(mount);
      }
      return;
    }

    list.className = 'chat-messages-container';
    list.innerHTML = messages.map(msg => {
      if (msg.sender === 'user') {
        return `
          <div class="message-row user">
            <div class="message-bubble">
              ${msg.attachedPills && msg.attachedPills.length ? `
                <div style="font-size: 12px; margin-bottom: 6px; opacity: 0.9;">
                  💊 Контекст: ${msg.attachedPills.map(p => p.name).join(', ')}
                </div>
              ` : ''}
              ${msg.text}
            </div>
          </div>
        `;
      }

      // Ответ бота
      if (msg.isEmergency) {
        return `
          <div class="message-row bot">
            <div class="message-bubble">
              <div class="emergency-card">
                <div class="emergency-header">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                  <span>ПРОТОКОЛ НЕОТЛОЖНОЙ ПОМОЩИ (RED FLAG)</span>
                </div>
                <p style="font-weight: 600; font-size: 14.5px; color: #181C20; margin-bottom: 12px;">
                  ${msg.data.message}
                </p>
                <div style="font-size: 13.5px; color: #374151; line-height: 1.6;">
                  ${msg.data.first_aid_steps.map(s => `<div>• ${s}</div>`).join('')}
                </div>
                <a href="tel:112" class="emergency-call-btn tap-effect">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                  Вызвать скорую помощь (112)
                </a>
              </div>
            </div>
          </div>
        `;
      }

      const rec = msg.data.recommendation;
      return `
        <div class="message-row bot">
          <div class="message-bubble">
            <div class="rag-card">
              <div class="rag-card-header">
                <span class="rag-med-title">${rec.medicine_name}</span>
                <span class="rag-kit-badge ${rec.in_user_kit ? 'in-kit' : 'out-kit'}">
                  ${rec.in_user_kit ? '✓ Есть в вашей аптечке' : '✕ Нет в наличии'}
                </span>
              </div>

              <div class="rag-section">
                <div class="rag-section-title">Режим дозирования</div>
                <div class="rag-section-text">${rec.dosage}</div>
              </div>

              <div class="rag-section">
                <div class="rag-section-title">Противопоказания и предупреждения</div>
                <div class="rag-section-text" style="color: #4B5563;">
                  ${rec.contraindications}<br/>
                  <span style="font-weight: 600; color: #D97008; margin-top: 4px; display: inline-block;">
                    Предупреждение: ${rec.warnings}
                  </span>
                </div>
              </div>

              <div class="rag-meta-footer">
                <div>Источник: ${msg.data.sources ? msg.data.sources[0].title : 'Официальная инструкция Минздрава РФ'}</div>
                <div style="font-size: 11px; margin-top: 4px; opacity: 0.8;">${msg.data.disclaimer}</div>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    list.scrollTop = list.scrollHeight;
  }

  render() {
    this.container.innerHTML = `
      <div class="chat-view-wrap">
        <!-- Лента сообщений -->
        <div class="chat-messages-container" id="chatMessagesList"></div>

        <!-- Зона ввода сообщения -->
        <div class="chat-input-area">
          <div class="selected-medicines-bar" id="selectedMedicinesBar" style="display: none;"></div>

          <div class="chat-input-row">
            <textarea id="chatTextarea" class="chat-textarea" placeholder="Опишите ваши симптомы или задайте вопрос о дозировке..." rows="1"></textarea>
            <button id="chatSendBtn" class="chat-send-btn tap-effect" disabled title="Отправить сообщение">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;

    this.renderMessages();
  }
}
