import '@testing-library/jest-dom'
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Node.js 22+ exposes localStorage as undefined (experimental Web Storage API without file).
// Polyfill it so jsdom-based tests can use it normally.
if (typeof localStorage === 'undefined' || localStorage === null) {
  const store: Record<string, string> = {}
  const mock: Storage = {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]) },
    get length() { return Object.keys(store).length },
    key: (i) => Object.keys(store)[i] ?? null,
  }
  Object.defineProperty(globalThis, 'localStorage', { value: mock, writable: true })
}

// jsdom does not implement scrollIntoView.
window.HTMLElement.prototype.scrollIntoView = function () {}

// jsdom does not implement window.matchMedia.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

export const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
