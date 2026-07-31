const TOKEN_KEY = 'token'

export const getAuthToken = () => {
  localStorage.removeItem(TOKEN_KEY)
  return sessionStorage.getItem(TOKEN_KEY)
}

export const setAuthToken = token => {
  sessionStorage.setItem(TOKEN_KEY, token)
  // Remove tokens written by older builds so they do not remain available
  // after this tab-scoped session ends.
  localStorage.removeItem(TOKEN_KEY)
}

export const clearAuthToken = () => {
  sessionStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_KEY)
}
