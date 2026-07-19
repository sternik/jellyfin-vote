let allMedia = [];
let allVotes = {keep: [], remove: []};
let currentFilter = 'all';
let currentTypeFilter = 'all';
let currentUser = null;

const actionsHtml = `<div class="chips">
    <button class="chip active" data-filter="all" onclick="setFilter('all')">All</button>
    <button class="chip" data-filter="keep" onclick="setFilter('keep')">Kept</button>
    <button class="chip" data-filter="remove" onclick="setFilter('remove')">Removed</button>
</div>
<div class="chips">
    <button class="chip active" data-type="all" onclick="setTypeFilter('all')">All types</button>
    <button class="chip" data-type="Movie" onclick="setTypeFilter('Movie')">Movies</button>
    <button class="chip" data-type="Series" onclick="setTypeFilter('Series')">Series</button>
</div>`;

async function init() {
    currentUser = await mountShell('myvotes', 'My Votes', actionsHtml);
    if (!currentUser) return;

    const mr = await fetch('/api/media');
    if (!mr.ok) return;
    allMedia = await mr.json();

    const vr = await fetch('/api/votes/' + currentUser);
    if (vr.ok) allVotes = await vr.json();

    render();
}

function setFilter(f) {
    currentFilter = f;
    document.querySelectorAll('.chip[data-filter]').forEach(el => el.classList.toggle('active', el.dataset.filter === f));
    render();
}

function setTypeFilter(t) {
    currentTypeFilter = t;
    document.querySelectorAll('.chip[data-type]').forEach(el => el.classList.toggle('active', el.dataset.type === t));
    render();
}

function render() {
    const content = document.getElementById('content');
    const items = allMedia.filter(m => {
        if (currentFilter === 'all') {
            if (!allVotes.keep.includes(m.id) && !allVotes.remove.includes(m.id)) return false;
        } else if (!allVotes[currentFilter].includes(m.id)) return false;
        if (currentTypeFilter !== 'all' && (m.type || 'Movie') !== currentTypeFilter) return false;
        return true;
    });
    if (!items.length) {
        content.innerHTML = '<div class="empty"><h2>Nothing here</h2><p>No items match these filters.</p><a href="/" class="btn-secondary">Go to Vote</a></div>';
        return;
    }
    content.innerHTML = `<div class="grid">${items.map(cardHtml).join('')}</div>`;
}

function cardHtml(m) {
    const status = allVotes.keep.includes(m.id) ? 'keep' : 'remove';
    const label = status === 'keep' ? 'Keep' : 'Remove';
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
                <button class="toggle-btn ${status}" onclick="toggle('${m.id}')">${label}</button>
            </div>
        </div>
    </div>`;
}

async function toggle(id) {
    if (allVotes.keep.includes(id)) {
        allVotes.keep = allVotes.keep.filter(x => x !== id);
        allVotes.remove.push(id);
    } else {
        allVotes.remove = allVotes.remove.filter(x => x !== id);
        allVotes.keep.push(id);
    }
    await fetch('/api/votes/' + currentUser, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(allVotes)});
    render();
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}

init();