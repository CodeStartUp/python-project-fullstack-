const API_BASE = '/api';

// Check if user is logged in
async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showAuthButtons();
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const user = await response.json();
            showDashboard(user);
        } else {
            logout();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        logout();
    }
}

function showDashboard(user) {
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('auth-buttons').style.display = 'none';
    
    document.getElementById('username').textContent = user.username;
    document.getElementById('email').textContent = user.email;
    document.getElementById('created_at').textContent = new Date(user.created_at).toLocaleString();
    
    if (user.hwid_bound) {
        document.getElementById('hwid_status').innerHTML = '<span style="color: #38a169;">✓ Bound</span>';
        document.getElementById('hwid_value').textContent = 'Bound to this account';
    } else {
        document.getElementById('hwid_status').innerHTML = '<span style="color: #e53e3e;">✗ Not Bound</span>';
        document.getElementById('hwid_value').textContent = 'No HWID bound';
    }
}

function showAuthButtons() {
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('auth-buttons').style.display = 'block';
}

// Login handler
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const hwid = document.getElementById('hwid').value;
        
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password, hwid })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('access_token', data.access_token);
                window.location.href = '/';
            } else {
                showError(data.detail);
            }
        } catch (error) {
            showError('Login failed. Please try again.');
        }
    });
}

// Register handler
if (document.getElementById('registerForm')) {
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const hwid = document.getElementById('hwid').value;
        
        try {
            const response = await fetch(`${API_BASE}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password, hwid })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('access_token', data.access_token);
                window.location.href = '/';
            } else {
                showError(data.detail);
            }
        } catch (error) {
            showError('Registration failed. Please try again.');
        }
    });
}

// Bind HWID
async function bindHWID() {
    const token = localStorage.getItem('access_token');
    const newHwid = document.getElementById('new_hwid').value;
    
    if (!newHwid) {
        alert('Please enter a HWID');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/bind-hwid`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ hwid: newHwid })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('HWID bound successfully!');
            checkAuth(); // Refresh dashboard
        } else {
            alert(data.detail || 'Failed to bind HWID');
        }
    } catch (error) {
        alert('Failed to bind HWID');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/';
}

// Initialize auth check on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAuth);
} else {
    checkAuth();
}