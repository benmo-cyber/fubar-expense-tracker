import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useDashboardStats } from '@/hooks/use-expenses'
import { api } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

const BLUES = ['#0B4F8A', '#1D6FE8', '#4C93F0', '#8BB8F6', '#C5DBFB', '#E7F0FC']

type Slice = { name: string; amount: number }
type GlChild = { code: string; name: string; amount: number; percent: number }
type GlGroup = { id?: string; code: string; name: string; amount: number; children: GlChild[] }
type Insights = {
  spend: number
  this_month: number
  awaiting_review: number
  monthly: { month: string; amount: number }[]
  by_gl: Slice[]
  gl_groups?: GlGroup[]
  by_person: Slice[]
  by_merchant: Slice[]
  reports: { status: string; count: number; amount: number }[]
}

function moneyTip({ active, payload, label }: { active?: boolean; payload?: { value: number; name?: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border bg-white px-3 py-2 text-sm shadow-sm">
      <p className="font-medium text-[#0B3D73]">{label || payload[0].name}</p>
      <p>{formatCurrency(payload[0].value)}</p>
    </div>
  )
}

export default function Dashboard() {
  const { data: stats, isLoading } = useDashboardStats()
  const insights = useQuery({
    queryKey: ['finance-insights'],
    queryFn: async () => (await api.get<Insights>('/admin/insights')).data,
  })

  if (isLoading || insights.isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#1D6FE8]" />
      </div>
    )
  }

  if (!stats || !insights.data) return null
  const finance = insights.data
  const groups = finance.gl_groups || []
  const accountChart = groups.length
    ? [...groups].sort((left, right) => right.amount - left.amount).slice(0, 6).map((group) => ({ name: group.name, amount: group.amount }))
    : finance.by_gl
  const breakdowns = groups.filter((group) => group.children.length > 0)

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-[#1D6FE8]">Finance</p>
        <h1 className="text-3xl font-bold text-[#0B3D73]">Spending overview</h1>
        <p className="text-muted-foreground">What is outstanding, who spent it, and which accounts it hit.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>Total spend</CardDescription>
            <CardTitle className="text-3xl text-[#0B3D73]">{formatCurrency(finance.spend)}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">All filed receipts</CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>This month</CardDescription>
            <CardTitle className="text-3xl text-[#0B3D73]">{formatCurrency(finance.this_month)}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Receipts dated this month</CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>Waiting on you</CardDescription>
            <CardTitle className="text-3xl text-[#0B3D73]">{formatCurrency(stats.total_pending_amount)}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">{stats.pending_count} receipts not yet approved</CardContent>
        </Card>
        <Card className="border-0 bg-[#0B3D73] text-white shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-blue-100">Reports to review</CardDescription>
            <CardTitle className="text-3xl text-white">{finance.awaiting_review}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link to="/reports" className="text-sm font-semibold text-white underline-offset-4 hover:underline">Open the inbox</Link>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="border-0 shadow-sm lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-[#0B3D73]">Spend by month</CardTitle>
            <CardDescription>The last six months that have receipts</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={finance.monthly}>
                <CartesianGrid vertical={false} stroke="#E6EEF8" />
                <XAxis dataKey="month" tick={{ fill: '#5B6B7C', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#5B6B7C', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip content={<moneyTip />} />
                <Bar dataKey="amount" fill="#1D6FE8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-[#0B3D73]">By merchant</CardTitle>
            <CardDescription>Where the money went</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={finance.by_merchant} dataKey="amount" nameKey="name" innerRadius={52} outerRadius={78} paddingAngle={3}>
                    {finance.by_merchant.map((entry, index) => (
                      <Cell key={entry.name} fill={BLUES[index % BLUES.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<moneyTip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1">
              {finance.by_merchant.map((entry, index) => (
                <div key={entry.name} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: BLUES[index % BLUES.length] }} />
                    {entry.name}
                  </span>
                  <span className="font-medium">{formatCurrency(entry.amount)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[#0B3D73]">By GL account</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accountChart} layout="vertical" margin={{ left: 24 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={120} tick={{ fill: '#334155', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<moneyTip />} />
                  <Bar dataKey="amount" fill="#0B4F8A" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {breakdowns.length ? (
              <div className="mt-4 space-y-4">
                {breakdowns.map((group) => (
                  <div key={group.id || group.code}>
                    <div className="flex items-center justify-between text-sm font-medium text-[#0B3D73]">
                      <span>{group.code} {group.name}</span>
                      <span>{formatCurrency(group.amount)}</span>
                    </div>
                    <div className="mt-1 space-y-1">
                      {group.children.map((child) => (
                        <div key={`${group.code}-${child.code}-${child.name}`} className="flex items-center justify-between pl-4 text-sm text-[#334155]">
                          <span>{child.code} {child.name}</span>
                          <span>{formatCurrency(child.amount)} · {child.percent.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[#0B3D73]">By person</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={finance.by_person} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={120} tick={{ fill: '#334155', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip content={<moneyTip />} />
                <Bar dataKey="amount" fill="#4C93F0" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[#0B3D73]">Needs a decision</CardTitle>
          <CardDescription>Newest receipts still waiting</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.recent_expenses.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing is waiting.</p>
          ) : (
            <div className="space-y-4">
              {stats.recent_expenses.map((expense) => (
                <div key={expense.id} className="flex items-center justify-between border-b border-blue-50 pb-4 last:border-0 last:pb-0">
                  <div>
                    <p className="font-medium">{expense.merchant_name || expense.description || 'Untitled'}</p>
                    <p className="text-sm text-muted-foreground">
                      {expense.user?.full_name} · {formatDate(expense.expense_date)}
                    </p>
                  </div>
                  <p className="font-semibold text-[#0B3D73]">{formatCurrency(expense.amount, expense.currency)}</p>
                </div>
              ))}
              <Link to="/expenses">
                <Button className="w-full bg-[#1D6FE8] hover:bg-[#0B4F8A]">Review expenses</Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
