let mediaMap = {};
let removeItems = [];

const actionsHtml = `<span id="resultsSummary" class="progress"></span>
<div class="chips">
    <button class="chip active" data-type="all" onclick="setTypeFilter('all')">All types</button>
    <button class="chip" data-type="Movie" onclick="setTypeFilter('Movie')">Movies</button>
    <button class="chip" data-type="Series" onclick="setTypeFilter('Series')">Series</button>
</div>`;

let currentTypeFilter = 'all';

async function init() {
    const user = await mountShell('results', 'Results', actionsHtml);
    if (!user) return;

    const mr = await fetch('/api/media');
    if (!mr.ok) return;
    const media = await mr.json();
    media.forEach(m => mediaMap[m.id] = m);

    const rr = await fetch('/api/results');
    removeItems = rr.ok ? await rr.json() : [];

    render();
}

function setTypeFilter(t) {
    currentTypeFilter = t;
    document.querySelectorAll('.chip[data-type]').forEach(el => el.classList.toggle('active', el.dataset.type === t));
    render();
}

function render() {
    const allItems = removeItems.filter(r => mediaMap[r.id]);
    const items = allItems.filter(m => currentTypeFilter === 'all' || (m.type || 'Movie') === currentTypeFilter);
    const summary = document.getElementById('resultsSummary');
    if (summary) {
        if (currentTypeFilter === 'all') summary.textContent = `${allItems.length} item${allItems.length === 1 ? '' : 's'} to remove · everyone agreed`;
        else summary.textContent = `${items.length} ${currentTypeFilter === 'Movie' ? 'movie' : 'series'}${items.length === 1 ? '' : 's'} to remove · everyone agreed`;
    }
    const content = document.getElementById('content');
    content.innerHTML = items.length === 0
        ? '<div class="empty"><h2>Nothing to remove</h2><p>No items have been marked for deletion yet.</p></div>'
        : `<div class="grid">${items.map(cardHtml).join('')}</div>`;
}

function cardHtml(r) {
    const m = mediaMap[r.id];
    const meta = [m.type === 'Series' ? 'Series' : 'Movie', m.year].filter(Boolean).join(' · ');
    return `<div class="grid-card">
        <div class="poster">
            <span class="type-badge">${m.type === 'Series' ? 'Series' : 'Movie'}</span>
            <img src="/api/img/${m.id}" alt="${escapeHtml(m.name)}" loading="lazy">
        </div>
        <div class="grid-info">
            <div class="grid-title">${escapeHtml(m.name)}</div>
            ${meta ? `<div class="grid-meta">${meta}</div>` : ''}
            <div class="grid-footer">
                <a class="card-link" href="${m.link}" target="_blank" rel="noopener">Details</a>
            </div>
        </div>
    </div>`;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}

init();