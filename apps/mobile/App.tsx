import { useCallback, useEffect, useState, type ReactNode } from "react"
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native"
import { StatusBar } from "expo-status-bar"
import * as ImagePicker from "expo-image-picker"
import * as Sharing from "expo-sharing"
import { File, Paths, UploadType } from "expo-file-system"
import { api, clearToken, getToken, setToken } from "./src/api"
import { API_URL } from "./src/config"

type Account = {
  category_id: string
  name: string
  description?: string
  gl_code?: string
  gl_name?: string
}

type Expense = {
  id: string
  merchant_name?: string
  amount: number | string
  expense_date: string
  status: "draft" | "pending" | "approved" | "rejected"
  notes?: string
  category?: { name: string }
  gl_account?: { account_code: string; account_name: string }
}

type ScanResult = {
  ocr_result: {
    merchant_name?: string | null
    amount?: number | string | null
    date?: string | null
    raw_text: string
    confidence: number | string
  }
  ai_suggestion?: {
    category_id: string
    category_name: string
    gl_account_code?: string | null
    gl_account_name?: string | null
    reasoning: string
    confidence: number | string
  } | null
}

type Split = { name: string; amount: number }
type TripRow = { id: string; name: string; total: number; by_gl: Split[]; by_merchant: Split[] }
type Line = {
  id: string
  merchant_name: string
  amount: number
  expense_date: string
  trip_name?: string | null
  category_name?: string | null
  gl_name?: string | null
  gl_code?: string | null
  receipt_url?: string | null
  notes?: string | null
}
type ReportRow = {
  id: string
  user_id: string
  user_name: string
  title: string
  period_start: string
  period_end: string
  status: string
  total: number
  review_notes?: string | null
  trips: TripRow[]
  by_gl: Split[]
  by_merchant: Split[]
  expenses?: Line[]
}
type Notice = { id: string; message: string; read: boolean }
type Summary = { spend: number; open_reports: number; awaiting_review: number; by_gl: Split[]; by_merchant: Split[] }
type Profile = { id: string; email: string; full_name: string; role: string; must_change_password?: boolean }
type Person = {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  is_superuser: boolean
  supervisor_id: string | null
}
type MerchantRow = { id: string | null; name: string; amount: number; count: number }
type Insights = {
  spend: number
  this_month: number
  awaiting_review: number
  monthly: { month: string; amount: number }[]
  by_gl: Split[]
  by_person: Split[]
  by_merchant: Split[]
}
type Screen = "home" | "reports" | "list" | "review" | "report" | "people" | "merchants" | "accounts"

type Draft = {
  merchant: string
  amount: string
  date: string
  categoryId: string
  notes: string
  ocrText: string
  ocrConfidence: string
  aiConfidence: string
  receiptUri: string
}

const STATUS_LABEL = {
  draft: "Draft",
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
}

function isoToUS(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  return match ? `${match[2]}/${match[3]}/${match[1]}` : value
}

function usToISO(value: string) {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim())
  if (!match) return ""
  return `${match[3]}-${match[1].padStart(2, "0")}-${match[2].padStart(2, "0")}`
}

function todayUS() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${month}/${day}/${date.getFullYear()}`
}

function money(amount: number | string) {
  const value = Number(amount)
  if (!Number.isFinite(value)) return "$0.00"
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" })
}

function prettyDate(iso: string) {
  const [year, month, day] = iso.split("-").map(Number)
  if (!year || !month || !day) return iso
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

function mediaUrl(path?: string | null) {
  if (!path) return ""
  if (path.startsWith("http")) return path
  return `${API_URL.replace(/\/api\/v1\/?$/, "")}${path}`
}

function directReports(people: Person[], id: string) {
  return people.filter((person) => person.supervisor_id === id && person.id !== id).length
}

function emptyDraft(categoryId = ""): Draft {
  return {
    merchant: "",
    amount: "",
    date: todayUS(),
    categoryId,
    notes: "",
    ocrText: "",
    ocrConfidence: "",
    aiConfidence: "",
    receiptUri: "",
  }
}

function Bars({ rows }: { rows: Split[] }) {
  const max = Math.max(...rows.map((row) => row.amount), 1)
  if (rows.length === 0) return <Text style={styles.meta}>Nothing filed yet.</Text>
  return (
    <View style={styles.bars}>
      {rows.map((row) => (
        <View key={row.name}>
          <View style={styles.barLabel}>
            <Text style={styles.meta}>{row.name}</Text>
            <Text style={styles.amount}>{money(row.amount)}</Text>
          </View>
          <View style={styles.track}>
            <View style={[styles.fill, { width: `${Math.max(6, (row.amount / max) * 100)}%` }]} />
          </View>
        </View>
      ))}
    </View>
  )
}

export default function App() {
  const [ready, setReady] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [email, setEmail] = useState("field@example.com")
  const [password, setPassword] = useState("")
  const [profile, setProfile] = useState<Profile | null>(null)
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [screen, setScreen] = useState<Screen>("home")
  const [summary, setSummary] = useState<Summary | null>(null)
  const [insights, setInsights] = useState<Insights | null>(null)
  const [notices, setNotices] = useState<Notice[]>([])
  const [reports, setReports] = useState<ReportRow[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [merchants, setMerchants] = useState<MerchantRow[]>([])
  const [activeReport, setActiveReport] = useState<ReportRow | null>(null)
  const [tripName, setTripName] = useState("")
  const [periodStart, setPeriodStart] = useState("")
  const [periodEnd, setPeriodEnd] = useState("")
  const [reportTitle, setReportTitle] = useState("")
  const [tripId, setTripId] = useState("")
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [busy, setBusy] = useState(false)
  const [loginError, setLoginError] = useState("")
  const [rejectNotes, setRejectNotes] = useState("")
  const [inviteName, setInviteName] = useState("")
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("sales")
  const [inviteSupervisor, setInviteSupervisor] = useState("")
  const [issuedPassword, setIssuedPassword] = useState("")
  const [mustChange, setMustChange] = useState(false)
  const [forgotMode, setForgotMode] = useState(false)
  const [forgotNotice, setForgotNotice] = useState("")
  const [nextPassword, setNextPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [renameId, setRenameId] = useState("")
  const [renameValue, setRenameValue] = useState("")
  const [mergeSource, setMergeSource] = useState("")
  const [accountName, setAccountName] = useState("")
  const [glCode, setGlCode] = useState("")
  const [showInvite, setShowInvite] = useState(false)
  const [chartPerson, setChartPerson] = useState("")
  const [merchantQuery, setMerchantQuery] = useState("")
  const [openLetter, setOpenLetter] = useState("")
  const [openGroup, setOpenGroup] = useState("")

  const isAdmin = profile?.role === "admin"

  const loadData = useCallback(async (asAdmin: boolean) => {
    const [expenseRows, accountRows, summaryRow, noticeRows, reportRows, merchantRows] = await Promise.all([
      api<Expense[]>("/expenses"),
      api<Account[]>("/gl-accounts/expense-accounts"),
      api<Summary>("/summary"),
      api<Notice[]>("/notices"),
      api<ReportRow[]>("/reports"),
      api<MerchantRow[]>("/merchants"),
    ])
    setExpenses(expenseRows)
    setAccounts(accountRows)
    setSummary(summaryRow)
    setNotices(noticeRows)
    setReports(reportRows)
    setMerchants(merchantRows)
    if (asAdmin) {
      const [insightRow, peopleRows] = await Promise.all([
        api<Insights>("/admin/insights"),
        api<Person[]>("/people"),
      ])
      setInsights(insightRow)
      setPeople(peopleRows)
      setInviteSupervisor((current) => current || peopleRows.find((person) => person.is_superuser)?.id || peopleRows[0]?.id || "")
    }
  }, [])

  useEffect(() => {
    getToken()
      .then(async (token) => {
        if (!token) return
        const me = await api<Profile>("/auth/me")
        setProfile(me)
        setMustChange(Boolean(me.must_change_password))
        setSignedIn(true)
        if (!me.must_change_password) await loadData(me.role === "admin")
      })
      .catch(async () => {
        await clearToken()
        setSignedIn(false)
      })
      .finally(() => setReady(true))
  }, [loadData])

  async function signIn() {
    setLoginError("")
    setBusy(true)
    try {
      const result = await api<{ access_token: string; must_change_password?: boolean }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })
      await setToken(result.access_token)
      const me = await api<Profile>("/auth/me")
      setProfile(me)
      setMustChange(Boolean(result.must_change_password || me.must_change_password))
      setSignedIn(true)
      setScreen("home")
      if (!(result.must_change_password || me.must_change_password)) await loadData(me.role === "admin")
    } catch (error) {
      const message = error instanceof Error ? error.message : ""
      setLoginError(message.includes("401") || message.toLowerCase().includes("password")
        ? "Those credentials were not accepted."
        : "The phone could not reach the server. Try again in a moment.")
    } finally {
      setBusy(false)
    }
  }

  async function requestReset() {
    setLoginError("")
    setForgotNotice("")
    setBusy(true)
    try {
      const result = await api<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      })
      setForgotNotice(result.message)
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "The reset could not be requested.")
    } finally {
      setBusy(false)
    }
  }

  async function saveNewPassword() {
    setLoginError("")
    setBusy(true)
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: password,
          new_password: nextPassword,
          confirm_password: confirmPassword,
        }),
      })
      setMustChange(false)
      setPassword("")
      setNextPassword("")
      setConfirmPassword("")
      if (profile) await loadData(profile.role === "admin")
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "The password was not changed.")
    } finally {
      setBusy(false)
    }
  }

  async function issuePassword(person: Person) {
    setIssuedPassword("")
    try {
      const created = await api<{ temporary_password: string }>(`/people/${person.id}/temporary-password`, { method: "POST" })
      setIssuedPassword(created.temporary_password)
    } catch (error) {
      Alert.alert("Password", error instanceof Error ? error.message : "A temporary password was not issued.")
    }
  }

  async function signOut() {
    await clearToken()
    setSignedIn(false)
    setProfile(null)
    setScreen("home")
  }

  function selectedAccount() {
    return accounts.find((account) => account.category_id === draft.categoryId)
  }

  async function readReceipt(asset: ImagePicker.ImagePickerAsset) {
    const token = await getToken()
    setBusy(true)
    try {
      const upload = await new File(asset.uri).upload(`${API_URL}/expenses/scan-receipt`, {
        uploadType: UploadType.MULTIPART,
        fieldName: "file",
        mimeType: asset.mimeType || "image/jpeg",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          "Bypass-Tunnel-Reminder": "true",
        },
      })
      if (upload.status < 200 || upload.status >= 300) {
        throw new Error(upload.body || `Scan failed (${upload.status})`)
      }
      const scan = JSON.parse(upload.body) as ScanResult
      const suggestion = scan.ai_suggestion
      setDraft({
        merchant: scan.ocr_result.merchant_name || "",
        amount: scan.ocr_result.amount == null ? "" : String(scan.ocr_result.amount),
        date: scan.ocr_result.date ? isoToUS(scan.ocr_result.date) : "",
        categoryId: suggestion?.category_id || "",
        notes: "",
        ocrText: scan.ocr_result.raw_text || "",
        ocrConfidence: String(scan.ocr_result.confidence ?? ""),
        aiConfidence: suggestion ? String(suggestion.confidence) : "",
        receiptUri: asset.uri,
      })
      setScreen("review")
    } catch (error) {
      Alert.alert("Could not read that image", error instanceof Error ? error.message : "The receipt could not be read.")
    } finally {
      setBusy(false)
    }
  }

  async function scanReceipt() {
    if (accounts.length === 0) {
      Alert.alert(
        "No expense accounts",
        "Create an expense account and assign it to a GL account first."
      )
      return
    }
    const permission = await ImagePicker.requestCameraPermissionsAsync()
    if (!permission.granted) {
      Alert.alert("Camera", "Allow the camera to scan a receipt, or use Add screenshot to pick a photo.")
      return
    }
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ["images"],
      quality: 0.9,
    })
    if (result.canceled || !result.assets[0]) return
    await readReceipt(result.assets[0])
  }

  async function addScreenshot() {
    if (accounts.length === 0) {
      Alert.alert(
        "No expense accounts",
        "Create an expense account and assign it to a GL account first."
      )
      return
    }
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!permission.granted) {
      Alert.alert("Photos", "Allow photo access to add a screenshot.")
      return
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.9,
    })
    if (result.canceled || !result.assets[0]) return
    await readReceipt(result.assets[0])
  }

  function openManual() {
    if (accounts.length === 0) {
      Alert.alert(
        "No expense accounts",
        "Create an expense account and assign it to a GL account first."
      )
      return
    }
    setDraft(emptyDraft(accounts[0].category_id))
    setScreen("review")
  }

  async function createReport() {
    const start = usToISO(periodStart)
    const end = usToISO(periodEnd)
    if (!start || !end) {
      Alert.alert("Dates", "Use dates like 08/01/2026.")
      return
    }
    setBusy(true)
    try {
      const report = await api<ReportRow>("/reports", {
        method: "POST",
        body: JSON.stringify({ period_start: start, period_end: end, title: reportTitle.trim() || null }),
      })
      setActiveReport(report)
      setScreen("report")
      await loadData(isAdmin)
    } catch (error) {
      Alert.alert("Not created", error instanceof Error ? error.message : "The report was not created.")
    } finally {
      setBusy(false)
    }
  }

  async function openReport(id: string) {
    setBusy(true)
    try {
      setRejectNotes("")
      setActiveReport(await api<ReportRow>(`/reports/${id}`))
      setScreen("report")
    } catch (error) {
      Alert.alert("Report", error instanceof Error ? error.message : "That report could not be opened.")
    } finally {
      setBusy(false)
    }
  }

  async function addTrip() {
    if (!activeReport || !tripName.trim()) return
    setBusy(true)
    try {
      setActiveReport(await api<ReportRow>(`/reports/${activeReport.id}/trips`, {
        method: "POST",
        body: JSON.stringify({ name: tripName.trim() }),
      }))
      setTripName("")
      await loadData(isAdmin)
    } finally {
      setBusy(false)
    }
  }

  async function submitReport() {
    if (!activeReport) return
    setBusy(true)
    try {
      setActiveReport(await api<ReportRow>(`/reports/${activeReport.id}/submit`, { method: "POST" }))
      await loadData(isAdmin)
    } catch (error) {
      Alert.alert("Not submitted", error instanceof Error ? error.message : "Add an expense before submitting.")
    } finally {
      setBusy(false)
    }
  }

  async function decideReport(action: "approve" | "reject") {
    if (!activeReport) return
    if (action === "reject" && !rejectNotes.trim()) {
      Alert.alert("Note required", "Say what needs to change before sending it back.")
      return
    }
    setBusy(true)
    try {
      setActiveReport(await api<ReportRow>(`/reports/${activeReport.id}/${action}`, {
        method: "POST",
        body: action === "reject" ? JSON.stringify({ notes: rejectNotes.trim() }) : undefined,
      }))
      setRejectNotes("")
      await loadData(true)
    } catch (error) {
      Alert.alert("Not updated", error instanceof Error ? error.message : "The report was not updated.")
    } finally {
      setBusy(false)
    }
  }

  async function downloadReport(format: "xlsx" | "csv") {
    if (!activeReport) return
    try {
      const token = await getToken()
      const destination = new File(Paths.cache, `fubar-${Date.now()}.${format}`)
      const file = await File.downloadFileAsync(
        `${API_URL}/reports/${activeReport.id}/export?file_format=${format}`,
        destination,
        {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            "Bypass-Tunnel-Reminder": "true",
          },
        },
      )
      await Sharing.shareAsync(file.uri, {
        mimeType: format === "csv" ? "text/csv" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        dialogTitle: "Expense report",
      })
    } catch (error) {
      Alert.alert("Download", error instanceof Error ? error.message : "The file could not be saved.")
    }
  }

  async function fileExpense() {
    const amount = Number(draft.amount)
    if (!draft.merchant.trim()) {
      Alert.alert("Merchant required", "Enter the merchant from the receipt.")
      return
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      Alert.alert("Amount required", "Enter the receipt total.")
      return
    }
    const expenseDate = usToISO(draft.date)
    if (!expenseDate) {
      Alert.alert("Date format", "Use a date like 08/02/2026.")
      return
    }
    if (!draft.categoryId) {
      Alert.alert("Account required", "Choose the expense account.")
      return
    }

    setBusy(true)
    try {
      const fields: Record<string, string> = {
        amount: String(amount),
        merchant_name: draft.merchant.trim(),
        expense_date: expenseDate,
        category_id: draft.categoryId,
        currency: "USD",
        notes: draft.notes.trim(),
        receipt_ocr_text: draft.ocrText,
      }
      if (draft.ocrConfidence) fields.ocr_confidence = draft.ocrConfidence
      if (draft.aiConfidence) fields.ai_confidence = draft.aiConfidence
      if (tripId) fields.trip_id = tripId
      if (draft.receiptUri) {
        const token = await getToken()
        const upload = await new File(draft.receiptUri).upload(`${API_URL}/expenses/file`, {
          uploadType: UploadType.MULTIPART,
          fieldName: "file",
          mimeType: "image/jpeg",
          parameters: fields,
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            "Bypass-Tunnel-Reminder": "true",
          },
        })
        if (upload.status < 200 || upload.status >= 300) {
          throw new Error(upload.body || `Submit failed (${upload.status})`)
        }
      } else {
        const body = new FormData()
        Object.entries(fields).forEach(([key, value]) => body.append(key, value))
        await api("/expenses/file", { method: "POST", body })
      }
      await loadData(isAdmin)
      setScreen("home")
    } catch (error) {
      Alert.alert("Not filed", error instanceof Error ? error.message : "The expense was not submitted.")
    } finally {
      setBusy(false)
    }
  }

  async function invitePerson() {
    if (!inviteName.trim() || !inviteEmail.trim()) {
      Alert.alert("Invite", "Enter a name and email.")
      return
    }
    setBusy(true)
    setIssuedPassword("")
    try {
      const created = await api<Person & { temporary_password: string }>("/people", {
        method: "POST",
        body: JSON.stringify({
          full_name: inviteName.trim(),
          email: inviteEmail.trim(),
          role: inviteRole,
          supervisor_id: inviteSupervisor || null,
        }),
      })
      setIssuedPassword(created.temporary_password)
      setInviteName("")
      setInviteEmail("")
      await loadData(true)
    } catch (error) {
      Alert.alert("Invite", error instanceof Error ? error.message : "That person was not invited.")
    } finally {
      setBusy(false)
    }
  }

  async function patchPerson(person: Person, patch: Partial<Person>) {
    setBusy(true)
    try {
      await api(`/people/${person.id}`, { method: "PATCH", body: JSON.stringify(patch) })
      setRenameId("")
      await loadData(true)
    } catch (error) {
      Alert.alert("People", error instanceof Error ? error.message : "That change was not saved.")
    } finally {
      setBusy(false)
    }
  }

  async function mergeMerchant(intoId: string) {
    if (!mergeSource || mergeSource === intoId) return
    setBusy(true)
    try {
      await api(`/merchants/${mergeSource}/merge?into_id=${intoId}`, { method: "POST" })
      setMergeSource("")
      await loadData(true)
    } catch (error) {
      Alert.alert("Merchants", error instanceof Error ? error.message : "Those merchants were not merged.")
    } finally {
      setBusy(false)
    }
  }

  async function createAccount() {
    if (!accountName.trim() || !glCode.trim()) {
      Alert.alert("Account", "Enter the expense name and GL code.")
      return
    }
    setBusy(true)
    try {
      await api("/gl-accounts/expense-accounts", {
        method: "POST",
        body: JSON.stringify({ name: accountName.trim(), gl_code: glCode.trim() }),
      })
      setAccountName("")
      setGlCode("")
      await loadData(true)
    } catch (error) {
      Alert.alert("Account", error instanceof Error ? error.message : "That account was not created.")
    } finally {
      setBusy(false)
    }
  }

  function go(next: Screen | "scan") {
    if (next === "scan") {
      void scanReceipt()
      return
    }
    setScreen(next)
  }

  function Shell({ title, children }: { title: string; children: React.ReactNode }) {
    const tabs: { id: Screen | "scan"; label: string }[] = isAdmin
      ? [
          { id: "home", label: "Inbox" },
          { id: "reports", label: "Reports" },
          { id: "scan", label: "Scan" },
          { id: "people", label: "People" },
          { id: "merchants", label: "Merchants" },
          { id: "accounts", label: "Accounts" },
        ]
      : [
          { id: "home", label: "Home" },
          { id: "reports", label: "Reports" },
          { id: "list", label: "Expenses" },
          { id: "scan", label: "Scan" },
        ]
    return (
      <View style={styles.screen}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <View style={styles.headerTop}>
            <Image source={require("./assets/wildwood-logo.png")} style={styles.logo} />
            <View style={styles.brandBlock}>
              <Text style={styles.brand}>FUBAR</Text>
              <Text style={styles.brandSub}>{title}</Text>
            </View>
            <Pressable onPress={() => void signOut()}>
              <Text style={styles.signOut}>Sign out</Text>
            </Pressable>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.navRow}>
            {tabs.map((tab) => {
              const on = tab.id === screen || (tab.id === "reports" && screen === "report")
              return (
                <Pressable key={tab.id} onPress={() => go(tab.id)} style={[styles.navPill, on && styles.navPillOn]}>
                  <Text style={[styles.navText, on && styles.navTextOn]}>{tab.label}</Text>
                </Pressable>
              )
            })}
          </ScrollView>
        </View>
        {children}
      </View>
    )
  }

  if (!ready || busy) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#1D6FE8" />
      </View>
    )
  }

  if (signedIn && mustChange) {
    return (
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <StatusBar style="dark" />
        <View style={styles.form}>
          <Image source={require("./assets/wildwood-logo.png")} style={styles.loginLogo} />
          <Text style={styles.wordmark}>FUBAR</Text>
          <Text style={styles.hint}>The temporary password works once. Pick your own to continue.</Text>
          <Text style={styles.label}>Temporary password</Text>
          <TextInput value={password} onChangeText={setPassword} secureTextEntry style={styles.input} />
          <Text style={styles.label}>New password</Text>
          <TextInput value={nextPassword} onChangeText={setNextPassword} secureTextEntry style={styles.input} />
          <Text style={styles.label}>Confirm password</Text>
          <TextInput value={confirmPassword} onChangeText={setConfirmPassword} secureTextEntry style={styles.input} />
          {loginError ? <Text style={styles.error}>{loginError}</Text> : null}
          <Pressable style={styles.primary} onPress={() => void saveNewPassword()}>
            <Text style={styles.primaryText}>Save password</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    )
  }

  if (!signedIn) {
    return (
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <StatusBar style="dark" />
        <View style={styles.form}>
          <Image source={require("./assets/wildwood-logo.png")} style={styles.loginLogo} />
          <Text style={styles.wordmark}>FUBAR</Text>
          <Text style={styles.hint}>Expense reports for Wildwood Ingredients.</Text>
          <Text style={styles.label}>Email</Text>
          <TextInput value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" style={styles.input} />
          {forgotMode ? (
            <>
              <Text style={styles.hint}>We will email a reset link if that account exists.</Text>
              {forgotNotice ? <Text style={styles.hint}>{forgotNotice}</Text> : null}
              {loginError ? <Text style={styles.error}>{loginError}</Text> : null}
              <Pressable style={styles.primary} onPress={() => void requestReset()}>
                <Text style={styles.primaryText}>Send reset link</Text>
              </Pressable>
              <Pressable onPress={() => { setForgotMode(false); setLoginError(""); setForgotNotice("") }}>
                <Text style={styles.linkText}>Back to sign in</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={styles.label}>Password</Text>
              <TextInput value={password} onChangeText={setPassword} secureTextEntry style={styles.input} />
              {loginError ? <Text style={styles.error}>{loginError}</Text> : null}
              <Pressable style={styles.primary} onPress={() => void signIn()}>
                <Text style={styles.primaryText}>Sign in</Text>
              </Pressable>
              <Pressable onPress={() => { setForgotMode(true); setLoginError("") }}>
                <Text style={styles.linkText}>Forgot password?</Text>
              </Pressable>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    )
  }

  if (screen === "review") {
    const account = selectedAccount()
    return (
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <StatusBar style="light" />
        <View style={styles.header}>
          <Pressable onPress={() => setScreen("home")}>
            <Text style={styles.signOut}>Back</Text>
          </Pressable>
          <Text style={styles.brand}>Review receipt</Text>
        </View>
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          {draft.ocrText.trim().length > 0 && draft.ocrText.trim().length < 80 ? (
            <Text style={styles.hint}>
              This photo was hard to read. Lay the receipt flat, fill the frame, and scan again.
            </Text>
          ) : null}
          <Text style={styles.label}>Merchant</Text>
          <TextInput
            value={draft.merchant}
            onChangeText={(merchant) => setDraft({ ...draft, merchant })}
            style={styles.input}
          />
          <Text style={styles.label}>Total</Text>
          <TextInput
            value={draft.amount}
            onChangeText={(amount) => setDraft({ ...draft, amount })}
            keyboardType="decimal-pad"
            style={styles.input}
          />
          <Text style={styles.label}>Date</Text>
          <TextInput
            value={draft.date}
            onChangeText={(date) => setDraft({ ...draft, date })}
            placeholder="MM/DD/YYYY"
            placeholderTextColor="#94a3b8"
            autoCapitalize="none"
            style={styles.input}
          />
          <Text style={styles.label}>Expense account</Text>
          {!draft.categoryId ? (
            <Text style={styles.hint}>No expense account matched this receipt. Choose one.</Text>
          ) : null}
          <View style={styles.chips}>
            {accounts.map((item) => (
              <Pressable
                key={item.category_id}
                onPress={() => setDraft({ ...draft, categoryId: item.category_id })}
                style={[styles.chip, draft.categoryId === item.category_id && styles.chipOn]}
              >
                <Text style={[styles.chipText, draft.categoryId === item.category_id && styles.chipTextOn]}>
                  {item.name}
                </Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.card}>
            <Text style={styles.detailLabel}>GL account</Text>
            <Text style={styles.detailValue}>
              {account?.gl_code ? `${account.gl_code} · ${account.gl_name}` : "Choose an expense account"}
            </Text>
          </View>
          <Text style={styles.label}>Trip, optional</Text>
          <View style={styles.chips}>
            <Pressable onPress={() => setTripId("")} style={[styles.chip, tripId === "" && styles.chipOn]}>
              <Text style={[styles.chipText, tripId === "" && styles.chipTextOn]}>No trip</Text>
            </Pressable>
            {reports
              .filter((report) => report.status === "draft" || report.status === "rejected")
              .flatMap((report) => report.trips.map((trip) => ({ ...trip, reportTitle: report.title })))
              .map((trip) => (
                <Pressable key={trip.id} onPress={() => setTripId(trip.id)} style={[styles.chip, tripId === trip.id && styles.chipOn]}>
                  <Text style={[styles.chipText, tripId === trip.id && styles.chipTextOn]}>
                    {trip.reportTitle}: {trip.name}
                  </Text>
                </Pressable>
              ))}
          </View>
          <Pressable style={styles.primary} onPress={() => void fileExpense()}>
            <Text style={styles.primaryText}>Submit to expense report</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    )
  }

  if (screen === "report" && activeReport) {
    const ownsReport = activeReport.user_id === profile?.id
    const canSubmit = ownsReport && (activeReport.status === "draft" || activeReport.status === "rejected")
    const canReview = isAdmin && activeReport.status === "submitted"
    return (
      <Shell title="Report">
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => setScreen("reports")}>
            <Text style={styles.back}>Back to reports</Text>
          </Pressable>
          <Text style={styles.title}>{activeReport.title}</Text>
          <Text style={styles.hint}>
            {activeReport.user_name} · {prettyDate(activeReport.period_start)} – {prettyDate(activeReport.period_end)} · {activeReport.status} · {money(activeReport.total)}
          </Text>
          {activeReport.review_notes ? <Text style={styles.error}>{activeReport.review_notes}</Text> : null}
          <View style={styles.card}>
            <Text style={styles.section}>By GL account</Text>
            <Bars rows={activeReport.by_gl} />
            <Text style={styles.section}>By merchant</Text>
            <Bars rows={activeReport.by_merchant} />
          </View>
          <Text style={styles.label}>Entries</Text>
          {(activeReport.expenses || []).map((line) => (
            <View key={line.id} style={styles.card}>
              <View style={styles.barLabel}>
                <Text style={styles.merchant}>{line.merchant_name}</Text>
                <Text style={styles.amount}>{money(line.amount)}</Text>
              </View>
              <Text style={styles.meta}>
                {prettyDate(line.expense_date)}
                {line.category_name ? ` · ${line.category_name}` : ""}
                {line.gl_code ? ` · ${line.gl_code}` : ""}
                {line.trip_name ? ` · ${line.trip_name}` : ""}
              </Text>
              {line.notes ? <Text style={styles.meta}>{line.notes}</Text> : null}
              {line.receipt_url ? (
                <Image source={{ uri: mediaUrl(line.receipt_url) }} style={styles.receipt} />
              ) : (
                <Text style={styles.meta}>No receipt photo</Text>
              )}
            </View>
          ))}
          <View style={styles.rowButtons}>
            <Pressable style={[styles.secondary, styles.half]} onPress={() => void downloadReport("xlsx")}>
              <Text style={styles.secondaryText}>Excel</Text>
            </Pressable>
            <Pressable style={[styles.secondary, styles.half]} onPress={() => void downloadReport("csv")}>
              <Text style={styles.secondaryText}>CSV</Text>
            </Pressable>
          </View>
          <Text style={styles.label}>Trips</Text>
          {activeReport.trips.map((trip) => (
            <View key={trip.id} style={styles.row}>
              <View style={styles.rowBody}>
                <Text style={styles.merchant}>{trip.name}</Text>
                <Text style={styles.meta}>{trip.by_gl.map((row) => row.name).join(", ") || "No expenses yet"}</Text>
              </View>
              <Text style={styles.amount}>{money(trip.total)}</Text>
            </View>
          ))}
          <TextInput value={tripName} onChangeText={setTripName} placeholder="Trip name" placeholderTextColor="#94a3b8" style={styles.input} />
          <Pressable style={styles.secondary} onPress={() => void addTrip()}>
            <Text style={styles.secondaryText}>Add trip</Text>
          </Pressable>
          <Pressable style={styles.secondary} onPress={() => void addScreenshot()}>
            <Text style={styles.secondaryText}>Add screenshot</Text>
          </Pressable>
          {canSubmit ? (
            <Pressable style={styles.primary} onPress={() => void submitReport()}>
              <Text style={styles.primaryText}>{activeReport.status === "rejected" ? "Resubmit" : "Submit for approval"}</Text>
            </Pressable>
          ) : null}
          {canReview ? (
            <View>
              <Text style={styles.label}>Send back with a note</Text>
              <TextInput
                value={rejectNotes}
                onChangeText={setRejectNotes}
                placeholder="What should they fix?"
                placeholderTextColor="#94a3b8"
                style={styles.input}
              />
              <Pressable style={styles.secondary} onPress={() => void decideReport("reject")}>
                <Text style={styles.secondaryText}>Send back</Text>
              </Pressable>
              <Pressable style={styles.primary} onPress={() => void decideReport("approve")}>
                <Text style={styles.primaryText}>Approve</Text>
              </Pressable>
            </View>
          ) : null}
        </ScrollView>
      </Shell>
    )
  }

  if (screen === "people" && isAdmin) {
    const ids = new Set(people.map((person) => person.id))
    const renderBranch = (parentId: string | null, depth: number, trail: string[]): ReactNode => {
      const nodes = people.filter((person) => {
        if (trail.includes(person.id)) return false
        const isRoot = !person.supervisor_id || person.supervisor_id === person.id || !ids.has(person.supervisor_id)
        return parentId ? person.supervisor_id === parentId && person.id !== parentId : isRoot
      })
      return nodes.map((person) => (
        <View key={person.id}>
          <Pressable
            style={[styles.row, { marginLeft: depth * 16 }]}
            onPress={() => setChartPerson(chartPerson === person.id ? "" : person.id)}
          >
            <View style={styles.rowBody}>
              <Text style={styles.merchant}>{person.full_name}</Text>
              <Text style={styles.meta}>{person.role}{person.is_active ? "" : " · inactive"} · {directReports(people, person.id)} below</Text>
            </View>
          </Pressable>
          {chartPerson === person.id ? (
            <View style={[styles.card, { marginLeft: depth * 16 }]}>
              <Text style={styles.meta}>{person.email}</Text>
              {issuedPassword && chartPerson === person.id ? <Text style={styles.detailValue}>Temporary password, shown once: {issuedPassword}</Text> : null}
              {renameId === person.id ? <TextInput value={renameValue} onChangeText={setRenameValue} style={styles.input} /> : null}
              <View style={styles.rowButtons}>
                <Pressable
                  style={[styles.secondary, styles.half]}
                  onPress={() => {
                    if (renameId === person.id) void patchPerson(person, { full_name: renameValue })
                    else {
                      setRenameId(person.id)
                      setRenameValue(person.full_name)
                    }
                  }}
                >
                  <Text style={styles.secondaryText}>{renameId === person.id ? "Save name" : "Rename"}</Text>
                </Pressable>
                <Pressable
                  style={[styles.secondary, styles.half]}
                  onPress={() => void patchPerson(person, { role: person.role === "admin" ? "sales" : "admin" })}
                >
                  <Text style={styles.secondaryText}>{person.role === "admin" ? "Make sales" : "Make admin"}</Text>
                </Pressable>
              </View>
              <Pressable style={styles.secondary} onPress={() => void issuePassword(person)}>
                <Text style={styles.secondaryText}>Issue temporary password</Text>
              </Pressable>
              {person.id !== profile?.id ? (
                <Pressable style={styles.secondary} onPress={() => void patchPerson(person, { is_active: !person.is_active })}>
                  <Text style={styles.secondaryText}>{person.is_active ? "Deactivate" : "Reactivate"}</Text>
                </Pressable>
              ) : null}
            </View>
          ) : null}
          {renderBranch(person.id, depth + 1, [...trail, person.id])}
        </View>
      ))
    }
    return (
      <Shell title="People">
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>People</Text>
          <Text style={styles.hint}>Each person sits under their supervisor. Tap a name to change them.</Text>
          {renderBranch(null, 0, [])}
          <Pressable style={styles.secondary} onPress={() => setShowInvite(!showInvite)}>
            <Text style={styles.secondaryText}>{showInvite ? "Close invite" : "Invite someone"}</Text>
          </Pressable>
          {showInvite ? (
            <View>
              {issuedPassword ? (
                <View style={styles.card}>
                  <Text style={styles.detailLabel}>Temporary password</Text>
                  <Text style={styles.detailValue}>{issuedPassword}</Text>
                </View>
              ) : null}
              <Text style={styles.label}>Name</Text>
              <TextInput value={inviteName} onChangeText={setInviteName} style={styles.input} />
              <Text style={styles.label}>Email</Text>
              <TextInput value={inviteEmail} onChangeText={setInviteEmail} autoCapitalize="none" keyboardType="email-address" style={styles.input} />
              <View style={styles.chips}>
                {["sales", "admin"].map((role) => (
                  <Pressable key={role} onPress={() => setInviteRole(role)} style={[styles.chip, inviteRole === role && styles.chipOn]}>
                    <Text style={[styles.chipText, inviteRole === role && styles.chipTextOn]}>{role}</Text>
                  </Pressable>
                ))}
              </View>
              <Text style={styles.label}>Supervisor</Text>
              <View style={styles.chips}>
                {people.filter((person) => person.is_active).map((person) => (
                  <Pressable key={person.id} onPress={() => setInviteSupervisor(person.id)} style={[styles.chip, inviteSupervisor === person.id && styles.chipOn]}>
                    <Text style={[styles.chipText, inviteSupervisor === person.id && styles.chipTextOn]}>{person.full_name}</Text>
                  </Pressable>
                ))}
              </View>
              <Pressable style={styles.primary} onPress={() => void invitePerson()}>
                <Text style={styles.primaryText}>Invite</Text>
              </Pressable>
            </View>
          ) : null}
        </ScrollView>
      </Shell>
    )
  }

  if (screen === "merchants" && isAdmin) {
    const needle = merchantQuery.trim().toLowerCase()
    const visible = merchants.filter((merchant) => merchant.name.toLowerCase().includes(needle))
    const letters = Array.from(new Set(visible.map((merchant) => (merchant.name[0] || "#").toUpperCase()))).sort()
    return (
      <Shell title="Merchants">
        <ScrollView contentContainerStyle={styles.form}>
          <Text style={styles.title}>Merchants</Text>
          <Text style={styles.hint}>Open a letter. Tap one merchant, then another, to merge the first into the second.</Text>
          <TextInput value={merchantQuery} onChangeText={setMerchantQuery} placeholder="Search merchants" placeholderTextColor="#94a3b8" style={styles.input} />
          {letters.map((letter) => {
            const rows = visible.filter((merchant) => (merchant.name[0] || "#").toUpperCase() === letter)
            const total = rows.reduce((sum, merchant) => sum + merchant.amount, 0)
            const open = needle.length > 0 || openLetter === letter
            return (
              <View key={letter}>
                <Pressable style={styles.row} onPress={() => setOpenLetter(openLetter === letter ? "" : letter)}>
                  <View style={styles.rowBody}>
                    <Text style={styles.merchant}>{letter}</Text>
                    <Text style={styles.meta}>{rows.length} {rows.length === 1 ? "merchant" : "merchants"}</Text>
                  </View>
                  <Text style={styles.amount}>{money(total)}</Text>
                </Pressable>
                {open ? rows.map((merchant) => {
                  const selected = merchant.id != null && mergeSource === merchant.id
                  return (
                    <Pressable
                      key={merchant.id || merchant.name}
                      style={[styles.row, { marginLeft: 16 }, selected && styles.rowOn]}
                      onPress={() => {
                        if (!merchant.id) return
                        if (!mergeSource) setMergeSource(merchant.id)
                        else void mergeMerchant(merchant.id)
                      }}
                    >
                      <View style={styles.rowBody}>
                        <Text style={styles.merchant}>{merchant.name}</Text>
                        <Text style={styles.meta}>{merchant.count} receipts{selected ? " · selected" : ""}</Text>
                      </View>
                      <Text style={styles.amount}>{money(merchant.amount)}</Text>
                    </Pressable>
                  )
                }) : null}
              </View>
            )
          })}
        </ScrollView>
      </Shell>
    )
  }

  if (screen === "accounts" && isAdmin) {
    return (
      <Shell title="Accounts">
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>Expense accounts</Text>
          <Text style={styles.hint}>Each name is what people pick on a receipt. It maps to one GL account.</Text>
          <Text style={styles.label}>Expense name</Text>
          <TextInput value={accountName} onChangeText={setAccountName} style={styles.input} />
          <Text style={styles.label}>GL code</Text>
          <TextInput value={glCode} onChangeText={setGlCode} style={styles.input} />
          <Pressable style={styles.primary} onPress={() => void createAccount()}>
            <Text style={styles.primaryText}>Add account</Text>
          </Pressable>
          {accounts.map((account) => (
            <View key={account.category_id} style={styles.row}>
              <View style={styles.rowBody}>
                <Text style={styles.merchant}>{account.name}</Text>
                <Text style={styles.meta}>{account.gl_code ? `${account.gl_code} · ${account.gl_name}` : "No GL mapping"}</Text>
              </View>
            </View>
          ))}
        </ScrollView>
      </Shell>
    )
  }

  if (screen === "list") {
    const months = Array.from(new Set(expenses.map((item) => item.expense_date.slice(0, 7)))).sort().reverse()
    return (
      <Shell title="Expenses">
        <ScrollView contentContainerStyle={styles.form}>
          <Text style={styles.title}>Expenses</Text>
          <Text style={styles.hint}>Grouped by month. Open a month to see the receipts.</Text>
          <Pressable style={styles.secondary} onPress={openManual}>
            <Text style={styles.secondaryText}>Enter manually</Text>
          </Pressable>
          {months.length === 0 ? <Text style={styles.empty}>No expenses filed yet.</Text> : null}
          {months.map((month) => {
            const rows = expenses.filter((item) => item.expense_date.startsWith(month))
            const total = rows.reduce((sum, item) => sum + Number(item.amount), 0)
            const open = openGroup === month
            const [year, monthNumber] = month.split("-").map(Number)
            const label = new Date(year, monthNumber - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" })
            return (
              <View key={month}>
                <Pressable style={styles.row} onPress={() => setOpenGroup(open ? "" : month)}>
                  <View style={styles.rowBody}>
                    <Text style={styles.merchant}>{label}</Text>
                    <Text style={styles.meta}>{rows.length} expenses</Text>
                  </View>
                  <Text style={styles.amount}>{money(total)}</Text>
                </Pressable>
                {open ? rows.map((item) => (
                  <View key={item.id} style={[styles.row, { marginLeft: 16 }]}>
                    <View style={styles.rowBody}>
                      <Text style={styles.merchant}>{item.merchant_name || "Receipt"}</Text>
                      <Text style={styles.meta}>
                        {item.category?.name || "Unassigned"}
                        {item.gl_account ? ` · ${item.gl_account.account_code}` : ""} · {prettyDate(item.expense_date)}
                      </Text>
                    </View>
                    <View style={styles.rowEnd}>
                      <Text style={styles.amount}>{money(item.amount)}</Text>
                      <Text style={styles.status}>{STATUS_LABEL[item.status]}</Text>
                    </View>
                  </View>
                )) : null}
              </View>
            )
          })}
        </ScrollView>
      </Shell>
    )
  }

  if (screen === "reports") {
    const groups = isAdmin
      ? Array.from(new Set(reports.map((report) => report.user_name))).sort().map((name) => ({
          key: name,
          title: name,
          rows: reports.filter((report) => report.user_name === name),
        }))
      : ["draft", "submitted", "rejected", "approved"].map((status) => ({
          key: status,
          title: status,
          rows: reports.filter((report) => report.status === status),
        })).filter((group) => group.rows.length > 0)
    return (
      <Shell title="Reports">
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>Reports</Text>
          <Text style={styles.hint}>{isAdmin ? "Grouped by person. Open a name to see their reports." : "Grouped by status."}</Text>
          {groups.map((group) => {
            const total = group.rows.reduce((sum, report) => sum + report.total, 0)
            const open = openGroup === `report-${group.key}`
            return (
              <View key={group.key}>
                <Pressable style={styles.row} onPress={() => setOpenGroup(open ? "" : `report-${group.key}`)}>
                  <View style={styles.rowBody}>
                    <Text style={styles.merchant}>{group.title}</Text>
                    <Text style={styles.meta}>{group.rows.length} {group.rows.length === 1 ? "report" : "reports"}</Text>
                  </View>
                  <Text style={styles.amount}>{money(total)}</Text>
                </Pressable>
                {open ? group.rows.map((report) => (
                  <Pressable key={report.id} style={[styles.row, { marginLeft: 16 }]} onPress={() => void openReport(report.id)}>
                    <View style={styles.rowBody}>
                      <Text style={styles.merchant}>{report.title}</Text>
                      <Text style={styles.meta}>{report.status} · {prettyDate(report.period_start)}</Text>
                    </View>
                    <Text style={styles.amount}>{money(report.total)}</Text>
                  </Pressable>
                )) : null}
              </View>
            )
          })}
          <Text style={styles.label}>New report</Text>
          <TextInput value={reportTitle} onChangeText={setReportTitle} placeholder="Title, optional" placeholderTextColor="#94a3b8" style={styles.input} />
          <TextInput value={periodStart} onChangeText={setPeriodStart} placeholder="Start MM/DD/YYYY" placeholderTextColor="#94a3b8" style={styles.input} />
          <TextInput value={periodEnd} onChangeText={setPeriodEnd} placeholder="End MM/DD/YYYY" placeholderTextColor="#94a3b8" style={styles.input} />
          <Pressable style={styles.primary} onPress={() => void createReport()}>
            <Text style={styles.primaryText}>Create report</Text>
          </Pressable>
        </ScrollView>
      </Shell>
    )
  }

  return (
    <Shell title={isAdmin ? "Inbox" : "Home"}>
      <ScrollView contentContainerStyle={styles.form}>
        <Text style={styles.eyebrow}>{isAdmin ? "Company spend" : profile?.full_name || "Your dashboard"}</Text>
        <Text style={styles.title}>{money(isAdmin ? insights?.spend || 0 : summary?.spend || 0)}</Text>
        <Text style={styles.hint}>
          {isAdmin
            ? `${money(insights?.this_month || 0)} this month · ${insights?.awaiting_review || 0} waiting on review`
            : `${summary?.open_reports || 0} open reports · ${summary?.awaiting_review || 0} waiting on a supervisor`}
        </Text>
        {notices.filter((notice) => !notice.read).slice(0, 3).map((notice) => (
          <Pressable
            key={notice.id}
            style={styles.row}
            onPress={() => {
              void api(`/notices/${notice.id}/read`, { method: "POST" })
              setNotices(notices.map((item) => item.id === notice.id ? { ...item, read: true } : item))
            }}
          >
            <Text style={styles.meta}>{notice.message}</Text>
          </Pressable>
        ))}
        {isAdmin && insights ? (
          <View style={styles.card}>
            <Text style={styles.section}>Last months</Text>
            <Bars rows={insights.monthly.map((row) => ({ name: row.month, amount: row.amount }))} />
            <Text style={styles.section}>By person</Text>
            <Bars rows={insights.by_person} />
            <Text style={styles.section}>By merchant</Text>
            <Bars rows={insights.by_merchant} />
            <Text style={styles.section}>By GL account</Text>
            <Bars rows={insights.by_gl} />
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.section}>By GL account</Text>
            <Bars rows={summary?.by_gl || []} />
            <Text style={styles.section}>By merchant</Text>
            <Bars rows={(summary?.by_merchant || []).slice(0, 6)} />
          </View>
        )}
        <Pressable style={styles.primary} onPress={() => void scanReceipt()}>
          <Text style={styles.primaryText}>Scan receipt</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={() => void addScreenshot()}>
          <Text style={styles.secondaryText}>Add screenshot</Text>
        </Pressable>
        <Pressable style={styles.secondary} onPress={openManual}>
          <Text style={styles.secondaryText}>Enter manually</Text>
        </Pressable>
        {(isAdmin ? reports.filter((report) => report.status === "submitted") : reports).slice(0, 5).map((report) => (
          <Pressable key={report.id} style={styles.row} onPress={() => void openReport(report.id)}>
            <View style={styles.rowBody}>
              <Text style={styles.merchant}>{report.title}</Text>
              <Text style={styles.meta}>
                {isAdmin ? `${report.user_name} · ` : ""}{report.status} · {prettyDate(report.period_start)}
              </Text>
            </View>
            <Text style={styles.amount}>{money(report.total)}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </Shell>
  )
}

const styles = StyleSheet.create({
  loading: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#F4F7FB" },
  screen: { flex: 1, backgroundColor: "#F4F7FB" },
  header: { backgroundColor: "#0B3D73", paddingTop: 54, paddingBottom: 12, paddingHorizontal: 16 },
  headerTop: { flexDirection: "row", alignItems: "center", gap: 10 },
  logo: { width: 56, height: 56, resizeMode: "contain" },
  loginLogo: { width: 96, height: 96, resizeMode: "contain", alignSelf: "center" },
  brandBlock: { flex: 1 },
  brand: { color: "#ffffff", fontSize: 22, fontWeight: "900", letterSpacing: 3 },
  brandSub: { color: "#BFDBFE", fontSize: 12, fontWeight: "700", textTransform: "uppercase", letterSpacing: 1 },
  wordmark: { marginTop: 8, textAlign: "center", color: "#0B3D73", fontSize: 28, fontWeight: "900", letterSpacing: 4 },
  signOut: { color: "#BFDBFE", fontWeight: "700" },
  linkText: { color: "#1D6FE8", fontWeight: "700", textAlign: "center" },
  navRow: { gap: 8, paddingTop: 12 },
  navPill: { borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8, backgroundColor: "rgba(255,255,255,0.12)" },
  navPillOn: { backgroundColor: "#ffffff" },
  navText: { color: "#DBEAFE", fontWeight: "700" },
  navTextOn: { color: "#0B3D73" },
  list: { paddingHorizontal: 16, paddingBottom: 32 },
  form: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 40 },
  eyebrow: { color: "#5C6B80", fontSize: 14, fontWeight: "700" },
  title: { marginTop: 4, fontSize: 32, fontWeight: "800", color: "#0B1F33" },
  hint: { marginTop: 8, color: "#5C6B80", lineHeight: 20 },
  card: { backgroundColor: "#ffffff", borderRadius: 16, padding: 16, marginTop: 12 },
  section: { marginTop: 12, marginBottom: 8, color: "#0B3D73", fontWeight: "800" },
  bars: { gap: 10 },
  barLabel: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  track: { height: 8, borderRadius: 99, backgroundColor: "#E6EEF8", marginTop: 4 },
  fill: { height: 8, borderRadius: 99, backgroundColor: "#1D6FE8" },
  row: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    marginTop: 10,
    flexDirection: "row",
    alignItems: "center",
  },
  rowOn: { borderWidth: 2, borderColor: "#1D6FE8" },
  rowBody: { flex: 1, paddingRight: 12 },
  rowEnd: { alignItems: "flex-end" },
  rowButtons: { flexDirection: "row", gap: 8, marginTop: 8 },
  half: { flex: 1, marginTop: 0 },
  merchant: { fontSize: 16, fontWeight: "800", color: "#0B1F33" },
  meta: { marginTop: 4, color: "#5C6B80" },
  amount: { fontSize: 15, fontWeight: "800", color: "#0B1F33" },
  status: { marginTop: 4, color: "#B45309", fontWeight: "700" },
  empty: { marginTop: 24, color: "#5C6B80", textAlign: "center" },
  back: { color: "#1D6FE8", fontWeight: "800", fontSize: 16, marginBottom: 8 },
  label: { marginTop: 16, marginBottom: 8, color: "#0B3D73", fontWeight: "800" },
  input: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    color: "#0B1F33",
    marginTop: 8,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 },
  chip: { backgroundColor: "#E6EEF8", borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  chipOn: { backgroundColor: "#0B3D73" },
  chipText: { color: "#0B3D73", fontWeight: "700" },
  chipTextOn: { color: "#ffffff" },
  primary: {
    marginTop: 16,
    backgroundColor: "#1D6FE8",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  primaryText: { color: "#ffffff", fontSize: 16, fontWeight: "800" },
  secondary: {
    marginTop: 10,
    backgroundColor: "#ffffff",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  secondaryText: { color: "#0B3D73", fontSize: 16, fontWeight: "800" },
  detailLabel: { color: "#5C6B80", fontSize: 13, fontWeight: "700" },
  detailValue: { marginTop: 4, color: "#0B1F33", fontSize: 16, fontWeight: "700" },
  receipt: { marginTop: 10, width: "100%", height: 180, borderRadius: 12, backgroundColor: "#F4F7FB", resizeMode: "contain" },
  error: { marginTop: 12, color: "#b91c1c" },
})
