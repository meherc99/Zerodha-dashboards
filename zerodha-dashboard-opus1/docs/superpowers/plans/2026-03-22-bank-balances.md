# Bank Balances Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-bank balance tracking system with PDF statement upload, AI-powered parsing with template learning, transaction categorization, and advanced analytics.

**Architecture:** Incremental intelligence - start with simple PDF parsers (pdfplumber), fall back to AI (Claude/GPT-4 Vision) when needed, save successful extraction patterns as reusable templates for instant future processing.

**Tech Stack:**
- Backend: Flask, SQLAlchemy, JWT auth, pdfplumber, OpenAI/Claude API, Celery (optional), Redis (caching)
- Frontend: Vue 3, Pinia, Chart.js, vue-virtual-scroller
- Database: PostgreSQL (or SQLite for dev)

---

## Implementation Phases

This plan builds the feature incrementally in 5 phases:
1. **Foundation**: Authentication system + User model
2. **Bank Accounts**: CRUD operations for bank accounts
3. **Statement Upload & Parsing**: PDF upload, parsing pipeline, template learning
4. **Transaction Management**: Display, filtering, categorization
5. **Analytics**: Charts and insights

Each phase produces working, testable software.

---

## Phase 1: Foundation - Authentication System

### Task 1.1: User Model and Database Setup

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/XXXX_add_user_model.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Update requirements.txt with auth dependencies**

Add to `backend/requirements.txt`:
```
flask-jwt-extended==4.6.0
werkzeug==3.0.1
```

- [ ] **Step 2: Create User model**

Create `backend/app/models/user.py`:
```python
"""User model for authentication"""
from datetime import datetime
from app.database import db


class User(db.Model):
    """User authentication and profile"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    bank_accounts = db.relationship('BankAccount', back_populates='user', lazy='dynamic')
    accounts = db.relationship('Account', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        """Convert user to dictionary (exclude password_hash)"""
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'is_active': self.is_active
        }
```

- [ ] **Step 3: Register User model**

Modify `backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.account import Account
from app.models.holding import Holding
from app.models.snapshot import Snapshot
from app.models.historical_price import HistoricalPrice

__all__ = ['User', 'Account', 'Holding', 'Snapshot', 'HistoricalPrice']
```

- [ ] **Step 4: Add user_id to existing Account model**

Modify `backend/app/models/account.py` - add after existing fields:
```python
# Add this field
user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

# Add this relationship
user = db.relationship('User', back_populates='accounts')
```

- [ ] **Step 5: Generate database migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "Add user model and link to accounts"
```

Expected: Migration file created in `backend/alembic/versions/`

- [ ] **Step 6: Review and apply migration**

Review the generated migration file, then run:
```bash
alembic upgrade head
```

Expected: Tables created: `users`, `user_id` column added to `accounts` table

- [ ] **Step 7: Install dependencies**

Run:
```bash
cd backend
pip install flask-jwt-extended werkzeug
```

Expected: Packages installed successfully

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/user.py backend/app/models/__init__.py backend/app/models/account.py backend/requirements.txt backend/alembic/versions/
git commit -m "feat: add User model with authentication fields

- Create User model with email, password_hash, profile fields
- Link User to existing Account model (one-to-many)
- Add database migration for users table
- Add flask-jwt-extended for JWT authentication

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 1.2: Authentication Routes (Registration & Login)

**Files:**
- Create: `backend/app/routes/auth.py`
- Create: `tests/backend/routes/test_auth.py`
- Modify: `backend/app/__init__.py` or main app file

- [ ] **Step 1: Write test for user registration**

Create `tests/backend/routes/test_auth.py`:
```python
import pytest
from app.models.user import User


class TestAuthRoutes:
    def test_register_new_user(self, client):
        """Test user registration with valid data"""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'full_name': 'New User'
        })

        assert response.status_code == 201
        data = response.json
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['full_name'] == 'New User'
        assert 'access_token' in data
        assert 'password' not in data['user']
        assert 'password_hash' not in data['user']

    def test_register_duplicate_email(self, client, sample_user):
        """Test registration with existing email fails"""
        response = client.post('/api/auth/register', json={
            'email': sample_user.email,
            'password': 'AnotherPassword123!',
            'full_name': 'Duplicate User'
        })

        assert response.status_code == 400
        assert 'already registered' in response.json['error'].lower()

    def test_login_valid_credentials(self, client, sample_user):
        """Test login with correct credentials"""
        response = client.post('/api/auth/login', json={
            'email': sample_user.email,
            'password': 'password123'
        })

        assert response.status_code == 200
        data = response.json
        assert data['user']['email'] == sample_user.email
        assert 'access_token' in data

    def test_login_invalid_credentials(self, client, sample_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'email': sample_user.email,
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        assert 'invalid credentials' in response.json['error'].lower()

    def test_get_current_user_authenticated(self, auth_client, sample_user):
        """Test getting current user with valid token"""
        response = auth_client.get('/api/auth/me')

        assert response.status_code == 200
        assert response.json['email'] == sample_user.email

    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without token fails"""
        response = client.get('/api/auth/me')

        assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend
pytest tests/backend/routes/test_auth.py -v
```

Expected: All tests FAIL with "404 Not Found" or "route not defined"

- [ ] **Step 3: Create auth routes blueprint**

Create `backend/app/routes/auth.py`:
```python
"""Authentication routes - registration, login, user info"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from app.database import db
from app.models.user import User


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json

    # Validate required fields
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 400

    # Create user
    user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        full_name=data.get('full_name', '')
    )

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user'}), 500

    # Generate JWT token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'token_type': 'Bearer'
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.json

    # Validate required fields
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user
    user = User.query.filter_by(email=data['email']).first()

    # Verify credentials
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    # Generate JWT token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'token_type': 'Bearer'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    return jsonify(user.to_dict()), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token deletion)"""
    # With JWT, logout is primarily client-side
    # Optionally implement token blacklist here for extra security
    return jsonify({'message': 'Logged out successfully'}), 200
```

- [ ] **Step 4: Configure JWT in Flask app**

Modify `backend/app/__init__.py` (or wherever Flask app is initialized):
```python
from flask_jwt_extended import JWTManager

# After creating Flask app
jwt = JWTManager(app)

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours

# Register auth blueprint
from app.routes.auth import auth_bp
app.register_blueprint(auth_bp)
```

- [ ] **Step 5: Update test fixtures**

Modify `tests/backend/conftest.py` to add user fixtures:
```python
import pytest
from werkzeug.security import generate_password_hash
from app.models.user import User


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            full_name='Test User'
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def auth_client(client, sample_user):
    """Authenticated test client with JWT token"""
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    token = response.json['access_token']

    # Add authorization header to client
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
pytest tests/backend/routes/test_auth.py -v
```

Expected: All tests PASS

- [ ] **Step 7: Manual test registration endpoint**

Run Flask app, then test:
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"manual@test.com","password":"Test123!","full_name":"Manual Test"}'
```

Expected: 201 response with user object and access_token

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes/auth.py backend/app/__init__.py tests/backend/routes/test_auth.py tests/backend/conftest.py
git commit -m "feat: add authentication routes (register, login, me)

- Implement user registration with password hashing
- Implement login with JWT token generation
- Add /me endpoint to get current user
- Configure flask-jwt-extended
- Add comprehensive test coverage for auth endpoints

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 1.3: Frontend Authentication (Login/Register Views & Store)

**Files:**
- Create: `frontend/src/stores/auth.js`
- Create: `frontend/src/views/auth/Login.vue`
- Create: `frontend/src/views/auth/Register.vue`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: Create auth store**

Create `frontend/src/stores/auth.js`:
```javascript
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token'),
    isAuthenticated: !!localStorage.getItem('token')
  }),

  actions: {
    async register(email, password, fullName) {
      const response = await api.post('/auth/register', {
        email,
        password,
        full_name: fullName
      })
      this.setAuth(response.data)
    },

    async login(email, password) {
      const response = await api.post('/auth/login', { email, password })
      this.setAuth(response.data)
    },

    setAuth(data) {
      this.user = data.user
      this.token = data.access_token
      this.isAuthenticated = true
      localStorage.setItem('token', data.access_token)

      // Set default Authorization header
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    },

    async logout() {
      try {
        await api.post('/auth/logout')
      } catch (error) {
        // Logout even if API call fails
      }

      this.user = null
      this.token = null
      this.isAuthenticated = false
      localStorage.removeItem('token')
      delete api.defaults.headers.common['Authorization']
    },

    async fetchCurrentUser() {
      if (!this.token) return

      try {
        const response = await api.get('/auth/me')
        this.user = response.data
      } catch (error) {
        // Token invalid, logout
        this.logout()
      }
    },

    initializeAuth() {
      // Called on app start to restore auth from localStorage
      if (this.token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        this.fetchCurrentUser()
      }
    }
  }
})
```

- [ ] **Step 2: Update API service with auth interceptors**

Modify `frontend/src/services/api.js`:
```javascript
import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'
})

// Request interceptor - add token to all requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle 401 errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 3: Create Login view**

Create `frontend/src/views/auth/Login.vue`:
```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Login to Portfolio Dashboard</h1>
      <p class="subtitle">Track your investments and bank balances</p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter your password"
            required
          />
        </div>

        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>

        <p v-if="error" class="error-message">{{ error }}</p>
      </form>

      <p class="auth-link">
        Don't have an account?
        <router-link to="/register">Register here</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    await authStore.login(email.value, password.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err.response?.data?.error || 'Login failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  max-width: 400px;
  width: 100%;
}

.auth-card h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: #111827;
}

.subtitle {
  color: #6b7280;
  margin-bottom: 30px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-primary {
  width: 100%;
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 15px;
  padding: 10px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 14px;
}

.auth-link {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #6b7280;
}

.auth-link a {
  color: #667eea;
  font-weight: 600;
  text-decoration: none;
}

.auth-link a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 4: Create Register view**

Create `frontend/src/views/auth/Register.vue`:
```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Create Account</h1>
      <p class="subtitle">Start tracking your portfolio</p>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="fullName">Full Name</label>
          <input
            id="fullName"
            v-model="fullName"
            type="text"
            placeholder="John Doe"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="your@email.com"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="At least 8 characters"
            required
          />
        </div>

        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? 'Creating account...' : 'Register' }}
        </button>

        <p v-if="error" class="error-message">{{ error }}</p>
      </form>

      <p class="auth-link">
        Already have an account?
        <router-link to="/login">Login here</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const fullName = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleRegister = async () => {
  loading.value = true
  error.value = ''

  try {
    await authStore.register(email.value, password.value, fullName.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err.response?.data?.error || 'Registration failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Same styles as Login.vue */
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  max-width: 400px;
  width: 100%;
}

.auth-card h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: #111827;
}

.subtitle {
  color: #6b7280;
  margin-bottom: 30px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-primary {
  width: 100%;
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 15px;
  padding: 10px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 14px;
}

.auth-link {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #6b7280;
}

.auth-link a {
  color: #667eea;
  font-weight: 600;
  text-decoration: none;
}

.auth-link a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 5: Add auth routes to router**

Modify `frontend/src/router/index.js`:
```javascript
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/',
    redirect: '/dashboard/overview'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true },
    redirect: '/dashboard/overview',
    children: [
      // existing dashboard routes...
    ]
  },
  {
    path: '/accounts',
    name: 'Accounts',
    component: Accounts,
    meta: { requiresAuth: true }
  }
]

// Navigation guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login')
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    // Redirect to dashboard if already logged in
    next('/dashboard')
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 6: Initialize auth on app start**

Modify `frontend/src/main.js`:
```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize auth from localStorage
const authStore = useAuthStore()
authStore.initializeAuth()

app.mount('#app')
```

- [ ] **Step 7: Test login flow manually**

Run frontend dev server:
```bash
cd frontend
npm run dev
```

Navigate to http://localhost:5173/login
1. Try invalid credentials - should show error
2. Register new account - should redirect to dashboard
3. Logout and login again - should work

- [ ] **Step 8: Commit**

```bash
git add frontend/src/stores/auth.js frontend/src/views/auth/ frontend/src/services/api.js frontend/src/router/index.js frontend/src/main.js
git commit -m "feat: add frontend authentication (login/register)

- Create auth store with register, login, logout actions
- Build Login and Register views with form validation
- Add API interceptors for automatic token handling
- Implement router guards for protected routes
- Auto-restore auth state from localStorage on app start

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Bank Accounts CRUD

### Task 2.1: Bank Account Model and Routes

**Files:**
- Create: `backend/app/models/bank_account.py`
- Create: `backend/app/routes/bank_accounts.py`
- Create: `tests/backend/routes/test_bank_accounts.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/XXXX_add_bank_accounts.py`

- [ ] **Step 1: Write test for bank account CRUD**

Create `tests/backend/routes/test_bank_accounts.py`:
```python
import pytest
from app.models.bank_account import BankAccount


class TestBankAccountsRoutes:
    def test_list_bank_accounts_authenticated(self, auth_client, sample_bank_account):
        """Test listing bank accounts for authenticated user"""
        response = auth_client.get('/api/bank-accounts')

        assert response.status_code == 200
        data = response.json
        assert len(data) >= 1
        assert data[0]['bank_name'] == sample_bank_account.bank_name

    def test_list_bank_accounts_unauthenticated(self, client):
        """Test listing requires authentication"""
        response = client.get('/api/bank-accounts')
        assert response.status_code == 401

    def test_create_bank_account(self, auth_client):
        """Test creating new bank account"""
        response = auth_client.post('/api/bank-accounts', json={
            'bank_name': 'HDFC Bank',
            'account_number': '1234567890',
            'account_type': 'savings'
        })

        assert response.status_code == 201
        data = response.json
        assert data['bank_name'] == 'HDFC Bank'
        assert data['account_number'] == '1234567890'
        assert data['account_type'] == 'savings'
        assert data['current_balance'] == 0

    def test_get_bank_account_own(self, auth_client, sample_bank_account):
        """Test getting own bank account"""
        response = auth_client.get(f'/api/bank-accounts/{sample_bank_account.id}')

        assert response.status_code == 200
        assert response.json['id'] == sample_bank_account.id

    def test_get_bank_account_other_user(self, auth_client, other_user_bank_account):
        """Test cannot access other user's bank account"""
        response = auth_client.get(f'/api/bank-accounts/{other_user_bank_account.id}')
        assert response.status_code == 404  # Not found due to user filter

    def test_update_bank_account(self, auth_client, sample_bank_account):
        """Test updating bank account"""
        response = auth_client.put(f'/api/bank-accounts/{sample_bank_account.id}', json={
            'bank_name': 'HDFC Bank Updated',
            'account_type': 'current'
        })

        assert response.status_code == 200
        assert response.json['bank_name'] == 'HDFC Bank Updated'
        assert response.json['account_type'] == 'current'

    def test_delete_bank_account(self, auth_client, sample_bank_account):
        """Test deleting (soft delete) bank account"""
        response = auth_client.delete(f'/api/bank-accounts/{sample_bank_account.id}')

        assert response.status_code == 200

        # Verify it's soft deleted (is_active = False)
        account = BankAccount.query.get(sample_bank_account.id)
        assert account.is_active == False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/backend/routes/test_bank_accounts.py -v
```

Expected: Tests FAIL with "bank_account model not found" or "route not defined"

- [ ] **Step 3: Create BankAccount model**

Create `backend/app/models/bank_account.py`:
```python
"""Bank account model for tracking balances"""
from datetime import datetime
from app.database import db


class BankAccount(db.Model):
    """Bank account with balance tracking"""

    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    account_type = db.Column(db.String(20), default='savings')  # savings, current, credit
    current_balance = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='INR')
    last_statement_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='bank_accounts')
    statements = db.relationship('BankStatement', back_populates='bank_account', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', back_populates='bank_account', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BankAccount {self.bank_name} - {self.account_number}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'current_balance': float(self.current_balance) if self.current_balance else 0,
            'currency': self.currency,
            'last_statement_date': self.last_statement_date.isoformat() if self.last_statement_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
```

- [ ] **Step 4: Register BankAccount model**

Modify `backend/app/models/__init__.py`:
```python
from app.models.bank_account import BankAccount

__all__ = ['User', 'Account', 'Holding', 'Snapshot', 'HistoricalPrice', 'BankAccount']
```

- [ ] **Step 5: Create bank accounts routes**

Create `backend/app/routes/bank_accounts.py`:
```python
"""Bank accounts routes - CRUD operations"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.database import db
from app.models.bank_account import BankAccount


bank_accounts_bp = Blueprint('bank_accounts', __name__, url_prefix='/api/bank-accounts')


@bank_accounts_bp.route('', methods=['GET'])
@jwt_required()
def list_bank_accounts():
    """List all bank accounts for current user"""
    user_id = get_jwt_identity()

    accounts = BankAccount.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(BankAccount.bank_name).all()

    return jsonify([account.to_dict() for account in accounts]), 200


@bank_accounts_bp.route('', methods=['POST'])
@jwt_required()
def create_bank_account():
    """Create new bank account"""
    user_id = get_jwt_identity()
    data = request.json

    # Validate required fields
    if not data.get('bank_name') or not data.get('account_number'):
        return jsonify({'error': 'Bank name and account number are required'}), 400

    # Create bank account
    account = BankAccount(
        user_id=user_id,
        bank_name=data['bank_name'],
        account_number=data['account_number'],
        account_type=data.get('account_type', 'savings'),
        currency=data.get('currency', 'INR')
    )

    try:
        db.session.add(account)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create bank account'}), 500

    return jsonify(account.to_dict()), 201


@bank_accounts_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_bank_account(account_id):
    """Get bank account details"""
    user_id = get_jwt_identity()

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
        is_active=True
    ).first_or_404()

    return jsonify(account.to_dict()), 200


@bank_accounts_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_bank_account(account_id):
    """Update bank account"""
    user_id = get_jwt_identity()

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
        is_active=True
    ).first_or_404()

    data = request.json

    # Update allowed fields
    if 'bank_name' in data:
        account.bank_name = data['bank_name']
    if 'account_number' in data:
        account.account_number = data['account_number']
    if 'account_type' in data:
        account.account_type = data['account_type']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update bank account'}), 500

    return jsonify(account.to_dict()), 200


@bank_accounts_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_bank_account(account_id):
    """Delete bank account (soft delete)"""
    user_id = get_jwt_identity()

    account = BankAccount.query.filter_by(
        id=account_id,
        user_id=user_id,
        is_active=True
    ).first_or_404()

    # Soft delete
    account.is_active = False

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete bank account'}), 500

    return jsonify({'message': 'Bank account deleted successfully'}), 200
```

- [ ] **Step 6: Register bank accounts blueprint**

Modify `backend/app/__init__.py`:
```python
from app.routes.bank_accounts import bank_accounts_bp
app.register_blueprint(bank_accounts_bp)
```

- [ ] **Step 7: Generate and apply migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "Add bank_accounts table"
alembic upgrade head
```

Expected: `bank_accounts` table created

- [ ] **Step 8: Add test fixtures**

Modify `tests/backend/conftest.py`:
```python
from app.models.bank_account import BankAccount

@pytest.fixture
def sample_bank_account(app, sample_user):
    """Create sample bank account"""
    with app.app_context():
        account = BankAccount(
            user_id=sample_user.id,
            bank_name='Test Bank',
            account_number='9999999999',
            account_type='savings',
            current_balance=10000
        )
        db.session.add(account)
        db.session.commit()
        yield account
        db.session.delete(account)
        db.session.commit()

@pytest.fixture
def other_user_bank_account(app):
    """Create bank account for different user"""
    with app.app_context():
        other_user = User(
            email='other@example.com',
            password_hash=generate_password_hash('password'),
            full_name='Other User'
        )
        db.session.add(other_user)
        db.session.commit()

        account = BankAccount(
            user_id=other_user.id,
            bank_name='Other Bank',
            account_number='8888888888'
        )
        db.session.add(account)
        db.session.commit()
        yield account

        db.session.delete(account)
        db.session.delete(other_user)
        db.session.commit()
```

- [ ] **Step 9: Run tests to verify they pass**

Run:
```bash
pytest tests/backend/routes/test_bank_accounts.py -v
```

Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/bank_account.py backend/app/routes/bank_accounts.py backend/app/models/__init__.py backend/app/__init__.py tests/backend/routes/test_bank_accounts.py tests/backend/conftest.py backend/alembic/versions/
git commit -m "feat: add bank account model and CRUD routes

- Create BankAccount model with user ownership
- Implement bank account CRUD API endpoints
- Add comprehensive tests for ownership verification
- Soft delete support for account removal

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2.2: Frontend Bank Accounts (Store, Tab, Card Grid)

**Files:**
- Create: `frontend/src/stores/bankAccounts.js`
- Create: `frontend/src/views/dashboard/BankBalancesTab.vue`
- Create: `frontend/src/components/bank/BankCard.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/dashboard/Sidebar.vue`

- [ ] **Step 1: Create bank accounts store**

Create `frontend/src/stores/bankAccounts.js`:
```javascript
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useBankAccountsStore = defineStore('bankAccounts', {
  state: () => ({
    bankAccounts: [],
    selectedBank: null,
    loading: false,
    error: null
  }),

  getters: {
    totalBalance: (state) => {
      return state.bankAccounts.reduce((sum, bank) => sum + bank.current_balance, 0)
    }
  },

  actions: {
    async fetchBankAccounts() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get('/bank-accounts')
        this.bankAccounts = response.data
      } catch (error) {
        this.error = error.response?.data?.error || 'Failed to load bank accounts'
        throw error
      } finally {
        this.loading = false
      }
    },

    async createBankAccount(data) {
      try {
        const response = await api.post('/bank-accounts', data)
        this.bankAccounts.push(response.data)
        return response.data
      } catch (error) {
        throw error
      }
    },

    async updateBankAccount(id, data) {
      try {
        const response = await api.put(`/bank-accounts/${id}`, data)
        const index = this.bankAccounts.findIndex(b => b.id === id)
        if (index !== -1) {
          this.bankAccounts[index] = response.data
        }
        return response.data
      } catch (error) {
        throw error
      }
    },

    async deleteBankAccount(id) {
      try {
        await api.delete(`/bank-accounts/${id}`)
        this.bankAccounts = this.bankAccounts.filter(b => b.id !== id)
      } catch (error) {
        throw error
      }
    },

    selectBank(bank) {
      this.selectedBank = bank
    }
  }
})
```

- [ ] **Step 2: Create BankCard component**

Create `frontend/src/components/bank/BankCard.vue`:
```vue
<template>
  <div
    class="bank-card"
    :class="{ selected: isSelected }"
    @click="$emit('select', bank.id)"
  >
    <div class="bank-header">
      <div class="bank-icon">🏦</div>
      <h3 class="bank-name">{{ bank.bank_name }}</h3>
    </div>

    <div class="bank-balance">
      <div class="balance-label">Current Balance</div>
      <div class="balance-amount">{{ formatCurrency(bank.current_balance) }}</div>
    </div>

    <div v-if="monthlyChange" class="monthly-change" :class="changeClass">
      <span class="change-icon">{{ changeIcon }}</span>
      <span>{{ formatCurrency(Math.abs(monthlyChange)) }}</span>
      <span class="change-label">this month</span>
    </div>

    <button
      @click.stop="$emit('upload')"
      class="upload-btn"
    >
      📄 Upload Statement
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bank: {
    type: Object,
    required: true
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  monthlyChange: {
    type: Number,
    default: null
  }
})

defineEmits(['select', 'upload'])

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value || 0)
}

const changeClass = computed(() => {
  if (!props.monthlyChange) return ''
  return props.monthlyChange >= 0 ? 'positive' : 'negative'
})

const changeIcon = computed(() => {
  if (!props.monthlyChange) return ''
  return props.monthlyChange >= 0 ? '↑' : '↓'
})
</script>

<style scoped>
.bank-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.bank-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.bank-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
}

.bank-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.bank-icon {
  font-size: 28px;
}

.bank-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.bank-balance {
  margin-bottom: 12px;
}

.balance-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.balance-amount {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.monthly-change {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 16px;
}

.monthly-change.positive {
  color: #10b981;
}

.monthly-change.negative {
  color: #ef4444;
}

.change-icon {
  font-weight: 700;
}

.change-label {
  color: #6b7280;
}

.upload-btn {
  width: 100%;
  padding: 10px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn:hover {
  background: #e5e7eb;
  border-color: #d1d5db;
}
</style>
```

- [ ] **Step 3: Create Bank Balances Tab**

Create `frontend/src/views/dashboard/BankBalancesTab.vue`:
```vue
<template>
  <div class="bank-balances-tab">
    <!-- Empty state when no banks -->
    <div v-if="!loading && bankAccounts.length === 0" class="empty-state">
      <div class="empty-icon">🏦</div>
      <h2>Add Your First Bank Account</h2>
      <p>Start tracking your bank balances by adding an account</p>
      <button @click="showAddModal = true" class="btn-primary">
        + Add Bank Account
      </button>
    </div>

    <!-- Bank cards grid -->
    <div v-else>
      <div class="header">
        <div>
          <h2>Bank Accounts</h2>
          <p class="total-balance">
            Total Balance: <strong>{{ formatCurrency(totalBalance) }}</strong>
          </p>
        </div>
        <button @click="showAddModal = true" class="btn-primary">
          + Add Bank Account
        </button>
      </div>

      <div class="bank-cards-grid">
        <BankCard
          v-for="bank in bankAccounts"
          :key="bank.id"
          :bank="bank"
          :is-selected="selectedBank?.id === bank.id"
          @select="handleSelectBank"
          @upload="handleUploadStatement"
        />
      </div>

      <!-- Selected bank details would go here in next phase -->
      <div v-if="selectedBank" class="selected-bank-details">
        <h3>{{ selectedBank.bank_name }} - Details</h3>
        <p>Transactions and analytics will be displayed here in next phase</p>
      </div>
    </div>

    <!-- Add Bank Modal (simple version for now) -->
    <div v-if="showAddModal" class="modal-overlay" @click="showAddModal = false">
      <div class="modal-card" @click.stop>
        <h3>Add Bank Account</h3>
        <form @submit.prevent="handleAddBank">
          <div class="form-group">
            <label>Bank Name</label>
            <input v-model="newBank.bank_name" type="text" required />
          </div>
          <div class="form-group">
            <label>Account Number</label>
            <input v-model="newBank.account_number" type="text" required />
          </div>
          <div class="form-group">
            <label>Account Type</label>
            <select v-model="newBank.account_type">
              <option value="savings">Savings</option>
              <option value="current">Current</option>
              <option value="credit">Credit Card</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" @click="showAddModal = false" class="btn-secondary">
              Cancel
            </button>
            <button type="submit" class="btn-primary">Add Account</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import BankCard from '@/components/bank/BankCard.vue'

const bankStore = useBankAccountsStore()
const { bankAccounts, selectedBank, loading, totalBalance } = storeToRefs(bankStore)

const showAddModal = ref(false)
const newBank = ref({
  bank_name: '',
  account_number: '',
  account_type: 'savings'
})

const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value || 0)
}

const handleSelectBank = (bankId) => {
  const bank = bankAccounts.value.find(b => b.id === bankId)
  bankStore.selectBank(bank)
}

const handleUploadStatement = () => {
  alert('Upload statement functionality coming in next phase')
}

const handleAddBank = async () => {
  try {
    await bankStore.createBankAccount(newBank.value)
    showAddModal.value = false
    newBank.value = { bank_name: '', account_number: '', account_type: 'savings' }
  } catch (error) {
    alert('Failed to add bank account')
  }
}

onMounted(async () => {
  await bankStore.fetchBankAccounts()
})
</script>

<style scoped>
.bank-balances-tab {
  padding: 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #111827;
}

.empty-state p {
  margin: 0 0 24px 0;
  color: #6b7280;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0 0 4px 0;
  font-size: 24px;
}

.total-balance {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.total-balance strong {
  color: #111827;
  font-size: 18px;
}

.btn-primary {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover {
  background: #2563eb;
}

.bank-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.selected-bank-details {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: white;
  border-radius: 12px;
  padding: 32px;
  max-width: 500px;
  width: 100%;
}

.modal-card h3 {
  margin: 0 0 24px 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-secondary {
  padding: 10px 20px;
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
</style>
```

- [ ] **Step 4: Add route for Bank Balances tab**

Modify `frontend/src/router/index.js`:
```javascript
{
  path: 'bank-balances',
  name: 'BankBalances',
  component: () => import('@/views/dashboard/BankBalancesTab.vue')
}
```

- [ ] **Step 5: Add Bank Balances link to sidebar**

Modify `frontend/src/components/dashboard/Sidebar.vue`:
```vue
<router-link to="/dashboard/bank-balances" class="nav-item">
  <span class="icon">💰</span>
  <span>Bank Balances</span>
</router-link>
```

- [ ] **Step 6: Test bank balances UI manually**

Run frontend:
```bash
npm run dev
```

Test:
1. Navigate to Bank Balances tab
2. Add a new bank account via modal
3. Click on bank card - should see it selected
4. Verify total balance updates

- [ ] **Step 7: Commit**

```bash
git add frontend/src/stores/bankAccounts.js frontend/src/views/dashboard/BankBalancesTab.vue frontend/src/components/bank/BankCard.vue frontend/src/router/index.js frontend/src/components/dashboard/Sidebar.vue
git commit -m "feat: add bank balances frontend (cards grid, CRUD)

- Create bank accounts Pinia store
- Build Bank Balances tab with card grid layout
- Implement BankCard component with balance display
- Add bank account creation modal
- Integrate with bank accounts API

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: Statement Upload & PDF Parsing

This phase builds the core PDF parsing system with template learning, transaction extraction, and review workflow.

### Task 3.1: Transaction Category Model & Seed Data

**Files:**
- Create: `backend/app/models/transaction_category.py`
- Create: `backend/app/utils/seed_categories.py`
- Create: `tests/backend/models/test_transaction_category.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/XXXX_add_transaction_categories.py`

- [ ] **Step 1: Write test for category model**

Create `tests/backend/models/test_transaction_category.py`:
```python
import pytest
from app.models.transaction_category import TransactionCategory


class TestTransactionCategory:
    def test_create_category(self, app):
        """Test creating a category"""
        with app.app_context():
            category = TransactionCategory(
                name='Groceries',
                icon='🛒',
                color='#10b981',
                keywords=['grocery', 'supermarket', 'bigbasket']
            )
            db.session.add(category)
            db.session.commit()

            assert category.id is not None
            assert category.name == 'Groceries'
            assert 'grocery' in category.keywords

    def test_hierarchical_categories(self, app):
        """Test parent-child category relationships"""
        with app.app_context():
            parent = TransactionCategory(name='Shopping', icon='🛍️')
            db.session.add(parent)
            db.session.commit()

            child = TransactionCategory(
                name='Groceries',
                icon='🛒',
                parent_category_id=parent.id
            )
            db.session.add(child)
            db.session.commit()

            assert child.parent_category_id == parent.id
            assert parent.children.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/backend/models/test_transaction_category.py -v
```

Expected: FAIL with "TransactionCategory model not found"

- [ ] **Step 3: Create TransactionCategory model**

Create `backend/app/models/transaction_category.py`:
```python
"""Transaction category model for organizing transactions"""
from datetime import datetime
from app.database import db


class TransactionCategory(db.Model):
    """Categories for classifying transactions"""

    __tablename__ = 'transaction_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    icon = db.Column(db.String(10))  # Emoji or icon class
    color = db.Column(db.String(7))  # Hex color code
    parent_category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'))
    keywords = db.Column(db.JSON, default=list)  # List of keywords for matching
    is_system = db.Column(db.Boolean, default=True)  # System vs user-created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    children = db.relationship('TransactionCategory', backref=db.backref('parent', remote_side=[id]))
    transactions = db.relationship('Transaction', back_populates='category')

    def __repr__(self):
        return f'<TransactionCategory {self.name}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
            'parent_category_id': self.parent_category_id,
            'keywords': self.keywords or [],
            'is_system': self.is_system
        }
```

- [ ] **Step 4: Register model and generate migration**

Modify `backend/app/models/__init__.py`:
```python
from app.models.transaction_category import TransactionCategory
__all__ = [..., 'TransactionCategory']
```

Run:
```bash
cd backend
alembic revision --autogenerate -m "Add transaction categories table"
alembic upgrade head
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/backend/models/test_transaction_category.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Create seed data utility**

Create `backend/app/utils/seed_categories.py`:
```python
"""Seed default transaction categories"""
from app.database import db
from app.models.transaction_category import TransactionCategory


DEFAULT_CATEGORIES = [
    {'name': 'Income', 'icon': '💰', 'color': '#10b981', 'keywords': ['salary', 'freelance', 'interest', 'dividend']},
    {'name': 'Housing', 'icon': '🏠', 'color': '#3b82f6', 'keywords': ['rent', 'mortgage', 'maintenance', 'property tax']},
    {'name': 'Utilities', 'icon': '⚡', 'color': '#f59e0b', 'keywords': ['electricity', 'water', 'internet', 'phone', 'mobile']},
    {'name': 'Groceries', 'icon': '🛒', 'color': '#10b981', 'keywords': ['grocery', 'supermarket', 'bigbasket', 'grofers', 'blinkit']},
    {'name': 'Dining', 'icon': '🍽️', 'color': '#ef4444', 'keywords': ['restaurant', 'swiggy', 'zomato', 'food delivery', 'cafe']},
    {'name': 'Transportation', 'icon': '🚗', 'color': '#8b5cf6', 'keywords': ['fuel', 'petrol', 'uber', 'ola', 'metro', 'bus']},
    {'name': 'Shopping', 'icon': '🛍️', 'color': '#ec4899', 'keywords': ['amazon', 'flipkart', 'myntra', 'clothing', 'electronics']},
    {'name': 'Healthcare', 'icon': '🏥', 'color': '#ef4444', 'keywords': ['doctor', 'hospital', 'pharmacy', 'medicine', 'insurance']},
    {'name': 'Entertainment', 'icon': '🎬', 'color': '#a855f7', 'keywords': ['netflix', 'prime', 'movie', 'cinema', 'spotify']},
    {'name': 'Education', 'icon': '📚', 'color': '#3b82f6', 'keywords': ['course', 'book', 'tuition', 'school', 'college']},
    {'name': 'Insurance', 'icon': '🛡️', 'color': '#6366f1', 'keywords': ['insurance', 'premium', 'policy']},
    {'name': 'Investments', 'icon': '📈', 'color': '#059669', 'keywords': ['mutual fund', 'sip', 'stock', 'investment']},
    {'name': 'Transfers', 'icon': '↔️', 'color': '#6b7280', 'keywords': ['transfer', 'neft', 'imps', 'upi']},
    {'name': 'Uncategorized', 'icon': '❓', 'color': '#9ca3af', 'keywords': []}
]


def seed_categories():
    """Seed default categories if they don't exist"""
    for cat_data in DEFAULT_CATEGORIES:
        existing = TransactionCategory.query.filter_by(name=cat_data['name']).first()
        if not existing:
            category = TransactionCategory(**cat_data, is_system=True)
            db.session.add(category)

    db.session.commit()
    print(f"Seeded {len(DEFAULT_CATEGORIES)} default categories")


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_categories()
```

- [ ] **Step 7: Run seed script**

Run:
```bash
cd backend
python -m app.utils.seed_categories
```

Expected: "Seeded 14 default categories"

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/transaction_category.py backend/app/utils/seed_categories.py backend/app/models/__init__.py tests/backend/models/test_transaction_category.py backend/alembic/versions/
git commit -m "feat: add transaction category model and seed data

- Create TransactionCategory model with hierarchical support
- Add 14 default categories with icons, colors, keywords
- Implement seed utility for populating categories
- Add comprehensive tests for category functionality

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

**Note:** The plan continues with Tasks 3.2-3.5 and Phases 4-5. Due to message length constraints, I'm providing a representative sample. The full expanded plan would follow this same detailed TDD pattern for all remaining tasks. Would you like me to:

1. Continue expanding in subsequent messages (will require multiple iterations)
2. Create a separate detailed expansion document
3. Proceed with this level of detail understanding the pattern is established

The complete expansion would add approximately 400 more similar task breakdowns.