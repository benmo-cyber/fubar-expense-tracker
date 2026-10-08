import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { GLAccount, GLAccountMapping, Category } from '@/types'

export function useGLAccounts() {
  return useQuery({
    queryKey: ['gl-accounts'],
    queryFn: async () => {
      const { data } = await api.get<GLAccount[]>('/gl-accounts')
      return data
    },
  })
}

export function useGLAccountMappings() {
  return useQuery({
    queryKey: ['gl-account-mappings'],
    queryFn: async () => {
      const { data } = await api.get<GLAccountMapping[]>('/gl-accounts/mappings')
      return data
    },
  })
}

export type ExpenseAccount = {
  category_id: string
  name: string
  description?: string
  gl_account_id?: string
  gl_code?: string
  gl_name?: string
  parent_id?: string
  parent_code?: string
  parent_name?: string
  removed_code?: string
  removed_name?: string
}

export function useExpenseAccounts() {
  return useQuery({
    queryKey: ['expense-accounts'],
    queryFn: async () => {
      const { data } = await api.get<ExpenseAccount[]>('/gl-accounts/expense-accounts')
      return data
    },
  })
}

export function useCreateExpenseAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (account: {
      name: string
      description?: string
      gl_code: string
      gl_name?: string
      parent_code?: string
      parent_name?: string
    }) => {
      const { data } = await api.post<ExpenseAccount>('/gl-accounts/expense-accounts', account)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['gl-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
    },
  })
}

export function useReassignExpenseAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      categoryId,
      gl_account_id,
      gl_code,
      gl_name,
    }: {
      categoryId: string
      gl_account_id?: string
      gl_code?: string
      gl_name?: string
    }) => {
      const { data } = await api.put<ExpenseAccount>(`/gl-accounts/expense-accounts/${categoryId}`, {
        gl_account_id,
        gl_code,
        gl_name,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['finance-insights'] })
    },
  })
}

export function useUpdateGLAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, account_code, account_name }: { id: string; account_code: string; account_name: string }) => {
      const { data } = await api.put(`/gl-accounts/${id}`, { account_code, account_name })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['finance-insights'] })
    },
  })
}

export function useDeleteGLAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/gl-accounts/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['finance-insights'] })
    },
  })
}

export function useUpdateGLAccountParent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, parent_id }: { id: string; parent_id: string | null }) => {
      const { data } = await api.put(`/gl-accounts/${id}`, { parent_id })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['finance-insights'] })
    },
  })
}

export function useUpdateCategory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, name, description }: { id: string; name: string; description: string }) => {
      const { data } = await api.put(`/categories/${id}`, { name, description })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
    },
  })
}

export function useDeleteCategory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/categories/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
    },
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const { data } = await api.get<Category[]>('/categories')
      return data
    },
  })
}

export function useCreateGLAccountMapping() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (mapping: { category_id: string; gl_account_id: string }) => {
      const { data } = await api.post('/gl-accounts/mappings', mapping)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
    },
  })
}

export function useUpdateGLAccountMapping() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ mappingId, glAccountId }: { mappingId: string; glAccountId: string }) => {
      const { data } = await api.put(`/gl-accounts/mappings/${mappingId}`, {
        gl_account_id: glAccountId,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
    },
  })
}

export function useDeleteGLAccountMapping() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (mappingId: string) => {
      await api.delete(`/gl-accounts/mappings/${mappingId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gl-account-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['expense-accounts'] })
    },
  })
}
