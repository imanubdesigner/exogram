import { describe, expect, it } from 'vitest'

import { resolveApiBase } from './api'

describe('api base resolution', () => {
  it('uses the configured env base url', () => {
    expect(resolveApiBase('https://exogram.app')).toBe('https://exogram.app/api')
  })

  it('falls back to localhost when no env value is set', () => {
    expect(resolveApiBase('')).toBe('http://localhost:8000/api')
  })
})
