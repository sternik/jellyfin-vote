const NAV_ITEMS = [
    { key: 'vote',    label: 'Vote',    href: '/',         icon: 'card' },
    { key: 'myvotes', label: 'My Votes', href: '/myvotes',  icon: 'check' },
    { key: 'results', label: 'Results', href: '/results',   icon: 'bars' },
];

const ICONS = {
    card: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 12l3 3 6-7"/></svg>',
    bars: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 10h.01M12 10h4M8 14h.01M12 14h4"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
};

function logout() {
    fetch('/api/logout').then(() => window.location.href = '/login');
}

async function checkAuth() {
    const res = await fetch('/api/me');
    if (!res.ok) {
        window.location.href = '/login';
        return null;
    }
    return res.json();
}

function buildSidebar(activeKey, username) {
    const navHtml = NAV_ITEMS.map(item =>
        `<a class="nav-item${item.key === activeKey ? ' active' : ''}" href="${item.href}">${ICONS[item.icon]}<span>${item.label}</span></a>`
    ).join('');
    return `
        <header class="topbar-shell">
            <div class="brand"><span class="brand-mark">J</span><span class="brand-name">Jellyfin Vote</span></div>
            <nav class="nav">${navHtml}</nav>
            <div class="account">
                <div class="user-chip"><span class="user-avatar">${username.charAt(0).toUpperCase()}</span><span class="user-name">${username}</span></div>
                <button class="icon-btn logout-btn" onclick="logout()" aria-label="Logout">${ICONS.logout}</button>
            </div>
        </header>`;
}

async function mountShell(activeKey, pageTitle, actionsHtml = '') {
    const data = await checkAuth();
    if (!data) return null;
    const user = data.user;
    const shell = document.getElementById('shell');
    if (shell) {
        shell.innerHTML = `
            ${buildSidebar(activeKey, user)}
            <main class="main">
                <header class="topbar">
                    <h1 class="page-title">${pageTitle}</h1>
                    <div class="topbar-actions">${actionsHtml}</div>
                </header>
                <div class="content" id="content"></div>
            </main>`;
    }
    return user;
}