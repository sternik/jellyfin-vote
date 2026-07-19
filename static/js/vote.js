let currentUser = null;
let mediaItems = [], currentIndex = 0, votes = {keep: [], remove: []};
let dragStartX = 0, dragging = false, dragX = 0;
let progressSummary = null;

const actionsHtml = `<div class="progress" id="progressSummary">0/0 · removed 0</div><button class="icon-btn" id="refreshBtn" onclick="refreshMedia()">Refresh</button>`;

function updateProgress() {
    if (!progressSummary) return;
    const shown = currentIndex >= mediaItems.length ? mediaItems.length : currentIndex;
    progressSummary.textContent = `${shown}/${mediaItems.length} · removed ${votes.remove.length}`;
}

async function refreshMedia() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.textContent = 'Working…';
    const r = await fetch('/api/media/refresh', {method: 'POST'});
    if (r.ok) {
        if (btn) btn.textContent = 'Done';
        setTimeout(() => window.location.reload(), 800);
    } else if (btn) btn.textContent = 'Error';
}

async function init() {
    currentUser = await mountShell('vote', 'Vote', actionsHtml);
    if (!currentUser) return;
    progressSummary = document.getElementById('progressSummary');
    document.querySelector('.main').classList.add('vote-page');
    document.querySelector('.topbar').classList.add('vote-topbar');

    const r = await fetch('/api/media');
    if (!r.ok) {
        document.getElementById('content').innerHTML = '<div class="empty"><h2>Something went wrong</h2><p>Could not load media from Jellyfin.</p><button class="btn-primary" onclick="refreshMedia()">Refresh</button></div>';
        return;
    }
    mediaItems = await r.json();
    const mediaIds = new Set(mediaItems.map(m => m.id));

    try {
        const vr = await fetch('/api/votes/' + currentUser);
        if (vr.ok) votes = await vr.json();
    } catch(e) {}

    votes.remove = votes.remove.filter(id => mediaIds.has(id));
    const voted = [...votes.keep, ...votes.remove];
    mediaItems = mediaItems.filter(m => !voted.includes(m.id));
    renderCard();
}

async function saveVotes() {
    try {
        await fetch('/api/votes/' + currentUser, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(votes)});
    } catch(e) {}
}

function renderCard() {
    const content = document.getElementById('content');
    updateProgress();
    if (currentIndex >= mediaItems.length) {
        content.className = 'content';
        content.innerHTML = `<div class="empty">
            <h2>You're done!</h2>
            <p>Removed: ${votes.remove.length}</p>
            <div class="done-actions">
                <a href="/myvotes" class="btn-secondary">My Votes</a>
                <a href="/results" class="btn-primary">Results</a>
            </div>
        </div>`;
        return;
    }
    const m = mediaItems[currentIndex];
    content.className = 'content vote-content';
    content.innerHTML = `
        <div class="vote-stage" id="voteStage">
            <div class="card" id="card">
                <span class="type-badge">${m.type === 'Series' ? 'Series' : 'Movie'}</span>
                <img class="card-image" src="/api/img/${m.id}" alt="${escapeHtml(m.name)}">
                <div class="card-info">
                    <div class="card-title">${escapeHtml(m.name)}</div>
                    ${m.year ? `<div class="card-year">${m.year}</div>` : ''}
                    <div class="card-links">
                        ${m.imdb ? `<a class="card-link" href="${m.imdb}" target="_blank" rel="noopener">IMDB</a>` : ''}
                        <a class="card-link" href="${m.link}" target="_blank" rel="noopener">Details</a>
                    </div>
                </div>
            </div>
            <div class="vote-actions">
                <button class="vote-btn keep" onclick="swipe('keep')" aria-label="Keep">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H7"/></svg>
                </button>
                <button class="vote-btn remove" onclick="swipe('remove')" aria-label="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H17"/></svg>
                </button>
            </div>
            <div class="hint-pill" id="keepHint">KEEP</div>
            <div class="hint-pill" id="removeHint">REMOVE</div>
        </div>`;
    attachDrag();
}

function swipe(action) {
    const card = document.getElementById('card');
    if (!card || card.classList.contains('swiping-left') || card.classList.contains('swiping-right')) return;
    const m = mediaItems[currentIndex];
    if (action === 'keep') { card.classList.add('swiping-left'); votes.keep.push(m.id); }
    else { card.classList.add('swiping-right'); votes.remove.push(m.id); }
    updateProgress();
    saveVotes();
    setTimeout(() => { currentIndex++; renderCard(); }, 350);
}

function attachDrag() {
    const card = document.getElementById('card');
    if (!card) return;
    const keepHint = document.getElementById('keepHint');
    const removeHint = document.getElementById('removeHint');

    function down(x) { dragging = true; dragStartX = x; card.classList.add('grabbing'); }
    function move(x) {
        if (!dragging) return;
        dragX = x - dragStartX;
        card.style.transform = `translateX(${dragX}px) rotate(${dragX / 20}deg)`;
        if (dragX < -60) { keepHint.classList.add('show'); removeHint.classList.remove('show'); }
        else if (dragX > 60) { removeHint.classList.add('show'); keepHint.classList.remove('show'); }
        else { keepHint.classList.remove('show'); removeHint.classList.remove('show'); }
    }
    function up() {
        if (!dragging) return;
        dragging = false;
        card.classList.remove('grabbing');
        if (dragX < -120) { swipe('keep'); }
        else if (dragX > 120) { swipe('remove'); }
        else { card.style.transform = ''; keepHint.classList.remove('show'); removeHint.classList.remove('show'); }
        dragX = 0;
    }

    card.addEventListener('mousedown', e => down(e.clientX));
    window.addEventListener('mousemove', e => move(e.clientX));
    window.addEventListener('mouseup', up);
    card.addEventListener('touchstart', e => down(e.touches[0].clientX), {passive: true});
    window.addEventListener('touchmove', e => move(e.touches[0].clientX), {passive: true});
    window.addEventListener('touchend', up);
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
}

init();