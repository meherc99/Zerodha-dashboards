import { afterEach, describe, expect, it, vi } from 'vitest'

import apiClient, {
  resetApiSession,
  setUnauthorizedHandler
} from '@/services/api'
import { getAuthToken, setAuthToken } from '@/utils/authSession'

describe('API session isolation', () => {
  afterEach(() => {
    setUnauthorizedHandler(null)
    resetApiSession()
  })

  it('aborts in-flight work and rejects its late response after a session reset', async () => {
    let requestConfig
    let resolveRequest
    const responsePromise = apiClient.get('/slow-request', {
      adapter: config => {
        requestConfig = config
        return new Promise(resolve => {
          resolveRequest = () => resolve({
            data: { owner: 'previous-user' },
            status: 200,
            statusText: 'OK',
            headers: {},
            config
          })
        })
      }
    })

    await vi.waitFor(() => expect(requestConfig).toBeDefined())
    resetApiSession()

    expect(requestConfig.signal.aborted).toBe(true)
    resolveRequest()
    await expect(responsePromise).rejects.toMatchObject({
      code: 'ERR_CANCELED'
    })
  })

  it('uses the new token normally after old requests are cancelled', async () => {
    setAuthToken('next-user-token')
    let requestConfig

    const response = await apiClient.get('/current-request', {
      adapter: async config => {
        requestConfig = config
        return {
          data: { owner: 'next-user' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config
        }
      }
    })

    expect(requestConfig.headers.Authorization).toBe('Bearer next-user-token')
    expect(response.data).toEqual({ owner: 'next-user' })
  })

  it('ignores a late 401 from the previous session instead of logging out the new user', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    setAuthToken('previous-user-token')

    const requestInterceptor = apiClient.interceptors.request.handlers.at(-1).fulfilled
    const responseErrorInterceptor = (
      apiClient.interceptors.response.handlers.at(-1).rejected
    )
    const previousConfig = await requestInterceptor({ headers: {} })

    resetApiSession()
    setAuthToken('next-user-token')

    await expect(responseErrorInterceptor({
      config: previousConfig,
      response: { status: 401 }
    })).rejects.toMatchObject({
      code: 'ERR_CANCELED'
    })

    expect(getAuthToken()).toBe('next-user-token')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })
})
