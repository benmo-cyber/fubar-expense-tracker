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
    },
  })
}
