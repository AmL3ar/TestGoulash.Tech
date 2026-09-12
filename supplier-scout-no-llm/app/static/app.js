const form = document.querySelector('#searchForm');
const results = document.querySelector('#results');
const loading = document.querySelector('#loading');
const summary = document.querySelector('#summary');
const modeInfo = document.querySelector('#modeInfo');
const favoritesButton = document.querySelector('#favoritesButton');
const exportCsvButton = document.querySelector('#exportCsv');
const exportXlsxButton = document.querySelector('#exportXlsx');
const compareBar = document.querySelector('#compareBar');
const compareCount = document.querySelector('#compareCount');
const openCompareButton = document.querySelector('#openCompare');
const clearCompareButton = document.querySelector('#clearCompare');
const noteDialog = document.querySelector('#noteDialog');
const noteForm = document.querySelector('#noteForm');
const noteText = document.querySelector('#noteText');
const noteSupplierName = document.querySelector('#noteSupplierName');
const compareDialog = document.querySelector('#compareDialog');
const compareContent = document.querySelector('#compareContent');
const escapeHtml = (value = '') =>
  String(value).replace(
    /[&<>'"]/g,
    char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[char])
  );
let suppliers = [];
let noteSupplierId = null;
let onlyFavorites = false;
let favorites = new Set(JSON.parse(localStorage.getItem('supplier-favorites') || '[]'));
let compare = new Set();

function checkedDate(value) {
  if (!value) {
    return 'не указана';
  }
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(new Date(value));
}

function saveFavorites() {
  localStorage.setItem('supplier-favorites', JSON.stringify([...favorites]));
}

function card(s, rank) {
  const reasons = s.score_reasons.map(reason => `<span class="reason">${escapeHtml(reason)}</span>`).join('');
  const favorite = favorites.has(s.id);
  const compared = compare.has(s.id);
  return `<article class="supplier" data-id="${s.id}">
    <div class="supplier-top">
      <div class="score">${Math.round(s.score)}</div>
      <div class="supplier-title"><div class="sub">№${rank} · ${escapeHtml(s.category)}</div><h3>${escapeHtml(s.name)}</h3><div class="sub">${escapeHtml(s.city)} · ${escapeHtml(s.region)}</div></div>
      <button class="icon-button favorite ${favorite ? 'active' : ''}" data-action="favorite" data-id="${s.id}" type="button" title="Избранное">${favorite ? '★' : '☆'}</button>
    </div>
    <div class="reasons">${reasons}</div>
    <div class="supplier-grid">
      <div class="fact"><span>Контакты</span><b>${escapeHtml(s.contact || 'не найдены')}</b></div>
      <div class="fact"><span>MOQ</span><b>${escapeHtml(s.min_order || 'уточнить')}</b></div>
      <div class="fact"><span>Цена</span><b>${escapeHtml(s.price_hint || 'нет публичной')}</b></div>
      <div class="fact"><span>Доставка</span><b>${escapeHtml(s.delivery || 'уточнить')}</b></div>
      <div class="fact"><span>Документы</span><b>${escapeHtml(s.certificates || 'уточнить')}</b></div>
      <div class="fact"><span>Проверка источника</span><b>${checkedDate(s.source_checked_at)}</b></div>
    </div>
    <div class="note-preview"><span>Заметка</span><p>${escapeHtml(s.notes || 'Заметок пока нет.')}</p></div>
    <div class="supplier-actions">
      <label class="compare-check"><input type="checkbox" data-action="compare" data-id="${s.id}" ${compared ? 'checked' : ''}> Сравнить</label>
      <button class="secondary" data-action="note" data-id="${s.id}" type="button">${s.notes ? 'Изменить заметку' : 'Добавить заметку'}</button>
      <a class="secondary link-button" href="${escapeHtml(s.website)}" target="_blank" rel="noreferrer">Сайт ↗</a>
      <a class="secondary link-button" href="${escapeHtml(s.source_url)}" target="_blank" rel="noreferrer">Источник ↗</a>
    </div>
  </article>`;
}

function visibleSuppliers() {
  return onlyFavorites ? suppliers.filter(supplier => favorites.has(supplier.id)) : suppliers;
}

function render() {
  const visible = visibleSuppliers();
  results.innerHTML = visible.map((supplier, index) => card(supplier, index + 1)).join('');
  if (!visible.length) {
    results.innerHTML = '<div class="empty">Подходящих карточек для выбранного режима пока нет.</div>';
  }
  favoritesButton.textContent = onlyFavorites ? 'Показать все' : `Избранное (${favorites.size})`;
  favoritesButton.classList.toggle('active', onlyFavorites);
  updateCompareBar();
}

function updateCompareBar() {
  compareCount.textContent = compare.size;
  compareBar.classList.toggle('hidden', compare.size === 0);
  openCompareButton.disabled = compare.size < 2;
}

async function search() {
  const payload = {
    category: document.querySelector('#category').value,
    geography: document.querySelector('#geography').value || null,
    need_delivery: document.querySelector('#delivery').checked,
    need_certificates: document.querySelector('#certs').checked,
    live_search: document.querySelector('#liveSearch').checked,
    limit: 12
  };
  loading.classList.remove('hidden');
  results.innerHTML = '';
  summary.textContent = 'Собираем список поставщиков…';
  modeInfo.textContent = '';
  try {
    const response = await fetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!response.ok) {
      throw new Error('Ошибка при выполнении поиска');
    }
    const data = await response.json();
    suppliers = data.suppliers;
    compare.clear();
    onlyFavorites = false;
    render();
    const discovered = data.discovered ? ` · новых источников обработано: ${data.discovered}` : '';
    summary.textContent = `${data.suppliers.length} вариантов · рейтинг учитывает требования закупки и полноту коммерческих данных.`;
    modeInfo.textContent = `Режим: ${data.mode}${discovered}`;
  } catch (error) {
    summary.textContent = 'Не удалось выполнить поиск.';
    results.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  } finally {
    loading.classList.add('hidden');
  }
}

function openNote(id) {
  const supplier = suppliers.find(item => item.id === id);
  if (!supplier) {
    return;
  }
  noteSupplierId = id;
  noteSupplierName.textContent = supplier.name;
  noteText.value = supplier.notes || '';
  noteDialog.showModal();
  noteText.focus();
}

async function saveNote() {
  const response = await fetch(`/api/suppliers/${noteSupplierId}/notes`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notes: noteText.value }) });
  if (!response.ok) {
    throw new Error('Не удалось сохранить заметку');
  }
  const updated = await response.json();
  const supplier = suppliers.find(item => item.id === noteSupplierId);
  if (supplier) supplier.notes = updated.notes;
  noteDialog.close();
  render();
}

function comparisonTable() {
  const selected = suppliers.filter(supplier => compare.has(supplier.id));
  const lines = [
    ['Оценка', ...selected.map(s => Math.round(s.score))],
    ['Категория', ...selected.map(s => s.category)],
    ['География', ...selected.map(s => `${s.city} · ${s.region}`)],
    ['Контакты', ...selected.map(s => s.contact || 'не найдены')],
    ['MOQ', ...selected.map(s => s.min_order || 'уточнить')],
    ['Цена', ...selected.map(s => s.price_hint || 'нет публичной')],
    ['Доставка', ...selected.map(s => s.delivery || 'уточнить')],
    ['Документы', ...selected.map(s => s.certificates || 'уточнить')],
    ['Заметка', ...selected.map(s => s.notes || '—')]
  ];
  const header = `<tr><th>Параметр</th>${selected.map(s => `<th>${escapeHtml(s.name)}</th>`).join('')}</tr>`;
  const body = lines.map(line => `<tr><td>${escapeHtml(line[0])}</td>${line.slice(1).map(value => `<td>${escapeHtml(value)}</td>`).join('')}</tr>`).join('');
  return `<div class="compare-table-wrap"><table class="compare-table">${header}${body}</table></div>`;
}

async function exportData(format, ids) {
  if (!ids.length) {
    return;
  }
  const response = await fetch(`/api/export/${format}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ supplier_ids: ids }) });
  if (!response.ok) {
    throw new Error('Не удалось сформировать файл');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = format === 'xlsx' ? 'postavshiki.xlsx' : 'postavshiki.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

results.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button) {
    return;
  }
  const id = Number(button.dataset.id);
  if (button.dataset.action === 'favorite') {
    favorites.has(id) ? favorites.delete(id) : favorites.add(id);
    saveFavorites();
    render();
  }
  if (button.dataset.action === 'note') openNote(id);
});

results.addEventListener('change', event => {
  const input = event.target.closest('[data-action="compare"]');
  if (!input) {
    return;
  }
  const id = Number(input.dataset.id);
  if (input.checked && compare.size >= 3) {
    input.checked = false;
    alert('Для наглядного сравнения можно выбрать не более трёх поставщиков.');
    return;
  }
  input.checked ? compare.add(id) : compare.delete(id);
  updateCompareBar();
});

favoritesButton.addEventListener('click', () => {
  onlyFavorites = !onlyFavorites;
  render();
});
clearCompareButton.addEventListener('click', () => {
  compare.clear();
  render();
});
openCompareButton.addEventListener('click', () => {
  compareContent.innerHTML = comparisonTable();
  compareDialog.showModal();
});
noteForm.addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await saveNote();
  } catch (error) {
    alert(error.message);
  }
});
document.querySelectorAll('[data-close-dialog]').forEach(button => {
  button.addEventListener('click', () => button.closest('dialog').close());
});
exportCsvButton.addEventListener('click', () => {
  exportData('csv', visibleSuppliers().map(supplier => supplier.id))
    .catch(error => alert(error.message));
});
exportXlsxButton.addEventListener('click', () => {
  exportData('xlsx', visibleSuppliers().map(supplier => supplier.id))
    .catch(error => alert(error.message));
});
document.querySelector('#exportCompareCsv').addEventListener('click', () => {
  exportData('csv', [...compare]).catch(error => alert(error.message));
});
document.querySelector('#exportCompareXlsx').addEventListener('click', () => {
  exportData('xlsx', [...compare]).catch(error => alert(error.message));
});
form.addEventListener('submit', event => {
  event.preventDefault();
  search();
});
search();
