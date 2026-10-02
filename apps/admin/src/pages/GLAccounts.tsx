import { useState } from 'react'
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
} from '@/hooks/use-gl-accounts'
import { Loader2, Trash2, Plus } from 'lucide-react'

export default function GLAccountsPage() {
  const { data: glAccounts, isLoading: glLoading } = useGLAccounts()
  const { data: mappings, isLoading: mappingsLoading } = useGLAccountMappings()
  const { data: categories, isLoading: categoriesLoading } = useCategories()
  const createMapping = useCreateGLAccountMapping()
  const updateMapping = useUpdateGLAccountMapping()
  const deleteMapping = useDeleteGLAccountMapping()

  const [newMapping, setNewMapping] = useState<{
    categoryId: string
    glAccountId: string
  } | null>(null)

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
        <h1 className="text-3xl font-bold">GL Account Mappings</h1>
        <p className="text-muted-foreground">
          Map expense categories to general ledger account codes
        </p>
      </div>

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
