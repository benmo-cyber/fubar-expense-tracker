export interface User {
  id: string
  email: string
  full_name: string
  role: 'operations' | 'sales' | 'admin'
  department?: string
  default_currency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Category {
  id: string
  name: string
  description?: string
  color?: string
  icon?: string
  is_active: boolean
  created_at: string
}

export interface GLAccount {
  id: string
  account_code: string
  account_name: string
  description?: string
  account_type?: string
  parent_id?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface GLAccountMapping {
  id: string
  category_id: string
  gl_account_id: string
  created_at: string
  updated_at: string
  category?: Category
  gl_account?: GLAccount
}

export interface Expense {
  id: string
  user_id: string
  category_id?: string
  gl_account_id?: string
  amount: number
  currency: string
  description?: string
  merchant_name?: string
  expense_date: string
  receipt_url?: string
  receipt_ocr_text?: string
  ocr_confidence?: number
  ai_suggested_category_id?: string
  ai_confidence?: number
  category_manually_set: boolean
  status: 'draft' | 'pending' | 'approved' | 'rejected'
  report_id?: string | null
  notes?: string
  rejection_reason?: string
  gl_override: boolean
  created_at: string
  updated_at: string
  submitted_at?: string
  approved_at?: string
  approved_by?: string
  user?: User
  category?: Category
  ai_suggested_category?: Category
  gl_account?: GLAccount
  approver?: User
}

export interface DashboardStats {
  pending_count: number
  approved_count: number
  rejected_count: number
  total_pending_amount: number
  total_approved_amount: number
  recent_expenses: Expense[]
}
