import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Expenses from './pages/Expenses'
import GLAccounts from './pages/GLAccounts'
import People from './pages/People'
import Reports, { ReportDetail } from './pages/Reports'
import Merchants from './pages/Merchants'
import { LayoutDashboard, Receipt, FileText, Users, ClipboardList, Store } from 'lucide-react'
import { api } from './lib/api'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Label } from './components/ui/label'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const NAV = [
  { to: '/dashboard', label: 'Inbox', icon: LayoutDashboard },
  { to: '/expenses', label: 'Expenses', icon: Receipt },
  { to: '/reports', label: 'Reports', icon: ClipboardList },
  { to: '/merchants', label: 'Merchants', icon: Store },
  { to: '/people', label: 'People', icon: Users },
  { to: '/gl-accounts', label: 'GL Accounts', icon: FileText },
]

function Layout({ children, onSignOut }: { children: React.ReactNode; onSignOut: () => void }) {
  return (
    <div className="flex h-screen bg-[#F4F7FB]">
      <aside className="flex w-64 flex-col bg-[#0B3D73] text-white">
        <div className="px-5 pb-2 pt-6">
          <img src="/wildwood-logo.png?v=2" alt="Wildwood Ingredients" className="h-24 w-auto" />
          <p className="mt-3 text-2xl font-black tracking-[0.22em]">FUBAR</p>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-200">Expense reports</p>
        </div>
        <nav className="mt-4 space-y-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-full px-3 py-2.5 text-sm font-medium ${
                  isActive ? 'bg-white text-[#0B3D73]' : 'text-blue-100 hover:bg-white/10'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button type="button" onClick={onSignOut} className="mb-6 mt-auto px-6 text-left text-sm text-blue-200 hover:text-white">
          Sign out
        </button>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl p-8">{children}</div>
      </main>
    </div>
  )
}

function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F7FB] p-6">
      <div className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-8 shadow-sm">
        <img src="/wildwood-logo.png?v=2" alt="Wildwood Ingredients" className="mx-auto h-36 w-auto" />
        <div className="text-center">
          <p className="text-sm font-black tracking-[0.28em] text-[#1D6FE8]">FUBAR</p>
          <h1 className="text-2xl font-bold text-[#0B3D73]">{title}</h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  )
}

function LoginScreen({ onSuccess }: { onSuccess: (mustChange: boolean) => void }) {
  const resetToken = new URLSearchParams(window.location.search).get('token') || ''
  const [mode, setMode] = useState<'sign-in' | 'forgot' | 'reset'>(
    window.location.pathname === '/reset' || resetToken ? 'reset' : window.location.pathname === '/forgot' ? 'forgot' : 'sign-in'
  )
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const { data } = await api.post<{ access_token: string; must_change_password: boolean }>('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      onSuccess(Boolean(data.must_change_password))
    } catch {
      setError('Those credentials were not accepted.')
    }
  }

  async function sendReset(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const { data } = await api.post<{ message: string }>('/auth/forgot-password', { email })
      setNotice(data.message)
    } catch {
      setError('The reset could not be requested.')
    }
  }

  async function choosePassword(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await api.post('/auth/reset-password', { token: resetToken, new_password: password, confirm_password: confirm })
      window.history.replaceState({}, '', '/')
      setPassword('')
      setConfirm('')
      setNotice('Password saved. Sign in with it.')
      setMode('sign-in')
    } catch {
      setError('That reset link is invalid, or the passwords do not match.')
    }
  }

  if (mode === 'forgot') {
    return (
      <AuthCard title="Forgot password" subtitle="We will email a reset link if that account exists.">
        <form onSubmit={sendReset} className="space-y-4">
          <div>
            <Label>Email</Label>
            <Input className="mt-1" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          {notice ? <p className="text-sm text-[#0B3D73]">{notice}</p> : null}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <Button type="submit" className="w-full bg-[#1D6FE8] hover:bg-[#0B4F8A]">Send reset link</Button>
          <button type="button" className="w-full text-sm text-[#1D6FE8]" onClick={() => { setMode('sign-in'); setNotice(''); setError('') }}>Back to sign in</button>
        </form>
      </AuthCard>
    )
  }

  if (mode === 'reset') {
    return (
      <AuthCard title="Choose a password" subtitle="Use at least 8 characters.">
        <form onSubmit={choosePassword} className="space-y-4">
          <div>
            <Label>New password</Label>
            <Input className="mt-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <div>
            <Label>Confirm password</Label>
            <Input className="mt-1" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required />
          </div>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <Button type="submit" className="w-full bg-[#1D6FE8] hover:bg-[#0B4F8A]">Save password</Button>
        </form>
      </AuthCard>
    )
  }

  return (
    <AuthCard title="Expenses" subtitle="Sign in to review spending.">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <Label>Email</Label>
          <Input className="mt-1" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </div>
        <div>
          <Label>Password</Label>
          <Input className="mt-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </div>
        {notice ? <p className="text-sm text-[#0B3D73]">{notice}</p> : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <Button type="submit" className="w-full bg-[#1D6FE8] hover:bg-[#0B4F8A]">Sign in</Button>
        <button type="button" className="w-full text-sm text-[#1D6FE8]" onClick={() => { setMode('forgot'); setError(''); setNotice('') }}>Forgot password?</button>
      </form>
    </AuthCard>
  )
}

function ChangePasswordScreen({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await api.post('/auth/change-password', {
        current_password: current,
        new_password: password,
        confirm_password: confirm,
      })
      onDone()
    } catch {
      setError('Check the temporary password, and make the new one at least 8 characters.')
    }
  }

  return (
    <AuthCard title="Choose a password" subtitle="The temporary password works once. Pick your own to continue.">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <Label>Temporary password</Label>
          <Input className="mt-1" type="password" value={current} onChange={(event) => setCurrent(event.target.value)} required />
        </div>
        <div>
          <Label>New password</Label>
          <Input className="mt-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </div>
        <div>
          <Label>Confirm password</Label>
          <Input className="mt-1" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <Button type="submit" className="w-full bg-[#1D6FE8] hover:bg-[#0B4F8A]">Save password</Button>
      </form>
    </AuthCard>
  )
}

function App() {
  const [authed, setAuthed] = useState<boolean | null>(null)
  const [mustChange, setMustChange] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setAuthed(false)
      return
    }
    api.get<{ must_change_password?: boolean }>('/auth/me')
      .then(({ data }) => {
        setMustChange(Boolean(data.must_change_password))
        setAuthed(true)
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        setAuthed(false)
      })
  }, [])

  if (authed === null) {
    return <div className="flex min-h-screen items-center justify-center">Checking sign-in…</div>
  }

  if (!authed) {
    return <LoginScreen onSuccess={(change) => { setMustChange(change); setAuthed(true) }} />
  }

  if (mustChange) {
    return <ChangePasswordScreen onDone={() => setMustChange(false)} />
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout onSignOut={() => { localStorage.removeItem('access_token'); setAuthed(false) }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/expenses" element={<Expenses />} />
            <Route path="/gl-accounts" element={<GLAccounts />} />
            <Route path="/people" element={<People />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/reports/:reportId" element={<ReportDetail />} />
            <Route path="/merchants" element={<Merchants />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
