import AsyncStorage from "@react-native-async-storage/async-storage"
import { API_URL } from "./config"

const TOKEN_KEY = "access_token"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function readDetail(body: string, status: number) {
  const text = (body || "").trim()
  if (!text) return `Request failed (${status})`
  if (text.startsWith("<")) return "The phone could not reach the server. Try again in a moment."
  try {
    const parsed = JSON.parse(text) as { detail?: unknown }
    const detail = parsed.detail
    if (typeof detail === "string") return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { loc?: unknown[]; msg?: string }
      const loc = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1] || "") : ""
      if (loc.includes("date") || (first.msg || "").toLowerCase().includes("date")) {
        return "That date is not a real calendar day. Use a date like 08/02/2026."
      }
      return first.msg || `Request failed (${status})`
    }
  } catch {
    return text
  }
  return text
}

export async function getToken() {
  return AsyncStorage.getItem(TOKEN_KEY)
}

export async function setToken(token: string) {
  await AsyncStorage.setItem(TOKEN_KEY, token)
}

export async function clearToken() {
  await AsyncStorage.removeItem(TOKEN_KEY)
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken()
  const headers = new Headers(options.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  headers.set("Bypass-Tunnel-Reminder", "true")
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const detail = await response.text()
    throw new ApiError(response.status, readDetail(detail, response.status))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
