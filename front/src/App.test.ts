import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const ACCESS_TOKEN_STORAGE_KEY = 'chatico_ads.access_token'

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      'content-type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
}

function buildReport() {
  const emptyMetric = { current: 0, previous: 0, delta_pct: 0 }

  return {
    account: {
      id: 'act_1',
      account_id: '111',
      name: 'Primary Meta Account',
      currency: 'USD',
      timezone_name: 'UTC',
    },
    periods: {
      current: { since: '2026-06-01', until: '2026-06-30' },
      previous: { since: '2026-05-01', until: '2026-05-31' },
    },
    summary: {
      primary_result_kind: 'purchase',
      metrics: {
        spend: emptyMetric,
        reach: emptyMetric,
        impressions: emptyMetric,
        clicks: emptyMetric,
        ctr: emptyMetric,
        cpm: emptyMetric,
        cpc: emptyMetric,
        results: emptyMetric,
        cost_per_result: emptyMetric,
      },
      active_campaigns: 1,
      total_campaigns: 1,
    },
    campaigns: [
      {
        id: 'cmp_1',
        name: 'Campaign 1',
        status: 'ACTIVE',
        primary_result_kind: 'purchase',
        metrics: {
          spend: emptyMetric,
          reach: emptyMetric,
          impressions: emptyMetric,
          clicks: emptyMetric,
          ctr: emptyMetric,
          cpm: emptyMetric,
          cpc: emptyMetric,
          results: emptyMetric,
          cost_per_result: emptyMetric,
        },
        creatives: [],
      },
    ],
  }
}

function buildGoogleReport() {
  return {
    ...buildReport(),
    account: {
      id: '1234567890',
      account_id: '1234567890',
      name: 'Primary Google Account',
      currency: 'USD',
      timezone_name: 'UTC',
    },
  }
}

function buildTikTokReport() {
  return {
    ...buildReport(),
    account: {
      id: '1234567890123456789',
      account_id: '1234567890123456789',
      name: 'Primary TikTok Advertiser',
      currency: 'USD',
      timezone_name: 'UTC',
    },
    summary: {
      ...buildReport().summary,
      primary_result_kind: 'conversions',
    },
    campaigns: [
      {
        ...buildReport().campaigns[0],
        primary_result_kind: 'conversions',
        creatives: [
          {
            id: 'ad_1',
            name: 'Spark Ad 1',
            object_type: 'SPARK_AD',
            thumbnail_url: null,
            image_url: null,
            metrics: {
              spend: 10,
              impressions: 1000,
              clicks: 20,
              ctr: 2,
              results: 3,
              result_kind: 'conversions',
            },
          },
        ],
      },
    ],
  }
}

function createFetchMock(options: { googleCustomers?: unknown[]; tiktokAdvertisers?: unknown[] } = {}) {
  let adAccountsCalls = 0
  let googleCustomersCalls = 0
  let tiktokAdvertisersCalls = 0

  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
    const method = init?.method ?? 'GET'

    if (url.endsWith('/ai/providers')) {
      return jsonResponse([])
    }
    if (url.endsWith('/auth/me')) {
      return jsonResponse({
        id: 'user-1',
        email: 'owner@example.com',
        locale: 'en',
        is_active: true,
      })
    }
    if (url.endsWith('/meta/ad-accounts') && method === 'GET') {
      adAccountsCalls += 1
      return jsonResponse(
        adAccountsCalls === 1
          ? [
              {
                id: 'acc-1',
                external_id: 'act_1',
                account_id: '111',
                name: 'Primary Meta Account',
                currency: 'USD',
                timezone_name: 'UTC',
                account_status: 1,
              },
            ]
          : [],
      )
    }
    if (url.endsWith('/google-ads/customers')) {
      googleCustomersCalls += 1
      if (options.googleCustomers && googleCustomersCalls === 1) {
        return jsonResponse(options.googleCustomers)
      }
      return jsonResponse([])
    }
    if (url.endsWith('/tiktok-ads/advertisers')) {
      tiktokAdvertisersCalls += 1
      if (options.tiktokAdvertisers && tiktokAdvertisersCalls === 1) {
        return jsonResponse(options.tiktokAdvertisers)
      }
      return jsonResponse([])
    }
    if (url.endsWith('/ai/provider-keys')) {
      return jsonResponse([])
    }
    if (url.includes('/dashboard/meta/ad-accounts/act_1/report?')) {
      return jsonResponse(buildReport())
    }
    if (url.includes('/dashboard/google-ads/customers/1234567890/report?')) {
      return jsonResponse(buildGoogleReport())
    }
    if (url.includes('/dashboard/tiktok-ads/advertisers/1234567890123456789/report?')) {
      return jsonResponse(buildTikTokReport())
    }
    if (url.endsWith('/ai/meta/ad-accounts/act_1/auto-verdict') && method === 'POST') {
      return jsonResponse({ text: 'Stable account performance.' })
    }
    if (url.endsWith('/ai/google-ads/customers/1234567890/auto-verdict') && method === 'POST') {
      return jsonResponse({ text: 'Stable Google account performance.' })
    }
    if (url.endsWith('/ai/tiktok-ads/advertisers/1234567890123456789/auto-verdict') && method === 'POST') {
      return jsonResponse({ text: 'Stable TikTok advertiser performance.' })
    }
    if (url.endsWith('/meta/connections') && method === 'DELETE') {
      return new Response(null, { status: 204 })
    }
    if (url.endsWith('/google-ads/connections') && method === 'DELETE') {
      return new Response(null, { status: 204 })
    }
    if (url.endsWith('/tiktok-ads/connections') && method === 'DELETE') {
      return new Response(null, { status: 204 })
    }

    throw new Error(`Unhandled request: ${method} ${url}`)
  })
}

describe('App Meta disconnect flow', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.clear()
    localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'access-token')
    window.history.pushState({}, '', '/')
    vi.stubGlobal('fetch', createFetchMock())
    vi.stubGlobal('scrollTo', vi.fn())
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      value: vi.fn(),
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('deletes Meta connections and shows a success notice', async () => {
    const { default: App } = await import('./App.vue')
    const wrapper = mount(App)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Disconnect Meta')
    })

    const disconnectButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Disconnect Meta')

    expect(disconnectButton).toBeDefined()

    await disconnectButton!.trigger('click')
    await flushPromises()

    const fetchMock = vi.mocked(fetch)

    await vi.waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).endsWith('/meta/connections') && init?.method === 'DELETE',
        ),
      ).toBe(true)
      expect(wrapper.text()).toContain('Meta data has been removed from your account.')
      expect(wrapper.text()).not.toContain('Disconnect Meta')
    })

    wrapper.unmount()
  })

  it('deletes Google Ads connections and shows a success notice', async () => {
    vi.stubGlobal(
      'fetch',
      createFetchMock({
        googleCustomers: [
          {
            id: 'google-customer-1',
            external_customer_id: '1234567890',
            resource_name: 'customers/1234567890',
            descriptive_name: 'Primary Google Account',
            currency_code: 'USD',
            time_zone: 'UTC',
            is_manager: false,
            is_directly_accessible: true,
            hierarchy_level: 0,
            root_customer_id: '1234567890',
            manager_customer_id: null,
            login_customer_id: null,
          },
        ],
      }),
    )

    const { default: App } = await import('./App.vue')
    const wrapper = mount(App)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Disconnect Google Ads')
    })

    const disconnectButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Disconnect Google Ads')

    expect(disconnectButton).toBeDefined()

    await disconnectButton!.trigger('click')
    await flushPromises()

    const fetchMock = vi.mocked(fetch)

    await vi.waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).endsWith('/google-ads/connections') && init?.method === 'DELETE',
        ),
      ).toBe(true)
      expect(wrapper.text()).toContain('Google Ads data has been removed from your account.')
      expect(wrapper.text()).not.toContain('Disconnect Google Ads')
    })

    wrapper.unmount()
  })

  it('deletes TikTok Ads connections and shows a success notice', async () => {
    vi.stubGlobal(
      'fetch',
      createFetchMock({
        tiktokAdvertisers: [
          {
            id: 'tiktok-advertiser-1',
            advertiser_id: '1234567890123456789',
            name: 'Primary TikTok Advertiser',
            currency: 'USD',
            timezone_name: 'UTC',
            status: 'ACTIVE',
          },
        ],
      }),
    )

    const { default: App } = await import('./App.vue')
    const wrapper = mount(App)

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Disconnect TikTok Ads')
    })

    const disconnectButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Disconnect TikTok Ads')

    expect(disconnectButton).toBeDefined()

    await disconnectButton!.trigger('click')
    await flushPromises()

    const fetchMock = vi.mocked(fetch)

    await vi.waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) => String(input).endsWith('/tiktok-ads/connections') && init?.method === 'DELETE',
        ),
      ).toBe(true)
      expect(wrapper.text()).toContain('TikTok Ads data has been removed from your account.')
      expect(wrapper.text()).not.toContain('Disconnect TikTok Ads')
    })

    wrapper.unmount()
  })
})
