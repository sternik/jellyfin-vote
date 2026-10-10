let mediaMap = {};
let removeItems = [];
let cleanupStatus = {radarr: false, sonarr: false};
let deletedIds = new Set();

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

    const sr = await fetch('/api/cleanup/status');
    if (sr.ok) cleanupStatus = await sr.json();

    render();
}

function setTypeFilter(t) {
    currentTypeFilter = t;
    document.querySelectorAll('.chip[data-type]').forEach(el => el.classList.toggle('active', el.dataset.type === t));
    render();
}

function render() {
    const allItems = removeItems.filter(r => mediaMap[r.id]);
    const items = allItems.filter(r => {
        if (currentTypeFilter === 'all') return true;
        const m = mediaMap[r.id];
        return m && (m.type || 'Movie') === currentTypeFilter;
    });
    items.sort((a, b) => (mediaMap[a.id]?.name || '').localeCompare(mediaMap[b.id]?.name || ''));
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

function canDelete(m) {
    const type = m.type || 'Movie';
    return type === 'Series' ? cleanupStatus.sonarr : cleanupStatus.radarr;
}

function cardHtml(r) {
    const m = mediaMap[r.id];
    const meta = [m.type === 'Series' ? 'Series' : 'Movie', m.year].filter(Boolean).join(' · ');
    const isDeleted = deletedIds.has(m.id);
    const deleteBtn = isDeleted
        ? `<span class="delete-status">Deleted ✓</span>`
        : (canDelete(m)
            ? `<button class="delete-btn" onclick="confirmDelete('${m.id}')">Delete</button>`
            : '');
    return `<div class="grid-card${isDeleted ? ' deleted' : ''}" id="card-${m.id}">
        <div class="poster">
            <span class="type-badge">${m.type === 'Series' ? 'Series' : 'Movie'}</span>
            <img src="/api/img/${m.id}" alt="${escapeHtml(m.name)}" loading="lazy">
        </div>
        <div class="grid-info">
            <div class="grid-title">${escapeHtml(m.name)}</div>
            ${meta ? `<div class="grid-meta">${meta}</div>` : ''}
            <div class="grid-footer">
                <a class="card-link" href="${m.link}" target="_blank" rel="noopener">Details</a>
                ${m.imdb ? `<a class="card-link" href="${m.imdb.startsWith('http') ? m.imdb : 'https://www.imdb.com/title/' + m.imdb}" target="_blank" rel="noopener">IMDB</a>` : ''}
                ${deleteBtn}
            </div>
            <div class="delete-error" id="err-${m.id}"></div>
        </div>
    </div>`;
}

function confirmDelete(id) {
    const m = mediaMap[id];
    const target = (m.type || 'Movie') === 'Series' ? 'Sonarr' : 'Radarr';
    if (!window.confirm(`Delete "${m.name}" from ${target}?\n\nFiles on disk will be deleted permanently.`)) return;
    runDelete(id);
}

async function runDelete(id) {
    const err = document.getElementById('err-' + id);
    try {
        const r = await fetch('/api/cleanup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_id: id})
        });
        const data = await r.json();
        if (data.status === 'deleted') {
            deletedIds.add(id);
            delete mediaMap[id];
            removeItems = removeItems.filter(r => r.id !== id);
            render();
        } else {
            const target = (mediaMap[id]?.type || 'Movie') === 'Series' ? 'Sonarr' : 'Radarr';
            const messages = {
                not_agreed: 'Not everyone agreed to remove this item.',
                no_imdb: 'No IMDb ID — cannot match in *arr.',
                not_found: `Not in ${data.service || target} — this item is not managed by it (${data.imdb || 'no IMDb'}). Remove it manually in Jellyfin.`,
                unavailable: '*arr is not configured.',
                error: data.error || 'Server error.'
            };
            if (err) err.textContent = messages[data.status] || 'Delete failed.';
        }
    } catch (e) {
        if (err) err.textContent = 'Network error.';
    }
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}

init();
