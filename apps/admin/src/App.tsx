import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Expenses from './pages/Expenses'
import GLAccounts from './pages/GLAccounts'
import { LayoutDashboard, Receipt, FileText } from 'lucide-react'
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

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r bg-card">
        <div className="p-6">
          <h2 className="text-2xl font-bold">Expense Admin</h2>
          <p className="text-sm text-muted-foreground">Management Portal</p>
        </div>
        <nav className="space-y-1 px-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-accent"
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Link>
          <Link
            to="/expenses"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-accent"
          >
            <Receipt className="h-4 w-4" />
            Expenses
          </Link>
          <Link
            to="/gl-accounts"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-accent"
          >
            <FileText className="h-4 w-4" />
            GL Accounts
          </Link>
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="container mx-auto p-8">{children}</div>
      </main>
    </div>
  )
}

function LoginScreen({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const { data } = await api.post<{ access_token: string }>('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      onSuccess()
    } catch {
      setError('Those credentials were not accepted.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border bg-card p-6">
        <div>
          <h1 className="text-2xl font-bold">Expense Admin</h1>
          <p className="text-sm text-muted-foreground">Sign in to manage expense accounts.</p>
        </div>
        <div>
          <Label>Email</Label>
          <Input className="mt-1" value={email} onChange={(event) => setEmail(event.target.value)} />
        </div>
        <div>
          <Label>Password</Label>
          <Input className="mt-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <Button type="submit" className="w-full">Sign in</Button>
      </form>
    </div>
  )
}

function App() {
  const [authed, setAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setAuthed(false)
      return
    }
    api.get('/auth/me')
      .then(() => setAuthed(true))
      .catch(() => {
        localStorage.removeItem('access_token')
        setAuthed(false)
      })
  }, [])

  if (authed === null) {
    return <div className="flex min-h-screen items-center justify-center">Checking sign-in…</div>
  }

  if (!authed) {
    return <LoginScreen onSuccess={() => setAuthed(true)} />
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/gl-accounts" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/expenses" element={<Expenses />} />
            <Route path="/gl-accounts" element={<GLAccounts />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
