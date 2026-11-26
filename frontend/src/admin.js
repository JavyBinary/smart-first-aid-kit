import { AmbientBackground } from './components/AmbientBackground.js';
import { authApi } from './api/auth.api.js';
import { adminApi } from './api/admin.api.js';

function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function getTimeGreeting(name) {
  const hour = new Date().getHours();
  let prefix = 'Добрый вечер';
  if (hour >= 5 && hour < 12) prefix = 'Доброе утро';
  else if (hour >= 12 && hour < 18) prefix = 'Добрый день';
  else if (hour >= 0 && hour < 5) prefix = 'Доброй ночи';
  return `${prefix}, ${name || 'Администратор'}`;
}

function clearLocalSession() {
  localStorage.removeItem('medai_token');
  localStorage.removeItem('medai_user');
  localStorage.removeItem('medai_name');
  localStorage.removeItem('medai_role');
  localStorage.removeItem('medai_avatar');
}

document.addEventListener('DOMContentLoaded', async () => {
  const canvas = document.getElementById('ambientCanvas');
  if (canvas) new AmbientBackground(canvas);

  const garlandBulbs = document.getElementById('garlandBulbs');
  if (garlandBulbs) {
    const colors = ['#FF3B30', '#FFB300', '#00B074', '#4EA8DE', '#AF52DE', '#FF9500'];
    for (let i = 0; i < 32; i++) {
      const node = document.createElement('div');
      node.className = 'garland-bulb-node';
      const col = colors[i % colors.length];
      node.innerHTML = `
        <div class="garland-bulb-socket"></div>
        <div class="garland-bulb-lamp" style="background: ${col}; color: ${col}; animation-delay: ${(i * 0.12) % 1.8}s;"></div>
      `;
      garlandBulbs.appendChild(node);
    }
  }

  document.getElementById('adminLogoutBtn')?.addEventListener('click', async () => {
    await authApi.logout();
    clearLocalSession();
    window.location.href = 'login.html';
  });

  // Проверка реальной cookie-сессии и прав администратора
  const me = await authApi.getMe();
  if (!me || !me.id) {
    window.location.href = 'login.html';
    return;
  }
  if (me.role !== 'admin' && me.role !== 'superadmin') {
    document.body.innerHTML = `
      <div style="max-width:480px;margin:80px auto;padding:28px;background:#fff;border-radius:16px;text-align:center;font-family:system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,0.08);">
        <h2 style="color:#B91C1C;">Доступ ограничен (403)</h2>
        <p style="color:#4B5563;margin:12px 0;">Панель администратора доступна только пользователям с ролью <b>admin</b> или <b>superadmin</b>.</p>
        <a href="index.html" style="display:inline-block;padding:10px 20px;background:#00A86B;color:#fff;border-radius:999px;text-decoration:none;font-weight:600;">Вернуться в приложение</a>
      </div>
    `;
    return;
  }

  document.getElementById('adminGreetingTitle').textContent = getTimeGreeting(me.name);
  document.getElementById('adminRoleBadge').textContent = me.role === 'superadmin' ? 'Superadmin' : 'Admin';

  // Вкладки
  const tabs = {
    catalog: [document.getElementById('tabAdminCatalog'), document.getElementById('adminCatalogSection')],
    users: [document.getElementById('tabAdminUsers'), document.getElementById('adminUsersSection')],
    reports: [document.getElementById('tabAdminReports'), document.getElementById('adminReportsSection')],
    rag: [document.getElementById('tabAdminRAG'), document.getElementById('adminRAGSection')],
  };

  function switchAdminTab(target) {
    Object.entries(tabs).forEach(([key, [btn, sec]]) => {
      if (btn) btn.classList.toggle('active', key === target);
      if (sec) sec.style.display = key === target ? 'block' : 'none';
    });
  }

  tabs.catalog[0]?.addEventListener('click', () => switchAdminTab('catalog'));
  tabs.users[0]?.addEventListener('click', () => switchAdminTab('users'));
  tabs.reports[0]?.addEventListener('click', async () => {
    switchAdminTab('reports');
    await loadReports(currentReportFilter);
  });
  tabs.rag[0]?.addEventListener('click', async () => {
    switchAdminTab('rag');
    await runLiveBenchmark();
  });

  let medicines = [];
  let usersList = [];
  let currentReportFilter = 'new';

  function renderStats(stats) {
    if (!stats || stats._error || stats._fallback) return;
    document.getElementById('totalMedsStat').textContent = stats.medicines_count ?? medicines.length;
    document.getElementById('totalUsersStat').textContent = stats.users_total ?? 0;
    document.getElementById('totalUsersSub').textContent = `Пользователей (акт: ${stats.active_users ?? 0}, новых: ${stats.new_users ?? 0})`;
    document.getElementById('totalDialogsStat').textContent = stats.dialogs ?? 0;
    document.getElementById('totalMessagesSub').textContent = `Диалогов (сообщений: ${stats.messages ?? 0})`;
    document.getElementById('openReportsStat').textContent = stats.reports_new ?? 0;

    // График активности диалогов
    const chartEl = document.getElementById('adminActivityChart');
    if (chartEl) {
      const points = Array.isArray(stats.activity) ? stats.activity : [];
      const maxVal = Math.max(1, ...points.map((p) => p.dialogs || 0));
      chartEl.innerHTML = points.length
        ? points.map((p) => {
          const h = Math.max(6, Math.round(((p.dialogs || 0) / maxVal) * 76));
          const dt = String(p.start || '').slice(5, 10);
          return `<div title="${dt}: ${p.dialogs}" style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;"><div style="width:100%;max-width:18px;height:${h}px;background:#00B074;border-radius:4px 4px 0 0;opacity:${p.dialogs ? 1 : 0.25};"></div><span style="font-size:10px;color:#6B7280;">${dt}</span></div>`;
        }).join('')
        : '<div style="color:#6B7280;font-size:12px;">Нет активности за выбранный период</div>';
    }

    // Гистограмма оценок (5..1)
    const fbEl = document.getElementById('adminFeedbackBars');
    if (fbEl && stats.feedback) {
      const counts = stats.feedback.counts || [0, 0, 0, 0, 0];
      const maxCnt = Math.max(1, ...counts);
      fbEl.innerHTML = [5, 4, 3, 2, 1].map((score) => {
        const cnt = counts[score - 1] || 0;
        const pct = Math.round((cnt / maxCnt) * 100);
        return `
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="width:24px;font-weight:700;">${score}★</span>
            <div style="flex:1;height:8px;background:#F1F5F9;border-radius:999px;overflow:hidden;">
              <div style="width:${pct}%;height:100%;background:${score >= 4 ? '#00B074' : score === 3 ? '#F59E0B' : '#EF4444'};"></div>
            </div>
            <span style="width:28px;text-align:right;color:#4B5563;">${cnt}</span>
          </div>
        `;
      }).join('');
    }
  }

  function renderMedicines() {
    const tbody = document.getElementById('adminCatalogTableBody');
    const q = (document.getElementById('adminCatalogSearch')?.value || '').trim().toLowerCase();
    const filtered = medicines.filter((m) =>
      !q || m.title.toLowerCase().includes(q) || m.inn.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
    );
    tbody.innerHTML = filtered.map((m) => `
      <tr>
        <td><strong>${escapeHtml(m.id)} · ${escapeHtml(m.title)}</strong></td>
        <td>${escapeHtml(m.inn)}<br/><span style="font-size:11.5px;color:#6B7280;">${escapeHtml(m.atc_code)}</span></td>
        <td>${escapeHtml(m.category)}</td>
        <td style="font-size:12.5px;">${escapeHtml(m.dosage)}</td>
        <td style="font-size:12px;color:#6B7280;">${escapeHtml((m.contraindications || []).slice(0, 2).join(', ') || '—')}</td>
        <td style="text-align:right;">
          <button class="action-btn del del-med-btn" data-id="${escapeHtml(m.id)}">Удалить</button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="6" style="text-align:center;color:#6B7280;">Документы не найдены</td></tr>';

    tbody.querySelectorAll('.del-med-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const docId = btn.dataset.id;
        if (!window.confirm(`Удалить документ ${docId} из корпуса RAG?`)) return;
        const res = await adminApi.deleteMedicine(docId);
        if (!res._error && !res._fallback) {
          medicines = medicines.filter((x) => x.id !== docId);
          renderMedicines();
          await refreshStats();
        }
      });
    });
  }

  function renderUsers() {
    const tbody = document.getElementById('adminUsersTableBody');
    const q = (document.getElementById('adminUsersSearch')?.value || '').trim().toLowerCase();
    const filtered = usersList.filter((u) =>
      !q || (u.name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)
    );
    tbody.innerHTML = filtered.map((u) => `
      <tr>
        <td><strong>${escapeHtml(u.name)}</strong></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="role-badge ${escapeHtml(u.role)}">${escapeHtml(u.role)}</span></td>
        <td>${u.medcard_filled ? 'Заполнена ✓' : 'Пустая'}</td>
        <td>${u.kit_count ?? 0} преп. · ${u.dialogs ?? 0} диал.</td>
        <td style="text-align:right;">
          ${u.role === 'superadmin'
            ? '<span style="font-size:12px;color:#9CA3AF;">Superadmin защищён</span>'
            : `<button class="action-btn edit toggle-role-btn" data-id="${escapeHtml(u.id)}" data-role="${u.role === 'admin' ? 'user' : 'admin'}">${u.role === 'admin' ? 'Понизить до user' : 'Назначить admin'}</button>`}
        </td>
      </tr>
    `).join('') || '<tr><td colspan="6" style="text-align:center;color:#6B7280;">Пользователи не найдены</td></tr>';

    tbody.querySelectorAll('.toggle-role-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const userId = btn.dataset.id;
        const nextRole = btn.dataset.role;
        const updated = await adminApi.updateUserRole(userId, nextRole);
        if (updated && updated.id) {
          usersList = usersList.map((u) => (u.id === userId ? { ...u, role: updated.role } : u));
          renderUsers();
        } else {
          alert(updated?._error || 'Не удалось изменить роль');
        }
      });
    });
  }

  async function loadReports(statusFilter = 'new') {
    currentReportFilter = statusFilter;
    const res = await adminApi.getReports(statusFilter);
    const reports = Array.isArray(res?.reports) ? res.reports : [];
    const tbody = document.getElementById('adminReportsTableBody');
    tbody.innerHTML = reports.map((r) => `
      <tr>
        <td><strong>${escapeHtml(r.reason)}</strong>${r.comment ? `<br/><span style="font-size:12px;color:#6B7280;">${escapeHtml(r.comment)}</span>` : ''}</td>
        <td style="font-size:12.5px;">${escapeHtml(r.request_text)}</td>
        <td style="font-size:12.5px;max-width:300px;">${escapeHtml(r.answer_text)}</td>
        <td><span class="role-badge ${r.status === 'new' ? 'admin' : 'user'}">${escapeHtml(r.status)}</span></td>
        <td style="text-align:right;">
          ${r.status === 'new'
            ? `<button class="action-btn edit resolve-rep-btn" data-id="${r.id}" data-status="resolved">Решено</button>
               <button class="action-btn del dismiss-rep-btn" data-id="${r.id}" data-status="dismissed">Отклонить</button>`
            : '<span style="font-size:12px;color:#6B7280;">Обработана</span>'}
        </td>
      </tr>
    `).join('') || '<tr><td colspan="5" style="text-align:center;color:#6B7280;">Жалоб в этой категории нет</td></tr>';

    tbody.querySelectorAll('.resolve-rep-btn, .dismiss-rep-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await adminApi.updateReportStatus(btn.dataset.id, btn.dataset.status);
        await loadReports(currentReportFilter);
        await refreshStats();
      });
    });
  }

  async function runLiveBenchmark() {
    const dataset = document.getElementById('adminBenchDataset')?.value || 'extended';
    const tbody = document.getElementById('adminBenchmarkTableBody');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Запуск ablation-бенчмарка...</td></tr>';
    const res = await adminApi.getBenchmark(dataset);
    const rows = Array.isArray(res?.rows) ? res.rows : [];
    tbody.innerHTML = rows.map((r) => `
      <tr>
        <td><strong>${escapeHtml(r.mode.toUpperCase())}</strong></td>
        <td><strong>${r.mrr.toFixed(4)}</strong></td>
        <td>${r.recall_at_3.toFixed(4)}</td>
        <td>${r.recall_at_5.toFixed(4)}</td>
        <td>${r.context_precision.toFixed(4)}</td>
        <td style="color:#00875A;font-weight:700;">${r.accuracy.toFixed(4)}</td>
        <td>${r.correct_rejection_rate.toFixed(4)}</td>
        <td>${r.faithfulness.toFixed(4)}</td>
      </tr>
    `).join('') || '<tr><td colspan="8" style="text-align:center;color:#B91C1C;">Не удалось выполнить бенчмарк</td></tr>';
  }

  async function refreshStats() {
    const period = document.getElementById('adminPeriodSelect')?.value || '30';
    const stats = await adminApi.getStats(period);
    renderStats(stats);
    if (Array.isArray(stats?.recent_users)) {
      usersList = stats.recent_users;
      renderUsers();
    }
  }

  document.getElementById('adminPeriodSelect')?.addEventListener('change', refreshStats);
  document.getElementById('adminCatalogSearch')?.addEventListener('input', renderMedicines);
  document.getElementById('adminUsersSearch')?.addEventListener('input', renderUsers);
  document.getElementById('runBenchmarkBtn')?.addEventListener('click', runLiveBenchmark);

  document.querySelectorAll('.report-filter-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.report-filter-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      loadReports(btn.dataset.filter);
    });
  });

  // Модалка добавления документа в корпус RAG
  const medModal = document.getElementById('medicineModalOverlay');
  document.getElementById('openAddMedicineModalBtn')?.addEventListener('click', () => {
    document.getElementById('medicineModalForm')?.reset();
    document.getElementById('medFormId').value = `D${Math.max(21, medicines.length + 1)}`;
    medModal.style.display = 'flex';
  });
  document.getElementById('closeMedModalBtn')?.addEventListener('click', () => { medModal.style.display = 'none'; });
  document.getElementById('cancelMedModalBtn')?.addEventListener('click', () => { medModal.style.display = 'none'; });

  document.getElementById('medicineModalForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const doc = {
      id: document.getElementById('medFormId').value.trim(),
      title: document.getElementById('medFormName').value.trim(),
      inn: document.getElementById('medFormInn').value.trim(),
      atc_code: document.getElementById('medFormAtc').value.trim(),
      category: document.getElementById('medFormCategory').value.trim(),
      forms: document.getElementById('medFormForm').value.split(',').map((s) => s.trim()).filter(Boolean),
      indications: document.getElementById('medFormIndications').value.split(',').map((s) => s.trim()).filter(Boolean),
      contraindications: document.getElementById('medFormContraindications').value.split(',').map((s) => s.trim()).filter(Boolean),
      dosage: document.getElementById('medFormDosage').value.trim(),
      interactions: [],
      emergency_flags: [],
    };
    const saved = await adminApi.upsertMedicine(doc);
    if (saved && saved.id) {
      medicines = [saved, ...medicines.filter((m) => m.id !== saved.id)];
      renderMedicines();
      await refreshStats();
      medModal.style.display = 'none';
    } else {
      alert(saved?._error || 'Ошибка сохранения документа');
    }
  });

  // Первичная загрузка
  const [medsRes] = await Promise.all([
    adminApi.listMedicines(),
    refreshStats(),
  ]);
  if (Array.isArray(medsRes)) {
    medicines = medsRes;
    renderMedicines();
  }
});
