import { useCallback, useEffect, useState } from "react"
import {
  ActivityIndicator,
  Alert,
  FlatList,
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
import { File, UploadType } from "expo-file-system"
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

export default function App() {
  const [ready, setReady] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [email, setEmail] = useState("field@example.com")
  const [password, setPassword] = useState("")
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [screen, setScreen] = useState<"list" | "review">("list")
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [busy, setBusy] = useState(false)
  const [loginError, setLoginError] = useState("")

  const loadData = useCallback(async () => {
    const [expenseRows, accountRows] = await Promise.all([
      api<Expense[]>("/expenses"),
      api<Account[]>("/gl-accounts/expense-accounts"),
    ])
    setExpenses(expenseRows)
    setAccounts(accountRows)
  }, [])

  useEffect(() => {
    getToken()
      .then(async (token) => {
        if (!token) return
        await api("/auth/me")
        setSignedIn(true)
        await loadData()
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
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      })
      await setToken(result.access_token)
      setSignedIn(true)
      await loadData()
    } catch {
      setLoginError("Those credentials were not accepted.")
    } finally {
      setBusy(false)
    }
  }

  function selectedAccount() {
    return accounts.find((account) => account.category_id === draft.categoryId)
  }

  async function scanReceipt() {
    if (accounts.length === 0) {
      Alert.alert(
        "No expense accounts",
        "Create an expense account in the admin portal and assign it to a GL account first."
      )
      return
    }
    const permission = await ImagePicker.requestCameraPermissionsAsync()
    const result = permission.granted
      ? await ImagePicker.launchCameraAsync({
          mediaTypes: ["images"],
          quality: 0.9,
        })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ["images"],
          quality: 0.9,
        })
    if (result.canceled || !result.assets[0]) return

    const asset = result.assets[0]
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
      Alert.alert("Scan failed", error instanceof Error ? error.message : "The receipt could not be read.")
    } finally {
      setBusy(false)
    }
  }

  function openManual() {
    if (accounts.length === 0) {
      Alert.alert(
        "No expense accounts",
        "Create an expense account in the admin portal and assign it to a GL account first."
      )
      return
    }
    setDraft(emptyDraft(accounts[0].category_id))
    setScreen("review")
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
      await loadData()
      setScreen("list")
    } catch (error) {
      Alert.alert("Not filed", error instanceof Error ? error.message : "The expense was not submitted.")
    } finally {
      setBusy(false)
    }
  }

  if (!ready || busy) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#1d4ed8" />
      </View>
    )
  }

  if (!signedIn) {
    return (
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <StatusBar style="dark" />
        <View style={styles.form}>
          <Text style={styles.title}>Expenses</Text>
          <Text style={styles.hint}>Sign in with the field account to scan receipts.</Text>
          <Text style={styles.label}>Email</Text>
          <TextInput value={email} onChangeText={setEmail} autoCapitalize="none" style={styles.input} />
          <Text style={styles.label}>Password</Text>
          <TextInput value={password} onChangeText={setPassword} secureTextEntry style={styles.input} />
          {loginError ? <Text style={styles.error}>{loginError}</Text> : null}
          <Pressable style={styles.primary} onPress={() => void signIn()}>
            <Text style={styles.primaryText}>Sign in</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    )
  }

  if (screen === "review") {
    const account = selectedAccount()
    return (
      <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <StatusBar style="dark" />
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => setScreen("list")}>
            <Text style={styles.back}>Back</Text>
          </Pressable>
          <Text style={styles.title}>Review receipt</Text>
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
          <View style={styles.detailCard}>
            <Text style={styles.detailLabel}>GL account</Text>
            <Text style={styles.detailValue}>
              {account?.gl_code ? `${account.gl_code} · ${account.gl_name}` : "Choose an expense account"}
            </Text>
          </View>
          <Pressable style={styles.primary} onPress={() => void fileExpense()}>
            <Text style={styles.primaryText}>Submit to expense report</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    )
  }

  return (
    <View style={styles.screen}>
      <StatusBar style="dark" />
      <FlatList
        data={expenses}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View>
            <Text style={styles.eyebrow}>This month</Text>
            <Text style={styles.title}>Expenses</Text>
            <Text style={styles.hint}>
              Scan a receipt. It is filed under the expense account chosen from the admin list, on that account's GL.
            </Text>
          </View>
        }
        ListEmptyComponent={<Text style={styles.empty}>No expenses filed yet.</Text>}
        renderItem={({ item }) => (
          <View style={styles.row}>
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
        )}
      />
      <View style={styles.actions}>
        <Pressable style={[styles.primary, styles.actionButton]} onPress={() => void scanReceipt()}>
          <Text style={styles.primaryText}>Scan receipt</Text>
        </Pressable>
        <Pressable style={[styles.secondary, styles.actionButton]} onPress={openManual}>
          <Text style={styles.secondaryText}>Enter manually</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  loading: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#f4f6f8" },
  screen: { flex: 1, backgroundColor: "#f4f6f8" },
  list: { paddingTop: 64, paddingHorizontal: 20, paddingBottom: 150 },
  form: { paddingTop: 64, paddingHorizontal: 20, paddingBottom: 48 },
  eyebrow: { color: "#64748b", fontSize: 14, fontWeight: "600" },
  title: { marginTop: 4, fontSize: 34, fontWeight: "700", color: "#0f172a" },
  hint: { marginTop: 8, color: "#64748b", lineHeight: 20 },
  row: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    marginTop: 10,
    flexDirection: "row",
    alignItems: "center",
  },
  rowBody: { flex: 1, paddingRight: 12 },
  rowEnd: { alignItems: "flex-end" },
  merchant: { fontSize: 17, fontWeight: "700", color: "#0f172a" },
  meta: { marginTop: 4, color: "#64748b" },
  amount: { fontSize: 16, fontWeight: "700", color: "#0f172a" },
  status: { marginTop: 4, color: "#b45309", fontWeight: "700" },
  empty: { marginTop: 24, color: "#64748b", textAlign: "center" },
  actions: { position: "absolute", left: 20, right: 20, bottom: 24, gap: 10 },
  actionButton: { marginTop: 0 },
  back: { color: "#1d4ed8", fontWeight: "700", fontSize: 16, marginBottom: 12 },
  label: { marginTop: 16, marginBottom: 8, color: "#334155", fontWeight: "700" },
  input: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    color: "#0f172a",
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { backgroundColor: "#e2e8f0", borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  chipOn: { backgroundColor: "#1d4ed8" },
  chipText: { color: "#334155", fontWeight: "600" },
  chipTextOn: { color: "#ffffff" },
  primary: {
    marginTop: 16,
    backgroundColor: "#1d4ed8",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  primaryText: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  secondary: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  secondaryText: { color: "#1d4ed8", fontSize: 16, fontWeight: "700" },
  detailCard: { marginTop: 16, backgroundColor: "#ffffff", borderRadius: 16, padding: 16 },
  detailLabel: { color: "#64748b", fontSize: 13, fontWeight: "700" },
  detailValue: { marginTop: 4, color: "#0f172a", fontSize: 16 },
  error: { marginTop: 12, color: "#b91c1c" },
})
