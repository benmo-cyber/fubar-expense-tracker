import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { DashboardStats, Expense } from '@/types'

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/admin/dashboard')
      return data
    },
  })
}

export function usePendingExpenses() {
  return useQuery({
    queryKey: ['expenses', 'pending'],
    queryFn: async () => {
      const { data } = await api.get<Expense[]>('/expenses', {
        params: { status: 'pending' },
      })
      return data
    },
  })
}

export function useApproveExpenses() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (expenseIds: string[]) => {
      const { data } = await api.post('/expenses/approve', { expense_ids: expenseIds })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}

export function useRejectExpenses() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ expenseIds, reason }: { expenseIds: string[]; reason: string }) => {
      const { data } = await api.post('/expenses/reject', {
        expense_ids: expenseIds,
        rejection_reason: reason,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}
