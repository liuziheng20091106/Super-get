const API_BASE_KEY = 'api_base_url'

export function getApiBaseUrl() {
  const cookies = document.cookie.split(';')
  for (const cookie of cookies) {
    const [key, value] = cookie.trim().split('=')
    if (key === API_BASE_KEY && value) {
      return value
    }
  }
  return ''
}

export function setApiBaseUrl(url) {
  const expires = new Date()
  expires.setFullYear(expires.getFullYear() + 1)
  document.cookie = `${API_BASE_KEY}=${url};expires=${expires.toUTCString()};path=/`
}

export async function apiFetch(url, options = {}) {
  const baseUrl = getApiBaseUrl()
  const fullUrl = baseUrl + url
  return fetch(fullUrl, options)
}

export default {
  getApiBaseUrl,
  setApiBaseUrl,
  apiFetch
}
