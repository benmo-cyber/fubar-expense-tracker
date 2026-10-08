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
  useGLAccountMappings,
  useCategories,
  useCreateGLAccountMapping,
  useUpdateGLAccountMapping,
  useDeleteGLAccountMapping,
  useExpenseAccounts,
  useCreateExpenseAccount,
  useReassignExpenseAccount,
  useDeleteGLAccount,
  useUpdateGLAccount,
} from '@/hooks/use-gl-accounts'
import { Loader2, Trash2, Plus, Pencil } from 'lucide-react'

function detailFrom(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'That GL account was not saved.'
}

export default function GLAccountsPage() {
  const { data: glAccounts, isLoading: glLoading } = useGLAccounts()
  const { data: mappings, isLoading: mappingsLoading } = useGLAccountMappings()
  const { data: categories, isLoading: categoriesLoading } = useCategories()
  const createMapping = useCreateGLAccountMapping()
  const updateMapping = useUpdateGLAccountMapping()
  const deleteMapping = useDeleteGLAccountMapping()

  const { data: expenseAccounts } = useExpenseAccounts()
  const createAccount = useCreateExpenseAccount()
  const reassignAccount = useReassignExpenseAccount()
  const deleteGlAccount = useDeleteGLAccount()
  const updateGlAccount = useUpdateGLAccount()
  const [editingGl, setEditingGl] = useState<{ id: string; code: string; name: string } | null>(null)
  const [editError, setEditError] = useState('')
  const [newGlFor, setNewGlFor] = useState<string | null>(null)
  const [newCode, setNewCode] = useState('')
  const [assignError, setAssignError] = useState('')
  const [accountName, setAccountName] = useState('')
  const [accountDescription, setAccountDescription] = useState('')
  const [glCode, setGlCode] = useState('')
  const [formError, setFormError] = useState('')

  const [newMapping, setNewMapping] = useState<{
    categoryId: string
    glAccountId: string
  } | null>(null)

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
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(typeof detail === 'string' ? detail : 'That expense account was not created. Use a new name and fill in the GL account.')
    }
  }

  const isLoading = glLoading || mappingsLoading || categoriesLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  const unmappedCategories =
    categories?.filter(
      (cat) => !mappings?.some((m) => m.category_id === cat.id)
    ) || []

  const handleCreateMapping = async () => {
    if (!newMapping) return
    await createMapping.mutateAsync({
      category_id: newMapping.categoryId,
      gl_account_id: newMapping.glAccountId,
    })
    setNewMapping(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Expense accounts</h1>
        <p className="text-muted-foreground">
          Create the plain-text accounts people see and assign each one to a GL account. A four-digit code sets the parent on its own: 6410 rolls up to 6400. Removing a GL account takes it off the chart. Receipts already filed stay on it, and an expense account that used it can be pointed somewhere else.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New expense account</CardTitle>
          <CardDescription>
            The phone uses this name when it files a scanned receipt.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label>Account name</Label>
              <Input className="mt-1" value={accountName} onChange={(e) => setAccountName(e.target.value)} placeholder="Fuel" />
            </div>
            <div>
              <Label>What it is for</Label>
              <Input className="mt-1" value={accountDescription} onChange={(e) => setAccountDescription(e.target.value)} placeholder="Gas stations and vehicle fuel" />
            </div>
            <div>
              <Label>GL code</Label>
              <Input className="mt-1" value={glCode} onChange={(e) => setGlCode(e.target.value)} placeholder="6410" />
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Enter one four-digit code. The first two digits are the parent and the last two are the account under it. 6410 rolls up to 6400. A code ending in 00, such as 6400, is the parent.
          </p>
          {formError ? <p className="text-sm text-red-600">{formError}</p> : null}
          <Button
            onClick={handleCreateAccount}
            disabled={!accountName.trim() || !glCode.trim() || createAccount.isPending}
          >
            <Plus className="h-4 w-4 mr-2" />
            Create account
          </Button>
          {assignError ? <p className="text-sm text-red-600">{assignError}</p> : null}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Expense account</TableHead>
                <TableHead>Used for</TableHead>
                <TableHead>GL account</TableHead>
                <TableHead>Rolls up to</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {expenseAccounts?.length ? expenseAccounts.map((account) => (
                <TableRow key={account.category_id}>
                  <TableCell className="font-medium">{account.name}</TableCell>
                  <TableCell>{account.description || '—'}</TableCell>
                  <TableCell>
                    <select
                      className="rounded-md border border-input bg-background px-3 py-1"
                      value={newGlFor === account.category_id ? '__new__' : (account.gl_account_id || '')}
                      onChange={(event) => {
                        const value = event.target.value
                        setAssignError('')
                        if (value === '__new__') {
                          setNewGlFor(account.category_id)
                          setNewCode('')
                          return
                        }
                        setNewGlFor(null)
                        if (!value || value === account.gl_account_id) return
                        reassignAccount.mutate(
                          { categoryId: account.category_id, gl_account_id: value },
                          { onError: (error) => setAssignError(detailFrom(error)) },
                        )
                      }}
                    >
                      <option value="">Choose a GL</option>
                      {glAccounts?.map((gl) => (
                        <option key={gl.id} value={gl.id}>
                          {gl.account_code} - {gl.account_name}
                        </option>
                      ))}
                      <option value="__new__">Enter a different GL…</option>
                    </select>
                    {account.removed_code ? (
                      <p className="mt-1 text-sm text-amber-700">
                        Was {account.removed_code}{account.removed_name ? ` ${account.removed_name}` : ''}. Choose the GL it should use now.
                      </p>
                    ) : null}
                    {!account.gl_account_id && !account.removed_code ? (
                      <p className="mt-1 text-sm text-amber-700">Not posted to a GL.</p>
                    ) : null}
                    {newGlFor === account.category_id ? (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Input className="w-24" value={newCode} onChange={(event) => setNewCode(event.target.value)} placeholder="6410" />
                        <Button
                          size="sm"
                          disabled={!newCode.trim() || reassignAccount.isPending}
                          onClick={() => {
                            setAssignError('')
                            reassignAccount.mutate(
                              { categoryId: account.category_id, gl_code: newCode.trim() },
                              {
                                onSuccess: () => setNewGlFor(null),
                                onError: (error) => setAssignError(detailFrom(error)),
                              },
                            )
                          }}
                        >
                          Save GL
                        </Button>
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    {account.parent_code
                      ? (account.parent_name && account.parent_name !== account.parent_code
                        ? `${account.parent_code} ${account.parent_name}`
                        : account.parent_code)
                      : '—'}
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No expense accounts yet
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>GL accounts</CardTitle>
          <CardDescription>
            These are the codes receipts post to. Correct a code or name here. Receipts already filed stay on that account and show the correction. Removing one leaves those receipts where they are.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {editError ? <p className="px-6 py-3 text-sm text-red-600">{editError}</p> : null}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Rolls up to</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {glAccounts?.length ? glAccounts.map((gl) => {
                const parent = glAccounts.find((row) => row.id === gl.parent_id)
                const draft = editingGl?.id === gl.id ? editingGl : null
                return (
                  <TableRow key={gl.id}>
                    <TableCell className="font-medium">
                      {draft ? (
                        <Input className="w-24" value={draft.code} onChange={(event) => setEditingGl({ ...draft, code: event.target.value })} />
                      ) : gl.account_code}
                    </TableCell>
                    <TableCell>
                      {draft ? (
                        <Input value={draft.name} onChange={(event) => setEditingGl({ ...draft, name: event.target.value })} />
                      ) : gl.account_name}
                    </TableCell>
                    <TableCell>{parent ? `${parent.account_code} ${parent.account_name}` : '—'}</TableCell>
                    <TableCell className="text-right">
                      {draft ? (
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            disabled={!draft.code.trim() || !draft.name.trim() || updateGlAccount.isPending}
                            onClick={() => {
                              setEditError('')
                              updateGlAccount.mutate(
                                { id: gl.id, account_code: draft.code.trim(), account_name: draft.name.trim() },
                                {
                                  onSuccess: () => setEditingGl(null),
                                  onError: (error) => setEditError(detailFrom(error)),
                                },
                              )
                            }}
                          >
                            Save
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => { setEditingGl(null); setEditError('') }}>
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
                              setEditingGl({ id: gl.id, code: gl.account_code, name: gl.account_name })
                            }}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={deleteGlAccount.isPending}
                            onClick={() => {
                              const label = `${gl.account_code} ${gl.account_name}`
                              if (!window.confirm(`Remove ${label}? Receipts already filed stay on it.`)) return
                              deleteGlAccount.mutate(gl.id)
                            }}
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
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No GL accounts yet
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {unmappedCategories.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardHeader>
            <CardTitle>Create New Mapping</CardTitle>
            <CardDescription>
              {unmappedCategories.length} categories without GL account mappings
            </CardDescription>
          </CardHeader>
          <CardContent>
            {newMapping ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Category</Label>
                    <select
                      className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                      value={newMapping.categoryId}
                      onChange={(e) =>
                        setNewMapping({ ...newMapping, categoryId: e.target.value })
                      }
                    >
                      <option value="">Select category...</option>
                      {unmappedCategories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label>GL Account</Label>
                    <select
                      className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                      value={newMapping.glAccountId}
                      onChange={(e) =>
                        setNewMapping({ ...newMapping, glAccountId: e.target.value })
                      }
                    >
                      <option value="">Select GL account...</option>
                      {glAccounts?.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.account_code} - {acc.account_name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleCreateMapping} disabled={!newMapping.categoryId || !newMapping.glAccountId}>
                    Create Mapping
                  </Button>
                  <Button variant="outline" onClick={() => setNewMapping(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button onClick={() => setNewMapping({ categoryId: '', glAccountId: '' })}>
                <Plus className="h-4 w-4 mr-2" />
                Add Mapping
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Active Mappings</CardTitle>
          <CardDescription>
            {mappings?.length || 0} categories mapped to GL accounts
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead>GL Account Code</TableHead>
                <TableHead>GL Account Name</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mappings?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No mappings configured
                  </TableCell>
                </TableRow>
              ) : (
                mappings?.map((mapping) => (
                  <TableRow key={mapping.id}>
                    <TableCell className="font-medium">
                      {mapping.category?.name || 'Unknown'}
                    </TableCell>
                    <TableCell>
                      <select
                        className="rounded-md border border-input bg-background px-3 py-1"
                        value={mapping.gl_account_id}
                        onChange={(e) =>
                          updateMapping.mutate({
                            mappingId: mapping.id,
                            glAccountId: e.target.value,
                          })
                        }
                      >
                        {glAccounts?.map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.account_code}
                          </option>
                        ))}
                        {mapping.gl_account && !glAccounts?.some((acc) => acc.id === mapping.gl_account_id) ? (
                          <option value={mapping.gl_account_id}>
                            {mapping.gl_account.account_code}
                          </option>
                        ) : null}
                      </select>
                    </TableCell>
                    <TableCell>{mapping.gl_account?.account_name || 'Unknown'}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteMapping.mutate(mapping.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
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
