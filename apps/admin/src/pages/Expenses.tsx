import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePendingExpenses, useApproveExpenses, useRejectExpenses } from '@/hooks/use-expenses'
import { formatCurrency, formatDate } from '@/lib/utils'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import type { Expense } from '@/types'

export default function ExpensesPage() {
  const { data: expenses, isLoading } = usePendingExpenses()
  const approveExpenses = useApproveExpenses()
  const rejectExpenses = useRejectExpenses()
  const [selectedExpenses, setSelectedExpenses] = useState<Set<string>>(new Set())
  const [rejectionReason, setRejectionReason] = useState('')
  const [showRejectDialog, setShowRejectDialog] = useState(false)

  const toggleExpense = (id: string) => {
    const newSelected = new Set(selectedExpenses)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedExpenses(newSelected)
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pending Expenses</h1>
          <p className="text-muted-foreground">Review and approve expense reports</p>
        </div>
        {selectedExpenses.size > 0 && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowRejectDialog(!showRejectDialog)}
              className="gap-2"
            >
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

      {showRejectDialog && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle>Reject Expenses</CardTitle>
            <CardDescription>Provide a reason for rejection</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="reason">Rejection Reason</Label>
              <Input
                id="reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Please provide a detailed reason..."
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowRejectDialog(false)
                  setRejectionReason('')
                }}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={!rejectionReason}
              >
                Confirm Rejection
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={selectedExpenses.size === expenses?.length && expenses.length > 0}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedExpenses(new Set(expenses?.map((e) => e.id) || []))
                      } else {
                        setSelectedExpenses(new Set())
                      }
                    }}
                  />
                </TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Employee</TableHead>
                <TableHead>Merchant</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>GL Account</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {expenses?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    No pending expenses
                  </TableCell>
                </TableRow>
              ) : (
                expenses?.map((expense) => (
                  <TableRow key={expense.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedExpenses.has(expense.id)}
                        onChange={() => toggleExpense(expense.id)}
                      />
                    </TableCell>
                    <TableCell>{formatDate(expense.expense_date)}</TableCell>
                    <TableCell>{expense.user?.full_name || 'Unknown'}</TableCell>
                    <TableCell>{expense.merchant_name || expense.description || '-'}</TableCell>
                    <TableCell>
                      {expense.category?.name || (
                        <span className="text-muted-foreground">Uncategorized</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {expense.gl_account?.account_code || (
                        <span className="text-muted-foreground">Not mapped</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(expense.amount, expense.currency)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => approveExpenses.mutate([expense.id])}
                        >
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setSelectedExpenses(new Set([expense.id]))
                            setShowRejectDialog(true)
                          }}
                        >
                          <XCircle className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
