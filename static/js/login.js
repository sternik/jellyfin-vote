async function login() {
    const user = document.getElementById('usernameInput').value.trim();
    const pass = document.getElementById('passwordInput').value;
    const err = document.getElementById('errorMsg');
    if (!user || !pass) { err.textContent = 'Enter username and password'; err.style.display = 'block'; return; }
    try {
        const r = await fetch('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: user, password: pass})});
        if (!r.ok) { err.textContent = 'Invalid credentials'; err.style.display = 'block'; return; }
        window.location.href = '/';
    } catch(e) { err.textContent = 'Connection error'; err.style.display = 'block'; }
}

(function init() {
    fetch('/api/me').then(r => { if (r.ok) window.location.href = '/'; });
})();