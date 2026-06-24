const AUTH_TOKEN_KEY = 'auth_token'
const USER_KEY = 'current_user'

export const storage = {
  getToken: (): string | null => {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  },

  setToken: (token: string): void => {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  },

  clearToken: (): void => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
  },

  getUser: () => {
    const user = localStorage.getItem(USER_KEY)
    return user ? JSON.parse(user) : null
  },

  setUser: (user: unknown): void => {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  clearUser: (): void => {
    localStorage.removeItem(USER_KEY)
  },

  clear: (): void => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}
