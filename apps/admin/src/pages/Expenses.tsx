import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Input } from '@/components/ui/input'
import { Fold } from '@/components/Fold'
import { api } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Loader2 } from 'lucide-react'
import type { Expense } from '@/types'

const STATUSES = ['draft', 'pending', 'approved', 'rejected'] as const

export default function ExpensesPage() {
  const { data: expenses, isLoading } = useQuery({
    queryKey: ['expenses', 'all'],
    queryFn: async () => {
      const { data } = await api.get<Expense[]>('/expenses', { params: { limit: 500 } })
      return data
    },
  })
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')

  const needle = query.trim().toLowerCase()
  const visible = useMemo(() => (expenses || []).filter((expense) => {
    const matchesStatus = status === 'all' || expense.status === status
    const haystack = `${expense.user?.full_name || ''} ${expense.merchant_name || ''} ${expense.category?.name || ''}`.toLowerCase()
    return matchesStatus && (!needle || haystack.includes(needle))
  }), [expenses, needle, status])

  const people = Array.from(new Set(visible.map((expense) => expense.user?.full_name || 'Unknown'))).sort()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-[#0B3D73]">Expenses</h1>
        <p className="text-muted-foreground">Receipts already filed. Approve or send back the whole report, not one line.</p>
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

      <div className="space-y-3">
        {people.map((name) => {
          const rows = visible.filter((expense) => (expense.user?.full_name || 'Unknown') === name)
          const total = rows.reduce((sum, expense) => sum + Number(expense.amount), 0)
          return (
            <Fold key={name} title={name} meta={`${rows.length} · ${formatCurrency(total)}`} forceOpen={needle.length > 0}>
              <table className="w-full text-left text-sm">
                <thead className="text-[#5B6B7C]">
                  <tr>
                    <th className="px-4 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 font-medium">Merchant</th>
                    <th className="px-3 py-2 font-medium">Account</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((expense) => (
                    <tr key={expense.id} className="border-t">
                      <td className="px-4 py-2">{formatDate(expense.expense_date)}</td>
                      <td className="px-3 py-2">
                        {expense.report_id ? (
                          <Link className="font-medium text-[#1D6FE8]" to={`/reports/${expense.report_id}`}>{expense.merchant_name || expense.description || 'Receipt'}</Link>
                        ) : (
                          expense.merchant_name || expense.description || '—'
                        )}
                      </td>
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
