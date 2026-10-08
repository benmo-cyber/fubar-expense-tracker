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
  useUpdateGLAccountParent,
} from '@/hooks/use-gl-accounts'
import { Loader2, Trash2, Plus } from 'lucide-react'

export default function GLAccountsPage() {
  const { data: glAccounts, isLoading: glLoading } = useGLAccounts()
  const { data: mappings, isLoading: mappingsLoading } = useGLAccountMappings()
  const { data: categories, isLoading: categoriesLoading } = useCategories()
  const createMapping = useCreateGLAccountMapping()
  const updateMapping = useUpdateGLAccountMapping()
  const deleteMapping = useDeleteGLAccountMapping()

  const { data: expenseAccounts } = useExpenseAccounts()
  const createAccount = useCreateExpenseAccount()
  const updateParent = useUpdateGLAccountParent()
  const [accountName, setAccountName] = useState('')
  const [accountDescription, setAccountDescription] = useState('')
  const [glCode, setGlCode] = useState('')
  const [glName, setGlName] = useState('')
  const [parentCode, setParentCode] = useState('')
  const [parentName, setParentName] = useState('')
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
        gl_name: glName.trim(),
        parent_code: parentCode.trim() || undefined,
        parent_name: parentName.trim() || undefined,
      })
      setAccountName('')
      setAccountDescription('')
      setGlCode('')
      setGlName('')
      setParentCode('')
      setParentName('')
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(typeof detail === 'string' ? detail : 'That expense account was not created. Use a new name and fill in the GL account.')
    }
  }

  const parentKnown = glAccounts?.some((gl) => gl.account_code === parentCode.trim())
  const parentReady = !parentCode.trim() || Boolean(parentKnown) || Boolean(parentName.trim())
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
          Create the plain-text accounts people see, assign each one to a GL account, and roll sub-accounts up to a parent.
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
              <Input className="mt-1" value={glCode} onChange={(e) => setGlCode(e.target.value)} placeholder="6100" />
            </div>
            <div>
              <Label>GL account name</Label>
              <Input className="mt-1" value={glName} onChange={(e) => setGlName(e.target.value)} placeholder="Vehicle fuel" />
            </div>
            <div>
              <Label>Parent GL code</Label>
              <Input className="mt-1" value={parentCode} onChange={(e) => setParentCode(e.target.value)} placeholder="6400" />
            </div>
            <div>
              <Label>Parent GL name</Label>
              <Input className="mt-1" value={parentName} onChange={(e) => setParentName(e.target.value)} placeholder="Travel & Meals" />
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Leave the parent blank when this account stands on its own. To put travel or meals under 6400, enter that code and Travel & Meals. The parent is created the first time you use it.
          </p>
          {formError ? <p className="text-sm text-red-600">{formError}</p> : null}
          <Button
            onClick={handleCreateAccount}
            disabled={!accountName.trim() || !glCode.trim() || !glName.trim() || !parentReady || createAccount.isPending}
          >
            <Plus className="h-4 w-4 mr-2" />
            Create account
          </Button>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Expense account</TableHead>
                <TableHead>Used for</TableHead>
                <TableHead>GL code</TableHead>
                <TableHead>GL name</TableHead>
                <TableHead>Rolls up to</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {expenseAccounts?.length ? expenseAccounts.map((account) => (
                <TableRow key={account.category_id}>
                  <TableCell className="font-medium">{account.name}</TableCell>
                  <TableCell>{account.description || '—'}</TableCell>
                  <TableCell>{account.gl_code || 'Not assigned'}</TableCell>
                  <TableCell>{account.gl_name || 'Not assigned'}</TableCell>
                  <TableCell>
                    {account.gl_account_id ? (
                      <select
                        className="rounded-md border border-input bg-background px-3 py-1"
                        value={account.parent_id || ''}
                        onChange={(event) => updateParent.mutate({
                          id: account.gl_account_id as string,
                          parent_id: event.target.value || null,
                        })}
                      >
                        <option value="">No parent</option>
                        {glAccounts?.filter((gl) => gl.id !== account.gl_account_id).map((gl) => (
                          <option key={gl.id} value={gl.id}>
                            {gl.account_code} - {gl.account_name}
                          </option>
                        ))}
                      </select>
                    ) : 'Not assigned'}
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No expense accounts yet
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
