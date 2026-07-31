import { afterEach } from 'vitest'

const createStorage = () => {
  const values = new Map()

  return {
    get length() {
      return values.size
    },
    clear() {
      values.clear()
    },
    getItem(key) {
      return values.has(String(key)) ? values.get(String(key)) : null
    },
    key(index) {
      return [...values.keys()][index] ?? null
    },
    removeItem(key) {
      values.delete(String(key))
    },
    setItem(key, value) {
      values.set(String(key), String(value))
    }
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: createStorage()
})
Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: createStorage()
})

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})
