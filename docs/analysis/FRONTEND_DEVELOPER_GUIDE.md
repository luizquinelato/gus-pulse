# Frontend Developer Guide

## Quick Start

### Running the Frontends

```bash
# Analytics Dashboard (Frontend-App)
cd services/frontend-app
npm install
npm run dev
# Runs on http://localhost:3000

# ETL Management Interface (Frontend-ETL)
cd services/frontend-etl
npm install
npm run dev
# Runs on http://localhost:3002
```

---

## Design System Reference

### Color Variables

**5-Color Schema (Tenant-Customizable):**
```css
var(--color-1)  /* Blue - Primary brand/data */
var(--color-2)  /* Purple - Secondary brand/data */
var(--color-3)  /* Emerald - Success metrics/data */
var(--color-4)  /* Sky Blue - Info metrics/data */
var(--color-5)  /* Amber - Warning metrics/data */
```

**CRUD Operations (Universal - Never Change):**
```css
var(--crud-create)  /* #059669 - Green */
var(--crud-edit)    /* #0ea5e9 - Blue */
var(--crud-delete)  /* #dc2626 - Red */
var(--crud-cancel)  /* #6b7280 - Gray */
```

**Status Indicators (Universal - Never Change):**
```css
var(--status-success)  /* #10b981 - Green */
var(--status-warning)  /* #f59e0b - Amber */
var(--status-error)    /* #ef4444 - Red */
var(--status-info)     /* #3b82f6 - Blue */
```

**On-Colors (Auto-Computed for Text Readability):**
```css
var(--on-color-1)  /* White or Black based on contrast */
var(--on-color-2)
var(--on-color-3)
var(--on-color-4)
var(--on-color-5)
```

**Gradients:**
```css
var(--gradient-1-2)  /* linear-gradient(135deg, color1, color2) */
var(--gradient-2-3)
var(--gradient-3-4)
var(--gradient-4-5)
var(--gradient-5-1)

var(--on-gradient-1-2)  /* Text color for gradient backgrounds */
var(--on-gradient-2-3)
/* ... etc */
```

**Theme Variables:**
```css
var(--bg-primary)    /* Main background */
var(--bg-secondary)  /* Card backgrounds */
var(--bg-tertiary)   /* Hover states */
var(--text-primary)  /* Main text */
var(--text-secondary)/* Secondary text */
var(--text-muted)    /* Muted text */
var(--border-color)  /* Borders */
```

---

## Component Patterns

### Creating a New Page

```typescript
import { motion } from 'framer-motion'
import CollapsedSidebar from '../components/CollapsedSidebar'
import Header from '../components/Header'
import useDocumentTitle from '../hooks/useDocumentTitle'

export default function MyNewPage() {
  useDocumentTitle('My Page Title')

  return (
    <div className="min-h-screen bg-primary">
      <Header />
      
      <div className="flex">
        <CollapsedSidebar />
        
        <main className="flex-1 ml-16">
          <div className="max-w-[1400px] mx-auto px-6 py-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="space-y-6"
            >
              <div className="space-y-2">
                <h1 className="text-3xl font-bold text-primary">
                  Page Title
                </h1>
                <p className="text-secondary">
                  Page description
                </p>
              </div>
              
              {/* Your content here */}
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  )
}
```

### Using the Theme Context

```typescript
import { useTheme } from '../contexts/ThemeContext'

function MyComponent() {
  const { 
    theme,              // 'light' | 'dark'
    toggleTheme,        // Function to toggle theme
    colorSchema,        // Current active colors
    colorSchemaMode,    // 'default' | 'custom'
    accessibilityLevel  // 'regular' | 'AA' | 'AAA'
  } = useTheme()

  return (
    <div style={{ 
      background: theme === 'dark' ? '#24292f' : '#f6f8fa',
      color: `var(--color-1)` 
    }}>
      Current theme: {theme}
    </div>
  )
}
```

### Using the Auth Context

```typescript
import { useAuth } from '../contexts/AuthContext'

function MyComponent() {
  const { 
    user,       // User object with tenant_id, role, etc.
    isAdmin,    // Boolean - is user admin?
    logout,     // Function to logout
    isLoading   // Boolean - is auth loading?
  } = useAuth()

  if (isLoading) return <div>Loading...</div>
  if (!user) return <div>Not authenticated</div>

  return (
    <div>
      Welcome, {user.first_name}!
      {isAdmin && <button>Admin Panel</button>}
    </div>
  )
}
```

### Using Toast Notifications

```typescript
import { useToast } from '../hooks/useToast'

function MyComponent() {
  const { showSuccess, showError, showInfo, showWarning } = useToast()

  const handleSave = async () => {
    try {
      await saveData()
      showSuccess('Saved!', 'Your changes have been saved successfully')
    } catch (error) {
      showError('Error', 'Failed to save changes')
    }
  }

  return <button onClick={handleSave}>Save</button>
}
```

---

## Styling Guidelines

### Card Components

```tsx
<div className="card">
  {/* Card content */}
</div>

<div className="card-elevated">
  {/* Elevated card with more shadow */}
</div>
```

### Buttons

```tsx
{/* Primary button with gradient */}
<button className="btn-primary">
  Save Changes
</button>

{/* CRUD-specific buttons */}
<button className="btn-create">Create</button>
<button className="btn-edit">Edit</button>
<button className="btn-delete">Delete</button>
<button className="btn-cancel">Cancel</button>
```

### Text Colors

```tsx
<h1 className="text-primary">Main heading</h1>
<p className="text-secondary">Secondary text</p>
<span className="text-muted">Muted text</span>
```

---

## API Integration

### Frontend-App API Calls

```typescript
import axios from 'axios'

// API base URL is configured in .env
// VITE_API_BASE_URL=http://localhost:3001

const response = await axios.get('/api/v1/admin/tenants')
const data = response.data
```

### Frontend-ETL API Calls

```typescript
import { etlApi } from '../services/etlApiService'

// etlApi is pre-configured with auth headers
const response = await etlApi.get(`/jobs?tenant_id=${user.tenant_id}`)
const jobs = response.data
```

---

## WebSocket Integration

### Session WebSocket (Both Frontends)

```typescript
// Already initialized in AuthContext - no manual setup needed
// Listens for: logout, theme_changed, color_schema_changed
```

### ETL Job WebSocket (ETL Only)

```typescript
import { etlWebSocketService } from '../services/etlWebSocketService'

// Subscribe to job progress
useEffect(() => {
  const handleJobProgress = (event: CustomEvent) => {
    const { jobId, status, progress } = event.detail
    // Update UI
  }

  window.addEventListener('etl-job-progress', handleJobProgress as EventListener)
  return () => {
    window.removeEventListener('etl-job-progress', handleJobProgress as EventListener)
  }
}, [])
```

---

## Best Practices

### 1. Always Use CSS Variables for Colors
❌ **Don't:**
```tsx
<div style={{ color: '#2862EB' }}>Text</div>
```

✅ **Do:**
```tsx
<div style={{ color: 'var(--color-1)' }}>Text</div>
```

### 2. Use Framer Motion for Animations
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
  Content
</motion.div>
```

### 3. Handle Loading States
```tsx
if (isLoading) return <div className="flex items-center justify-center p-8">
  <Loader className="w-6 h-6 animate-spin" />
</div>
```

### 4. Use Semantic HTML
```tsx
<header>...</header>
<nav>...</nav>
<main>...</main>
<aside>...</aside>
```

### 5. Add Accessibility Attributes
```tsx
<button aria-label="Close modal" title="Close">
  <X className="w-4 h-4" />
</button>
```

---

## Common Pitfalls

### ❌ Hardcoding Colors
```tsx
// BAD - breaks theme and tenant customization
<div style={{ background: '#2862EB' }}>
```

### ❌ Not Handling Loading States
```tsx
// BAD - shows undefined data during load
<div>{user.name}</div>
```

### ❌ Forgetting to Clean Up Event Listeners
```tsx
// BAD - memory leak
useEffect(() => {
  window.addEventListener('resize', handleResize)
  // Missing cleanup!
}, [])
```

### ✅ Correct Patterns
```tsx
// GOOD - uses CSS variable
<div style={{ background: 'var(--color-1)' }}>

// GOOD - handles loading
{isLoading ? <Spinner /> : <div>{user.name}</div>}

// GOOD - cleans up
useEffect(() => {
  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [])
```

---

## Testing

### Running Tests
```bash
npm run test        # Run all tests
npm run test:watch  # Watch mode
npm run test:coverage  # Coverage report
```

### Writing Component Tests
```typescript
import { render, screen } from '@testing-library/react'
import MyComponent from './MyComponent'

test('renders component', () => {
  render(<MyComponent />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

---

## Deployment

### Building for Production
```bash
npm run build  # Creates optimized production build in /dist
```

### Environment Variables
```bash
# .env.production
VITE_API_BASE_URL=https://api.healthpulse.com
VITE_ETL_SERVICE_URL=https://etl.healthpulse.com
```

---

## Resources

- **Full UX Analysis**: `docs/FRONTEND_UX_ANALYSIS.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Security**: `docs/SECURITY.md`
- **Framer Motion Docs**: https://www.framer.com/motion/
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **Lucide Icons**: https://lucide.dev/

