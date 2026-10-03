import AsyncStorage from "@react-native-async-storage/async-storage"
import { API_URL } from "./config"

const TOKEN_KEY = "access_token"

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
    throw new Error(detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
