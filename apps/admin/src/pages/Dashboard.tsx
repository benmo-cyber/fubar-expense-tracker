import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDashboardStats } from '@/hooks/use-expenses'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Loader2, DollarSign, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function Dashboard() {
  const { data: stats, isLoading } = useDashboardStats()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of expense reports and approvals</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pending_count}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats.total_pending_amount)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approved</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.approved_count}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats.total_approved_amount)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rejected</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.rejected_count}</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(stats.total_pending_amount + stats.total_approved_amount)}
            </div>
            <p className="text-xs text-muted-foreground">Pending + Approved</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Pending Expenses</CardTitle>
          <CardDescription>Latest expense reports awaiting approval</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.recent_expenses.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending expenses</p>
          ) : (
            <div className="space-y-4">
              {stats.recent_expenses.map((expense) => (
                <div
                  key={expense.id}
                  className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {expense.merchant_name || expense.description || 'Untitled'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {expense.user?.full_name} • {formatDate(expense.expense_date)}
                    </p>
                    {expense.category && (
                      <span className="text-xs text-muted-foreground">
                        {expense.category.name}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">
                      {formatCurrency(expense.amount, expense.currency)}
                    </p>
                  </div>
                </div>
              ))}
              <div className="pt-4">
                <Link to="/expenses">
                  <Button variant="outline" className="w-full">
                    View All Expenses
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
