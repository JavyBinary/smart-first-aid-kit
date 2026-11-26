/**
 * Chat: Интеллектуальный медицинский диалог (SSE, RAG, Guardrails, Feedback, Reports, TTS)
 */

import { store } from '../state/store.js';
import { chatApi } from '../api/chat.api.js';
import { dialogsApi } from '../api/dialogs.api.js';
import { Mascot } from './Mascot.js';

const QUICK_PROMPT_CHIPS = [
  { label: 'Болит голова', query: 'Болит голова и лёгкая усталость, что из моей аптечки подойдёт?' },
  { label: 'Высокая температура', query: 'Температура 38.6, озноб — чем сбить с учётом моей медкарты?' },
  { label: 'Болит живот / изжога', query: 'Тяжесть и боли в желудке после еды, что можно принять?' },
  { label: 'Аллергия / зуд', query: 'Сезонная аллергия, чихание и зуд — какой препарат подойдёт?' },
  { label: 'Ожог кипятком (112)', query: 'Ребёнок обжёг руку кипятком, волдырь, что делать прямо сейчас?' },
];

const FEEDBACK_FACES = [
  { score: 1, icon: '😞', title: 'Совсем плохо (1/5)' },
  { score: 2, icon: '😕', title: 'Неточно (2/5)' },
  { score: 3, icon: '😐', title: 'Нормально (3/5)' },
  { score: 4, icon: '🙂', title: 'Хорошо (4/5)' },
  { score: 5, icon: '😄', title: 'Отлично (5/5)' },
];

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export class Chat {
  constructor(containerElement) {
    this.container = containerElement;
    this.emptyMascot = null;
    this.activeUnsubscribe = null;
    this.burnTimers = new Map();

    this.render();
    this.attachEvents();

    store.subscribe('messages:updated', () => this.renderMessages());
    store.subscribe('session:switched', () => this.renderMessages());
    store.subscribe('selectedPills:updated', () => this.renderSelectedPills());
    store.subscribe('user:updated', () => this.renderMessages());
    store.subscribe('depth:changed', () => this.renderDepthButtons());
    store.subscribe('reportNews:updated', () => this.renderReportNewsBanner());
    store.subscribe('mascot:stateChanged', (state) => this.handleMascotState(state));
  }

  handleMascotState(state) {
    if (this.emptyMascot) this.emptyMascot.setState(state);
  }

  renderDepthButtons() {
    const depth = store.getState().responseDepth;
    this.container.querySelectorAll('.chat-depth-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.depth === depth);
    });
  }

  renderReportNewsBanner() {
    const banner = this.container.querySelector('#chatReportNewsBanner');
    if (!banner) return;
    const news = store.getState().reportNews || [];
    if (!news.length) {
      banner.style.display = 'none';
      banner.innerHTML = '';
      return;
    }
    banner.style.display = 'flex';
    banner.innerHTML = `
      <div>
        <strong>Администратор проверил вашу жалобу</strong>
        <span>(по диалогу «${escapeHtml(news[0].dialog_title || 'Консультация')}», всего уведомлений: ${news.length})</span>
      </div>
      <button id="dismissReportNewsBtn" class="msg-action-btn">Понятно</button>
    `;
    banner.querySelector('#dismissReportNewsBtn')?.addEventListener('click', async () => {
      const ids = news.map((n) => n.report_id);
      store.setReportNews([]);
      await dialogsApi.markReportNewsSeen(ids);
    });
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

    this.container.querySelectorAll('.chat-depth-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        store.setResponseDepth(btn.dataset.depth);
      });
    });
  }

  async sendPromptText(promptText) {
    const input = this.container.querySelector('#chatTextarea');
    if (input) {
      input.value = promptText;
      input.dispatchEvent(new Event('input'));
    }
    await this.handleSendMessage();
  }

  async handleSendMessage() {
    const input = this.container.querySelector('#chatTextarea');
    const text = input ? input.value.trim() : '';
    const state = store.getState();
    const selectedPills = [...state.selectedPills];
    const queryText = text || 'Посоветуйте применение для выбранных препаратов';

    if (!text && !selectedPills.length) return;

    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }
    const sendBtn = this.container.querySelector('#chatSendBtn');
    if (sendBtn) sendBtn.disabled = true;

    store.addMessageToActiveSession({
      id: `msg_${Date.now()}`,
      sender: 'user',
      text: queryText,
      attachedPills: selectedPills
    });

    state.selectedPills = [];
    store.notify('selectedPills:updated', []);
    store.setMascotState('thinking');

    const isAuth = store.isAuthenticated();
    if (isAuth && typeof EventSource !== 'undefined') {
      const ok = await this.handleAuthenticatedSseQuery(queryText, selectedPills);
      if (ok) return;
    }

    await this.handleStatelessFallbackQuery(queryText, selectedPills);
  }

  async handleAuthenticatedSseQuery(queryText, selectedPills) {
    const state = store.getState();
    let session = state.sessions.find((s) => s.id === state.activeSessionId);
    if (!session) return false;

    if (!session.serverBacked) {
      const created = await dialogsApi.createDialog(queryText.slice(0, 48));
      if (!created || !created.dialog_id || created._fallback || created._status >= 400) {
        return false;
      }
      store.replaceSessionId(session.id, created.dialog_id, queryText.slice(0, 36));
      session = store.getState().sessions.find((s) => s.id === created.dialog_id);
    }

    const dialogId = session.id;
    const botTempId = `msg_${Date.now()}_bot`;
    store.addMessageToActiveSession({
      id: botTempId,
      sender: 'bot',
      isEmergency: false,
      streaming: true,
      text: '',
      data: { message: '' }
    });

    if (this.activeUnsubscribe) {
      this.activeUnsubscribe();
      this.activeUnsubscribe = null;
    }

    return new Promise((resolve) => {
      let settled = false;
      const finish = (success) => {
        if (settled) return;
        settled = true;
        if (this.activeUnsubscribe) {
          this.activeUnsubscribe();
          this.activeUnsubscribe = null;
        }
        const sendBtn = this.container.querySelector('#chatSendBtn');
        if (sendBtn) sendBtn.disabled = false;
        resolve(success);
      };

      const timeoutId = setTimeout(() => {
        finish(true);
      }, 35000);

      this.activeUnsubscribe = dialogsApi.subscribeEvents(dialogId, {
        onReady: async () => {
          const accepted = await dialogsApi.sendMessage(dialogId, {
            content: queryText,
            include_kit_context: true,
            selected_pills: selectedPills.map((p) => p.name),
            response_depth: store.getState().responseDepth,
          });
          if (accepted._fallback || accepted._status >= 400) {
            clearTimeout(timeoutId);
            finish(false);
          }
        },
        onDelta: (evt) => {
          const delta = evt.delta || '';
          if (!delta) return;
          store.updateMessageInSession(dialogId, botTempId, (cur) => ({
            ...cur,
            text: (cur.text || '') + delta,
            data: { ...(cur.data || {}), message: ((cur.data && cur.data.message) || '') + delta },
          }));
        },
        onEnd: (evt) => {
          clearTimeout(timeoutId);
          const isEmerg = Boolean(evt.emergency_mode);
          store.setMascotState(isEmerg ? 'emergency' : 'idle');
          store.updateMessageInSession(dialogId, botTempId, (cur) => ({
            ...cur,
            id: evt.message_id || botTempId,
            serverMessageId: evt.message_id || null,
            dialogId,
            streaming: false,
            isEmergency: isEmerg,
            data: {
              ...(cur.data || {}),
              message: (cur.data && cur.data.message) || cur.text || 'Ответ сформирован.',
              emergency_mode: isEmerg,
              first_aid_steps: evt.first_aid_steps || [],
              recommendation: evt.recommendation || null,
              safety_warnings: evt.safety_warnings || [],
              sources: evt.sources || [],
              used_llm: Boolean(evt.used_llm),
            },
          }));
          finish(true);
        },
        onError: (evt) => {
          clearTimeout(timeoutId);
          store.setMascotState('idle');
          store.updateMessageInSession(dialogId, botTempId, (cur) => ({
            ...cur,
            streaming: false,
            data: { message: evt.message || 'Ошибка генерации ответа.' },
          }));
          finish(true);
        },
        onStreamError: () => {
          clearTimeout(timeoutId);
          store.setMascotState('idle');
          finish(true);
        },
      });
    });
  }

  async handleStatelessFallbackQuery(queryText, selectedPills) {
    const state = store.getState();
    try {
      const response = await chatApi.sendQuery(queryText, {
        include_kit_context: true,
        user_kit_names: (state.kitItems || []).map((i) => i.name),
        selected_pills: selectedPills.map((p) => p.name),
        health_profile: state.healthProfile,
        response_depth: state.responseDepth,
      });

      if (response && response.emergency_mode) {
        store.setMascotState('emergency');
        store.addMessageToActiveSession({
          id: `msg_${Date.now()}_bot`,
          sender: 'bot',
          isEmergency: true,
          data: response
        });
        return;
      }

      store.setMascotState('idle');
      store.addMessageToActiveSession({
        id: `msg_${Date.now()}_bot`,
        sender: 'bot',
        isEmergency: false,
        data: response && !response._error ? response : { message: response?._error || 'Запрос успешно обработан.' }
      });
    } catch {
      store.setMascotState('idle');
      store.addMessageToActiveSession({
        id: `msg_${Date.now()}_bot`,
        sender: 'bot',
        isEmergency: false,
        data: { message: 'Произошла ошибка при обращении к сервису. Повторите запрос.' }
      });
    } finally {
      store.setMascotState('idle');
      const sendBtn = this.container.querySelector('#chatSendBtn');
      if (sendBtn) sendBtn.disabled = false;
    }
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
        <span>${escapeHtml(p.name)} (${escapeHtml(p.dosage)})</span>
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

  speakRussianText(btn, text) {
    if (!text) return;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = 'ru-RU';
      utter.rate = 1.02;
      btn.classList.add('active');
      utter.onend = () => btn.classList.remove('active');
      utter.onerror = () => btn.classList.remove('active');
      window.speechSynthesis.speak(utter);
    }
  }

  openReportDialog(sessionId, msg) {
    const reason = window.prompt(
      'Укажите причину жалобы на ответ:\n(inaccurate / unsafe / unhelpful / other)',
      'inaccurate'
    );
    if (!reason) return;
    const comment = window.prompt('Комментарий к жалобе (необязательно):', '') || null;
    if (store.isAuthenticated() && msg.serverMessageId) {
      dialogsApi.reportMessage(sessionId, msg.serverMessageId, reason.trim(), comment).then((res) => {
        store.updateMessageInSession(sessionId, msg.id, { reported: true });
        if (res && res._error) alert(`Ошибка отправки жалобы: ${res._error}`);
      });
    } else {
      store.updateMessageInSession(sessionId, msg.id, { reported: true });
    }
  }

  renderMessages() {
    const list = this.container.querySelector('#chatMessagesList');
    if (!list) return;

    const state = store.getState();
    const session = state.sessions.find(s => s.id === state.activeSessionId);
    const messages = session ? session.messages : [];
    const userName = (state.user && state.user.name && state.user.role !== 'guest') ? state.user.name : 'друг';

    if (!messages.length) {
      list.className = 'chat-messages-container empty';
      list.innerHTML = `
        <div class="chat-empty-state">
          <div class="empty-mascot-wrapper" id="emptyMascotMount"></div>
          <h2 class="empty-state-greeting">Чем могу помочь сегодня, ${escapeHtml(userName)}?</h2>
          <p style="font-size: 13.5px; color: var(--text-muted); max-width: 520px; text-align: center; margin-top: 4px;">
            Учитываю состав вашей домашней аптечки, возраст, аллергии и хронические заболевания.
          </p>
          <div class="chat-chips-row">
            ${QUICK_PROMPT_CHIPS.map((c, idx) => `
              <button type="button" class="chat-prompt-chip tap-effect" data-chip-idx="${idx}">
                ${escapeHtml(c.label)}
              </button>
            `).join('')}
          </div>
        </div>
      `;

      const mount = list.querySelector('#emptyMascotMount');
      if (mount) {
        this.emptyMascot = new Mascot(mount);
      }
      list.querySelectorAll('.chat-prompt-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          const chip = QUICK_PROMPT_CHIPS[Number(btn.dataset.chipIdx)];
          if (chip) this.sendPromptText(chip.query);
        });
      });
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
                  Выбранные препараты: ${msg.attachedPills.map(p => escapeHtml(p.name)).join(', ')}
                </div>
              ` : ''}
              ${escapeHtml(msg.text)}
            </div>
          </div>
        `;
      }

      const data = msg.data || {};
      const fullPlainText = data.message || msg.text || '';

      if (msg.isEmergency) {
        const isBurn = /ожог|кипят|плам/i.test(fullPlainText) || (data.first_aid_steps || []).some((s) => /охлад|водой/i.test(s));
        return `
          <div class="message-row bot" data-msg-id="${msg.id}">
            <div class="message-bubble">
              <div class="emergency-card">
                <div class="emergency-header">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                  <span>ПРОТОКОЛ НЕОТЛОЖНОЙ ПОМОЩИ (RED FLAG)</span>
                </div>
                <p style="font-weight: 600; font-size: 14.5px; color: #181C20; margin-bottom: 12px;">
                  ${escapeHtml(data.message)}
                </p>
                <div style="font-size: 13.5px; color: #374151; line-height: 1.6;">
                  ${(data.first_aid_steps || []).map(s => `<div>• ${escapeHtml(s)}</div>`).join('')}
                </div>
                ${isBurn ? `
                  <div class="emergency-timer-box">
                    <div style="font-size: 12.5px; font-weight: 600; color: #B91C1C;">
                      Таймер охлаждения ожога: <span class="burn-timer-display" data-msg-id="${msg.id}">15:00</span>
                    </div>
                    <button type="button" class="msg-action-btn burn-timer-start" data-msg-id="${msg.id}">Запустить 15 мин</button>
                  </div>
                ` : ''}
                <a href="tel:112" class="emergency-call-btn tap-effect">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
                  Вызвать скорую помощь (112)
                </a>
              </div>
            </div>
          </div>
        `;
      }

      const rec = data.recommendation || null;
      const warnings = Array.isArray(data.safety_warnings) ? data.safety_warnings : [];
      const actionsToolbar = msg.streaming ? '' : `
        <div class="bot-msg-actions">
          <button type="button" class="msg-action-btn msg-copy-btn" data-msg-id="${msg.id}">Копировать</button>
          <button type="button" class="msg-action-btn msg-tts-btn" data-msg-id="${msg.id}">Озвучить</button>
          <button type="button" class="msg-action-btn msg-report-btn ${msg.reported ? 'active' : ''}" data-msg-id="${msg.id}">
            ${msg.reported ? 'Жалоба отправлена' : 'Пожаловаться'}
          </button>
          <div class="msg-rating-bar">
            ${FEEDBACK_FACES.map(f => `
              <button type="button" class="msg-face-btn ${msg.feedback === f.score ? 'active' : ''}" data-msg-id="${msg.id}" data-score="${f.score}" title="${f.title}">${f.icon}</button>
            `).join('')}
          </div>
        </div>
      `;

      if (!rec || !rec.medicine_name) {
        return `
          <div class="message-row bot" data-msg-id="${msg.id}">
            <div class="message-bubble">
              <div style="font-size: 14.5px; line-height: 1.6; color: #181C20; white-space: pre-wrap;">${escapeHtml(fullPlainText || 'Обрабатываю запрос...')}${msg.streaming ? '<span class="streaming-cursor"></span>' : ''}</div>
              ${warnings.length ? `<div class="rag-safety-alert" style="margin-top: 8px;">${warnings.map(w => `<div>⚠️ ${escapeHtml(w)}</div>`).join('')}</div>` : ''}
              ${data.disclaimer ? `<div style="font-size: 11px; margin-top: 8px; opacity: 0.8; color: #6B7280;">${escapeHtml(data.disclaimer)}</div>` : ''}
              ${actionsToolbar}
            </div>
          </div>
        `;
      }

      return `
        <div class="message-row bot" data-msg-id="${msg.id}">
          <div class="message-bubble">
            <div class="rag-card">
              <div class="rag-card-header">
                <span class="rag-med-title">${escapeHtml(rec.medicine_name)}</span>
                <span class="rag-kit-badge ${rec.in_user_kit ? 'in-kit' : 'out-kit'}">
                  ${rec.in_user_kit ? '✓ Есть в вашей аптечке' : '✕ Нет в наличии'}
                </span>
              </div>

              ${warnings.length ? `
                <div class="rag-safety-alert">
                  ${warnings.map(w => `<div>⚠️ ${escapeHtml(w)}</div>`).join('')}
                </div>
              ` : ''}

              ${fullPlainText ? `
                <div class="rag-section">
                  <div class="rag-section-title">Рекомендация ассистента ${data.used_llm ? '· LLM' : ''}</div>
                  <div class="rag-section-text" style="white-space: pre-wrap;">${escapeHtml(fullPlainText)}</div>
                </div>
              ` : ''}

              <div class="rag-section">
                <div class="rag-section-title">Режим дозирования</div>
                <div class="rag-section-text">${escapeHtml(rec.dosage)}</div>
              </div>

              <div class="rag-section">
                <div class="rag-section-title">Противопоказания и предупреждения</div>
                <div class="rag-section-text" style="color: #4B5563;">
                  ${escapeHtml(rec.contraindications)}<br/>
                  <span style="font-weight: 600; color: #D97008; margin-top: 4px; display: inline-block;">
                    Предупреждение: ${escapeHtml(rec.warnings)}
                  </span>
                </div>
              </div>

              <div class="rag-meta-footer">
                <div>Источник: ${data.sources && data.sources.length ? escapeHtml(data.sources[0].title) : 'Официальная инструкция Минздрава РФ'}</div>
                <div style="font-size: 11px; margin-top: 4px; opacity: 0.8;">${escapeHtml(data.disclaimer || '')}</div>
              </div>

              ${actionsToolbar}
            </div>
          </div>
        </div>
      `;
    }).join('');

    this.bindMessageActions(list, session ? session.id : null, messages);
    list.scrollTop = list.scrollHeight;
  }

  bindMessageActions(list, sessionId, messages) {
    const findMsg = (id) => messages.find((m) => m.id === id);

    list.querySelectorAll('.msg-copy-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const msg = findMsg(btn.dataset.msgId);
        if (!msg) return;
        const d = msg.data || {};
        const rec = d.recommendation;
        const copyText = [
          d.message || msg.text,
          rec ? `${rec.medicine_name}: ${rec.dosage}` : '',
        ].filter(Boolean).join('\n\n');
        navigator.clipboard?.writeText(copyText).then(() => {
          btn.textContent = 'Скопировано ✓';
          setTimeout(() => { btn.textContent = 'Копировать'; }, 1400);
        }).catch(() => {});
      });
    });

    list.querySelectorAll('.msg-tts-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const msg = findMsg(btn.dataset.msgId);
        if (!msg) return;
        const textToRead = (msg.data && msg.data.message) || msg.text || '';
        if (store.isAuthenticated() && sessionId && msg.serverMessageId) {
          const res = await dialogsApi.requestAudio(sessionId, msg.serverMessageId, store.getState().voice);
          if (res && !res._fallback && !res._error && res.audio_url) {
            const audio = new Audio(res.audio_url);
            audio.play().catch(() => this.speakRussianText(btn, textToRead));
            return;
          }
        }
        this.speakRussianText(btn, textToRead);
      });
    });

    list.querySelectorAll('.msg-report-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const msg = findMsg(btn.dataset.msgId);
        if (msg && sessionId) this.openReportDialog(sessionId, msg);
      });
    });

    list.querySelectorAll('.msg-face-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const msg = findMsg(btn.dataset.msgId);
        const score = Number(btn.dataset.score);
        if (!msg || !sessionId) return;
        const nextScore = msg.feedback === score ? null : score;
        store.updateMessageInSession(sessionId, msg.id, { feedback: nextScore });
        if (store.isAuthenticated() && msg.serverMessageId) {
          if (nextScore === null) {
            await dialogsApi.deleteFeedback(sessionId, msg.serverMessageId);
          } else {
            await dialogsApi.setFeedback(sessionId, msg.serverMessageId, nextScore);
          }
        }
      });
    });

    list.querySelectorAll('.burn-timer-start').forEach((btn) => {
      btn.addEventListener('click', () => {
        const msgId = btn.dataset.msgId;
        if (this.burnTimers.has(msgId)) return;
        let remaining = 15 * 60;
        btn.disabled = true;
        btn.textContent = 'Идёт отсчёт...';
        const display = list.querySelector(`.burn-timer-display[data-msg-id="${msgId}"]`);
        const timer = setInterval(() => {
          remaining -= 1;
          if (display) {
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            display.textContent = `${m}:${s}`;
          }
          if (remaining <= 0) {
            clearInterval(timer);
            this.burnTimers.delete(msgId);
            if (display) display.textContent = '00:00 (Готово)';
            btn.textContent = 'Завершено';
          }
        }, 1000);
        this.burnTimers.set(msgId, timer);
      });
    });
  }

  render() {
    const depth = store.getState().responseDepth;
    this.container.innerHTML = `
      <div class="chat-view-wrap">
        <div id="chatReportNewsBanner" class="chat-report-news-banner" style="display: none;"></div>
        <!-- Лента сообщений -->
        <div class="chat-messages-container" id="chatMessagesList"></div>

        <!-- Зона ввода сообщения -->
        <div class="chat-input-area">
          <div class="chat-composer-meta">
            <span style="font-size: 11.5px; color: var(--text-muted);">
              Глубина ответа:
            </span>
            <div class="chat-depth-switcher">
              <button type="button" class="chat-depth-btn ${depth === 'brief' ? 'active' : ''}" data-depth="brief">Кратко</button>
              <button type="button" class="chat-depth-btn ${depth === 'detailed' ? 'active' : ''}" data-depth="detailed">Подробно</button>
            </div>
          </div>

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
    this.renderReportNewsBanner();
  }
}
