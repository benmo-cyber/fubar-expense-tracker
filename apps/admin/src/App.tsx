import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Expenses from './pages/Expenses'
import GLAccounts from './pages/GLAccounts'
import { LayoutDashboard, Receipt, FileText } from 'lucide-react'

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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
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
