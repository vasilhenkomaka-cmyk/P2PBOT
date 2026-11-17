const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Theme
document.documentElement.style.setProperty('--bg', tg.themeParams.bg_color || '#0f0f0f');
document.documentElement.style.setProperty('--text', tg.themeParams.text_color || '#ffffff');
document.documentElement.style.setProperty('--hint', tg.themeParams.hint_color || '#8a8a8a');
document.documentElement.style.setProperty('--button', tg.themeParams.button_color || '#2ea6ff');
document.documentElement.style.setProperty('--button-text', tg.themeParams.button_text_color || '#ffffff');
document.documentElement.style.setProperty('--secondary', tg.themeParams.secondary_bg_color || '#1c1c1e');

// User ID from Telegram
const userId = tg.initDataUnsafe?.user?.id;
if (!userId) {
  document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#888">Відкрий додаток через бота в Telegram</div>';
}

const API = window.location.origin;

// ---------- Helpers ----------
function fmt(n, digits = 2) {
  return Number(n).toLocaleString('uk-UA', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtMoney(n) {
  return fmt(n) + ' ₴';
}

function fmtUsdt(n) {
  return fmt(n) + ' USDT';
}

function dealTypeLabel(t) {
  return t === 'buy' ? '🟢 Купівля' : '🔴 Продаж';
}

// ---------- Tabs ----------
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');

    if (btn.dataset.tab === 'today') loadToday();
    if (btn.dataset.tab === 'stats') loadStats();
    if (btn.dataset.tab === 'history') loadHistory();
  });
});

// ---------- Type switch ----------
let currentType = 'buy';
document.querySelectorAll('.type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentType = btn.dataset.type;
    updatePreview();
  });
});

// ---------- Preview ----------
const rateInput = document.getElementById('rate');
const amountInput = document.getElementById('amount');
const feeInput = document.getElementById('fee');

[rateInput, amountInput, feeInput].forEach(el => {
  el.addEventListener('input', updatePreview);
});

function updatePreview() {
  const rate = parseFloat(rateInput.value) || 0;
  const amount = parseFloat(amountInput.value) || 0;
  const fee = parseFloat(feeInput.value) || 0;
  const gross = rate * amount;
  const net = currentType === 'buy'
    ? gross * (1 + fee / 100)
    : gross * (1 - fee / 100);
  const label = currentType === 'buy' ? 'Сплатиш' : 'Отримаєш';
  document.getElementById('preview').textContent = `${label}: ${fmtMoney(net)}`;
}

// ---------- Submit ----------
document.getElementById('dealForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Збереження...';

  const payload = {
    user_id: userId,
    deal_type: currentType,
    rate: parseFloat(rateInput.value),
    amount_usdt: parseFloat(amountInput.value),
    fee_percent: parseFloat(feeInput.value) || 0,
    note: document.getElementById('note').value.trim()
  };

  try {
    const res = await fetch(`${API}/api/deals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.ok) {
      tg.HapticFeedback?.notificationOccurred('success');
      tg.showAlert('Угоду збережено!');
      // reset form
      rateInput.value = '';
      amountInput.value = '';
      feeInput.value = '0';
      document.getElementById('note').value = '';
      updatePreview();
      // switch to today
      document.querySelector('.tab[data-tab="today"]').click();
    } else {
      throw new Error('Помилка');
    }
  } catch (err) {
    tg.showAlert('Не вдалося зберегти. Спробуй ще раз.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Зберегти угоду';
  }
});

// ---------- Load data ----------
async function loadToday() {
  try {
    const [statsRes, dealsRes] = await Promise.all([
      fetch(`${API}/api/stats?user_id=${userId}&today=true`),
      fetch(`${API}/api/deals/today?user_id=${userId}`)
    ]);
    const stats = await statsRes.json();
    const { deals } = await dealsRes.json();

    document.getElementById('todayProfit').textContent = fmtMoney(stats.profit);
    document.getElementById('todayDeals').textContent = stats.total_deals;
    document.getElementById('todayBuy').textContent = fmtUsdt(stats.buy_usdt);
    document.getElementById('todaySell').textContent = fmtUsdt(stats.sell_usdt);
    document.getElementById('balanceBadge').textContent = fmt(stats.balance_usdt) + ' USDT';

    const list = document.getElementById('todayList');
    if (!deals.length) {
      list.innerHTML = '<div class="empty">Поки немає угод сьогодні</div>';
      return;
    }
    list.innerHTML = deals.map(d => dealItem(d)).join('');
  } catch (e) {
    console.error(e);
  }
}

async function loadStats() {
  try {
    const res = await fetch(`${API}/api/stats?user_id=${userId}`);
    const s = await res.json();
    document.getElementById('totalProfit').textContent = fmtMoney(s.profit);
    document.getElementById('totalDeals').textContent = s.total_deals;
    document.getElementById('totalBalance').textContent = fmt(s.balance_usdt);
    document.getElementById('avgBuy').textContent = s.avg_buy ? s.avg_buy.toFixed(2) : '—';
    document.getElementById('avgSell').textContent = s.avg_sell ? s.avg_sell.toFixed(2) : '—';
    document.getElementById('spread').textContent = (s.avg_sell && s.avg_buy)
      ? (s.avg_sell - s.avg_buy).toFixed(2)
      : '—';
    document.getElementById('balanceBadge').textContent = fmt(s.balance_usdt) + ' USDT';
  } catch (e) {
    console.error(e);
  }
}

async function loadHistory() {
  try {
    const res = await fetch(`${API}/api/deals?user_id=${userId}&limit=40`);
    const { deals } = await res.json();
    const list = document.getElementById('historyList');
    if (!deals.length) {
      list.innerHTML = '<div class="empty">Історія порожня</div>';
      return;
    }
    list.innerHTML = deals.map(d => dealItem(d, true)).join('');
  } catch (e) {
    console.error(e);
  }
}

function dealItem(d, withDelete = false) {
  const dt = new Date(d.created_at);
  const time = dt.toLocaleString('uk-UA', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  const sum = d.amount_usdt * d.rate;
  return `
    <div class="deal-item">
      <div class="deal-left">
        <div class="deal-type ${d.deal_type}">${dealTypeLabel(d.deal_type)}</div>
        <div class="deal-meta">${time}${d.note ? ' · ' + d.note : ''}</div>
      </div>
      <div class="deal-right">
        <div class="deal-amount">${fmt(d.amount_usdt)} @ ${d.rate}</div>
        <div class="deal-sum">${fmtMoney(sum)}</div>
      </div>
      ${withDelete ? `<button class="btn-delete" onclick="deleteDeal(${d.id})">✕</button>` : ''}
    </div>
  `;
}

async function deleteDeal(id) {
  if (!confirm('Видалити угоду?')) return;
  try {
    await fetch(`${API}/api/deals/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, deal_id: id })
    });
    loadHistory();
    loadToday();
    tg.HapticFeedback?.notificationOccurred('success');
  } catch (e) {
    tg.showAlert('Помилка видалення');
  }
}

// Initial load
if (userId) {
  loadToday();
}
