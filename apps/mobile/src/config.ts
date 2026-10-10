const configured = process.env.EXPO_PUBLIC_API_URL
export const API_URL = (configured && configured.trim()) || "https://fubar.wildwoodingredients.com/api/v1"
