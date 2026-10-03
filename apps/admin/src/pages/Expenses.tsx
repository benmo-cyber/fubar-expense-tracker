import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Fold } from '@/components/Fold'
import { useApproveExpenses, useRejectExpenses } from '@/hooks/use-expenses'
import { api } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import type { Expense } from '@/types'

const STATUSES = ['pending', 'draft', 'approved', 'rejected'] as const

export default function ExpensesPage() {
  const { data: expenses, isLoading } = useQuery({
    queryKey: ['expenses', 'all'],
    queryFn: async () => {
      const { data } = await api.get<Expense[]>('/expenses', { params: { limit: 500 } })
      return data
    },
  })
  const approveExpenses = useApproveExpenses()
  const rejectExpenses = useRejectExpenses()
  const [selectedExpenses, setSelectedExpenses] = useState<Set<string>>(new Set())
  const [rejectionReason, setRejectionReason] = useState('')
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')

  const needle = query.trim().toLowerCase()
  const visible = useMemo(() => (expenses || []).filter((expense) => {
    const matchesStatus = status === 'all' || expense.status === status
    const haystack = `${expense.user?.full_name || ''} ${expense.merchant_name || ''} ${expense.category?.name || ''}`.toLowerCase()
    return matchesStatus && (!needle || haystack.includes(needle))
  }), [expenses, needle, status])

  const people = Array.from(new Set(visible.map((expense) => expense.user?.full_name || 'Unknown'))).sort()

  const toggleExpense = (id: string) => {
    const next = new Set(selectedExpenses)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedExpenses(next)
  }

  const handleApprove = async () => {
    if (selectedExpenses.size === 0) return
    await approveExpenses.mutateAsync(Array.from(selectedExpenses))
    setSelectedExpenses(new Set())
  }

  const handleReject = async () => {
    if (selectedExpenses.size === 0 || !rejectionReason) return
    await rejectExpenses.mutateAsync({
      expenseIds: Array.from(selectedExpenses),
      reason: rejectionReason,
    })
    setSelectedExpenses(new Set())
    setRejectionReason('')
    setShowRejectDialog(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#0B3D73]">Expenses</h1>
          <p className="text-muted-foreground">Grouped by person. Open a name to review their lines.</p>
        </div>
        {selectedExpenses.size > 0 && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowRejectDialog(!showRejectDialog)} className="gap-2">
              <XCircle className="h-4 w-4" />
              Reject ({selectedExpenses.size})
            </Button>
            <Button onClick={handleApprove} className="gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Approve ({selectedExpenses.size})
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setStatus('all')}
          className={`rounded-full px-3 py-1.5 text-sm font-semibold ${status === 'all' ? 'bg-[#0B3D73] text-white' : 'bg-white text-[#0B3D73]'}`}
        >
          All {expenses?.length || 0}
        </button>
        {STATUSES.filter((item) => expenses?.some((expense) => expense.status === item)).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setStatus(item)}
            className={`rounded-full px-3 py-1.5 text-sm font-semibold capitalize ${status === item ? 'bg-[#0B3D73] text-white' : 'bg-white text-[#0B3D73]'}`}
          >
            {item} {expenses?.filter((expense) => expense.status === item).length}
          </button>
        ))}
      </div>
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a person, merchant, or account" />

      {showRejectDialog && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle>Reject Expenses</CardTitle>
            <CardDescription>Provide a reason for rejection</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="reason">Rejection Reason</Label>
              <Input id="reason" value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} placeholder="Please provide a detailed reason..." />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { setShowRejectDialog(false); setRejectionReason('') }}>Cancel</Button>
              <Button variant="destructive" onClick={handleReject} disabled={!rejectionReason}>Confirm Rejection</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {people.map((name) => {
          const rows = visible.filter((expense) => (expense.user?.full_name || 'Unknown') === name)
          const total = rows.reduce((sum, expense) => sum + Number(expense.amount), 0)
          const pending = rows.filter((expense) => expense.status === 'pending')
          return (
            <Fold key={name} title={name} meta={`${rows.length} · ${formatCurrency(total)}`} forceOpen={needle.length > 0}>
              <table className="w-full text-left text-sm">
                <thead className="text-[#5B6B7C]">
                  <tr>
                    <th className="w-10 px-4 py-2">
                      {pending.length > 0 ? (
                        <input
                          type="checkbox"
                          checked={pending.every((expense) => selectedExpenses.has(expense.id))}
                          onChange={(event) => {
                            const next = new Set(selectedExpenses)
                            pending.forEach((expense) => event.target.checked ? next.add(expense.id) : next.delete(expense.id))
                            setSelectedExpenses(next)
                          }}
                        />
                      ) : null}
                    </th>
                    <th className="px-3 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 font-medium">Merchant</th>
                    <th className="px-3 py-2 font-medium">Account</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((expense) => (
                    <tr key={expense.id} className="border-t">
                      <td className="px-4 py-2">
                        {expense.status === 'pending' ? (
                          <input type="checkbox" checked={selectedExpenses.has(expense.id)} onChange={() => toggleExpense(expense.id)} />
                        ) : null}
                      </td>
                      <td className="px-3 py-2">{formatDate(expense.expense_date)}</td>
                      <td className="px-3 py-2">{expense.merchant_name || expense.description || '—'}</td>
                      <td className="px-3 py-2">{expense.category?.name || 'Uncategorized'}</td>
                      <td className="px-3 py-2 capitalize">{expense.status}</td>
                      <td className="px-4 py-2 text-right font-semibold">{formatCurrency(Number(expense.amount), expense.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Fold>
          )
        })}
        {people.length === 0 ? <p className="text-muted-foreground">No expenses match.</p> : null}
      </div>
    </div>
  )
}
