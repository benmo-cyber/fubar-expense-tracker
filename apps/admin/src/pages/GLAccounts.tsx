import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  useGLAccounts,
  useExpenseAccounts,
  useCreateExpenseAccount,
  useReassignExpenseAccount,
  useDeleteGLAccount,
  useUpdateGLAccount,
  useUpdateCategory,
  useDeleteCategory,
  type ExpenseAccount,
} from '@/hooks/use-gl-accounts'
import type { GLAccount } from '@/types'
import { Loader2, Trash2, Plus, Pencil } from 'lucide-react'

function detailFrom(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'That account was not saved.'
}

function rollupLabel(code?: string | null, name?: string | null) {
  if (!code) return '—'
  if (name && name !== code) return `${code} ${name}`
  return code
}

type AccountRow = {
  key: string
  categoryId?: string
  glId?: string
  name: string
  description: string
  code: string
  parentLabel: string
  removedLabel: string
}

function accountRows(expenseAccounts: ExpenseAccount[] | undefined, glAccounts: GLAccount[] | undefined): AccountRow[] {
  const used = new Set(
    (expenseAccounts ?? []).map((account) => account.gl_account_id).filter((id): id is string => Boolean(id)),
  )
  const rows: AccountRow[] = (expenseAccounts ?? []).map((account) => ({
    key: account.category_id,
    categoryId: account.category_id,
    glId: account.gl_account_id || undefined,
    name: account.name,
    description: account.description || '',
    code: account.gl_code || '',
    parentLabel: rollupLabel(account.parent_code, account.parent_name),
    removedLabel: account.removed_code
      ? `Was ${account.removed_code}${account.removed_name ? ` ${account.removed_name}` : ''}`
      : '',
  }))
  for (const gl of glAccounts ?? []) {
    if (used.has(gl.id)) continue
    const parent = glAccounts?.find((row) => row.id === gl.parent_id)
    rows.push({
      key: gl.id,
      glId: gl.id,
      name: gl.account_name,
      description: '',
      code: gl.account_code,
      parentLabel: rollupLabel(parent?.account_code, parent?.account_name),
      removedLabel: '',
    })
  }
  return rows.sort((a, b) => (a.code || 'zzzz').localeCompare(b.code || 'zzzz') || a.name.localeCompare(b.name))
}

export default function GLAccountsPage() {
  const { data: glAccounts, isLoading: glLoading } = useGLAccounts()
  const { data: expenseAccounts, isLoading: expenseLoading } = useExpenseAccounts()
  const createAccount = useCreateExpenseAccount()
  const reassignAccount = useReassignExpenseAccount()
  const deleteGlAccount = useDeleteGLAccount()
  const updateGlAccount = useUpdateGLAccount()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()
  const [editing, setEditing] = useState<{ key: string; name: string; description: string; code: string } | null>(null)
  const [editError, setEditError] = useState('')
  const [accountName, setAccountName] = useState('')
  const [accountDescription, setAccountDescription] = useState('')
  const [glCode, setGlCode] = useState('')
  const [formError, setFormError] = useState('')

  const handleCreateAccount = async () => {
    setFormError('')
    try {
      await createAccount.mutateAsync({
        name: accountName.trim(),
        description: accountDescription.trim(),
        gl_code: glCode.trim(),
      })
      setAccountName('')
      setAccountDescription('')
      setGlCode('')
    } catch (error) {
      setFormError(detailFrom(error))
    }
  }

  const saveRow = async (row: AccountRow) => {
    if (!editing) return
    setEditError('')
    const name = editing.name.trim()
    const description = editing.description.trim()
    const code = editing.code.trim()
    try {
      if (row.categoryId && (name !== row.name || description !== row.description)) {
        await updateCategory.mutateAsync({ id: row.categoryId, name, description })
      }
      if (row.glId && (code !== row.code || name !== row.name)) {
        await updateGlAccount.mutateAsync({ id: row.glId, account_code: code, account_name: name })
      } else if (!row.glId && row.categoryId && code) {
        await reassignAccount.mutateAsync({ categoryId: row.categoryId, gl_code: code })
      }
      setEditing(null)
    } catch (error) {
      setEditError(detailFrom(error))
    }
  }

  const removeRow = async (row: AccountRow) => {
    const label = row.code ? `${row.code} ${row.name}` : row.name
    if (!window.confirm(`Remove ${label}? Receipts already filed stay on it.`)) return
    setEditError('')
    const shared = (expenseAccounts ?? []).some(
      (account) => account.gl_account_id && account.gl_account_id === row.glId && account.category_id !== row.categoryId,
    )
    try {
      if (row.categoryId) await deleteCategory.mutateAsync(row.categoryId)
      if (row.glId && !shared) await deleteGlAccount.mutateAsync(row.glId)
      if (editing?.key === row.key) setEditing(null)
    } catch (error) {
      setEditError(detailFrom(error))
    }
  }

  if (glLoading || expenseLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  const rows = accountRows(expenseAccounts, glAccounts)
  const saving = updateCategory.isPending || updateGlAccount.isPending || reassignAccount.isPending

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Accounts</h1>
        <p className="text-muted-foreground">
          One list. The name is what people pick on a receipt, and the four-digit code is the GL account. 6410 rolls up to 6400. Correcting or removing an account leaves receipts already filed where they are.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New account</CardTitle>
          <CardDescription>The phone uses this name when it files a scanned receipt.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <Label>Account name</Label>
              <Input className="mt-1" value={accountName} onChange={(e) => setAccountName(e.target.value)} placeholder="Fuel" />
            </div>
            <div>
              <Label>What it is for</Label>
              <Input className="mt-1" value={accountDescription} onChange={(e) => setAccountDescription(e.target.value)} placeholder="Gas stations and vehicle fuel" />
            </div>
            <div>
              <Label>Code</Label>
              <Input className="mt-1" value={glCode} onChange={(e) => setGlCode(e.target.value)} placeholder="6410" />
            </div>
          </div>
          {formError ? <p className="text-sm text-red-600">{formError}</p> : null}
          <Button
            onClick={handleCreateAccount}
            disabled={!accountName.trim() || !glCode.trim() || createAccount.isPending}
          >
            <Plus className="h-4 w-4 mr-2" />
            Create account
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {editError ? <p className="px-6 py-3 text-sm text-red-600">{editError}</p> : null}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account</TableHead>
                <TableHead>What it is for</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Rolls up to</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length ? rows.map((row) => {
                const draft = editing?.key === row.key ? editing : null
                return (
                  <TableRow key={row.key}>
                    <TableCell className="font-medium">
                      {draft ? (
                        <Input value={draft.name} onChange={(event) => setEditing({ ...draft, name: event.target.value })} />
                      ) : row.name}
                    </TableCell>
                    <TableCell>
                      {draft && row.categoryId ? (
                        <Input value={draft.description} onChange={(event) => setEditing({ ...draft, description: event.target.value })} />
                      ) : (row.description || '—')}
                    </TableCell>
                    <TableCell>
                      {draft ? (
                        <Input className="w-24" value={draft.code} onChange={(event) => setEditing({ ...draft, code: event.target.value })} />
                      ) : (
                        <>
                          {row.code || '—'}
                          {row.removedLabel ? <p className="mt-1 text-sm text-amber-700">{row.removedLabel}</p> : null}
                        </>
                      )}
                    </TableCell>
                    <TableCell>{row.parentLabel}</TableCell>
                    <TableCell className="text-right">
                      {draft ? (
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            disabled={!draft.name.trim() || !draft.code.trim() || saving}
                            onClick={() => void saveRow(row)}
                          >
                            Save
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => { setEditing(null); setEditError('') }}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setEditError('')
                              setEditing({ key: row.key, name: row.name, description: row.description, code: row.code })
                            }}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={deleteGlAccount.isPending || deleteCategory.isPending}
                            onClick={() => void removeRow(row)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                )
              }) : (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No accounts yet
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
