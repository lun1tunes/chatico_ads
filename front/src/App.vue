<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

type Locale = 'ru' | 'kz' | 'en'
type AuthMode = 'login' | 'register'
type AIProvider = 'anthropic' | 'openai' | 'gemini'
type MetricKey =
  | 'spend'
  | 'reach'
  | 'impressions'
  | 'clicks'
  | 'ctr'
  | 'cpm'
  | 'cpc'
  | 'results'
  | 'cost_per_result'

interface User {
  id: string
  email: string
  locale: string
  is_active: boolean
}

interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

interface MetaAccount {
  id: string
  external_id: string
  account_id: string
  name: string
  currency: string | null
  timezone_name: string | null
  account_status: number | null
}

interface MetricValue {
  current: number | null
  previous: number | null
  delta_pct: number | null
}

type MetricCollection = Record<MetricKey, MetricValue>

interface Creative {
  id: string
  name: string
  object_type: string
  thumbnail_url: string | null
  image_url: string | null
  metrics: {
    spend: number
    impressions: number
    clicks: number
    ctr: number
    results: number
    result_kind: string
  }
}

interface Campaign {
  id: string
  name: string
  status: string
  primary_result_kind: string
  metrics: MetricCollection
  creatives: Creative[]
}

interface DashboardReport {
  account: {
    id: string
    account_id: string
    name: string
    currency: string | null
    timezone_name: string | null
  }
  periods: {
    current: { since: string; until: string }
    previous: { since: string; until: string }
  }
  summary: {
    primary_result_kind: string
    metrics: MetricCollection
    active_campaigns: number
    total_campaigns: number
  }
  campaigns: Campaign[]
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ProviderModelPreset {
  value: string
  label: string
  is_default: boolean
}

interface AIProviderCatalog {
  key: AIProvider
  label: string
  default_model: string
  presets: ProviderModelPreset[]
  supports_custom_model: boolean
}

function normalizeBasePath(value?: string): string {
  if (!value || value.trim() === '' || value.trim() === '/') {
    return '/'
  }

  const trimmed = value.trim()
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return withLeadingSlash.endsWith('/') ? withLeadingSlash : `${withLeadingSlash}/`
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

const APP_BASE_PATH = normalizeBasePath(import.meta.env.BASE_URL)
const API_BASE_URL = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? `${window.location.origin}${APP_BASE_PATH}api/v1`)
const STORAGE_TOKEN_KEY = 'chatico.access_token'
const STORAGE_LOCALE_KEY = 'chatico.locale'
const CUSTOM_MODEL_OPTION = '__custom__'
const metricOrder: MetricKey[] = [
  'spend',
  'reach',
  'impressions',
  'clicks',
  'ctr',
  'cpm',
  'cpc',
  'results',
  'cost_per_result',
]

const translations = {
  ru: {
    brand: 'Chatico Ads',
    authLead: 'Единая панель Meta Ads для владельца бизнеса.',
    authTitle: 'Подключайте кабинеты и читайте рекламу простым языком.',
    authBody:
      'Сервис хранит доступы на сервере, сам собирает отчёты через Meta Marketing API и показывает AI-вывод без ручных токенов в браузере.',
    authModeLogin: 'Вход',
    authModeRegister: 'Регистрация',
    email: 'Email',
    password: 'Пароль',
    locale: 'Язык интерфейса',
    signIn: 'Войти',
    signUp: 'Создать аккаунт',
    authHint: 'У каждого пользователя изолированные кабинеты, refresh-сессия хранится на сервере.',
    workspace: 'Рабочая панель',
    connectMeta: 'Подключить Meta',
    accounts: 'Кабинеты',
    campaigns: 'Кампании',
    days: 'Период',
    dayOptions: { 7: '7 дней', 30: '30 дней', 90: '90 дней' },
    noAccountsTitle: 'Meta ещё не подключена',
    noAccountsBody:
      'Нажмите кнопку подключения. После OAuth кабинет появится слева, а отчёт и AI-анализ загрузятся через серверный прокси.',
    refreshData: 'Обновить отчёт',
    logout: 'Выйти',
    activeCampaigns: 'Активные кампании',
    totalCampaigns: 'Всего кампаний',
    periodCompare: 'Сравнение периода',
    campaignFocus: 'Выбранная кампания',
    creativeFocus: 'Креативы',
    aiVerdict: 'Авто-вердикт',
    aiVerdictHint: 'Сервер делает один запрос к нашему Claude и возвращает короткое заключение.',
    aiChat: 'AI-чат по данным',
    aiChatHint: 'Подключите ключ клиента. Запросы идут через сервер, ключ не попадает в браузерные вызовы к провайдеру.',
    apiKey: 'API ключ клиента',
    model: 'Модель',
    modelDefaultOption: 'Серверный default',
    modelCustom: 'Своя модель',
    modelCustomOption: 'Указать вручную',
    modelCustomPlaceholder: 'Например: claude-sonnet-4-6',
    modelDefaultHint: 'Сейчас будет использована модель',
    modelCustomHint: 'Если нужен другой model id, укажите его точно как у провайдера. Пустое поле вернёт server default.',
    provider: 'Провайдер',
    askPlaceholder: 'Спросить по кампаниям, креативам или CPA...',
    send: 'Отправить',
    loading: 'Загружаем рабочую панель...',
    loadingReport: 'Собираем Meta-отчёт...',
    loadingVerdict: 'Генерируем AI-вердикт...',
    emptyCampaigns: 'Кампании не найдены для выбранного периода.',
    emptyCreatives: 'Meta не вернула превью креативов по этой кампании.',
    oauthSuccess: 'Meta успешно подключена. Данные кабинета уже доступны.',
    oauthError: 'Подключение Meta завершилось ошибкой.',
    chatKeyHint: 'Поддерживаются Anthropic, OpenAI и Gemini.',
    helperQuestions: ['Какая кампания тянет результат?', 'Где растёт стоимость лида?', 'Что отключить в первую очередь?'],
    status: { active: 'Активна', paused: 'Пауза', other: 'Другая' },
    resultKinds: { messages: 'Сообщения', leads: 'Лиды', result: 'Результаты' },
    metricCopy: {
      spend: ['Расход', 'Сколько потрачено за период.'],
      reach: ['Охват', 'Сколько людей увидели рекламу.'],
      impressions: ['Показы', 'Общее число показов.'],
      clicks: ['Клики', 'Переходы по объявлениям.'],
      ctr: ['CTR', 'Доля кликов от показов.'],
      cpm: ['CPM', 'Стоимость 1000 показов.'],
      cpc: ['CPC', 'Средняя цена клика.'],
      results: ['Результаты', 'Основная целевая конверсия Meta.'],
      cost_per_result: ['Цена результата', 'Сколько стоит одна целевая конверсия.'],
    },
  },
  kz: {
    brand: 'Chatico Ads',
    authLead: 'Шағын бизнеске арналған бірыңғай Meta Ads панелі.',
    authTitle: 'Кабинеттерді қосып, жарнаманы түсінікті тілде бақылаңыз.',
    authBody:
      'Сервис рұқсаттарды серверде сақтайды, Meta Marketing API арқылы есепті өзі жинайды және браузерге токен шығармай AI-қорытынды береді.',
    authModeLogin: 'Кіру',
    authModeRegister: 'Тіркелу',
    email: 'Email',
    password: 'Құпиясөз',
    locale: 'Интерфейс тілі',
    signIn: 'Кіру',
    signUp: 'Аккаунт ашу',
    authHint: 'Әр қолданушы тек өз кабинеттерін көреді, refresh-сессия серверде сақталады.',
    workspace: 'Жұмыс панелі',
    connectMeta: 'Meta қосу',
    accounts: 'Кабинеттер',
    campaigns: 'Кампаниялар',
    days: 'Кезең',
    dayOptions: { 7: '7 күн', 30: '30 күн', 90: '90 күн' },
    noAccountsTitle: 'Meta әлі қосылмаған',
    noAccountsBody:
      'Қосу батырмасын басыңыз. OAuth аяқталған соң кабинет сол жақта көрінеді, ал есеп пен AI-талдау серверлік прокси арқылы жүктеледі.',
    refreshData: 'Есепті жаңарту',
    logout: 'Шығу',
    activeCampaigns: 'Белсенді кампаниялар',
    totalCampaigns: 'Барлық кампания',
    periodCompare: 'Кезеңді салыстыру',
    campaignFocus: 'Таңдалған кампания',
    creativeFocus: 'Креативтер',
    aiVerdict: 'Авто-қорытынды',
    aiVerdictHint: 'Сервер біздің Claude арқылы бір сұрау жасап, қысқа қорытынды қайтарады.',
    aiChat: 'Дерекпен AI-чат',
    aiChatHint: 'Клиент кілтін енгізіңіз. Сұраулар сервер арқылы өтеді, кілт провайдерге браузерден тікелей кетпейді.',
    apiKey: 'Клиент API кілті',
    model: 'Модель',
    modelDefaultOption: 'Серверлік default',
    modelCustom: 'Өз моделі',
    modelCustomOption: 'Қолмен енгізу',
    modelCustomPlaceholder: 'Мысалы: claude-sonnet-4-6',
    modelDefaultHint: 'Қазір мына модель қолданылады',
    modelCustomHint: 'Егер басқа model id керек болса, оны провайдердегі дәл атауымен енгізіңіз. Бос өріс server default-қа қайтарады.',
    provider: 'Провайдер',
    askPlaceholder: 'Кампания, креатив немесе CPA туралы сұраңыз...',
    send: 'Жіберу',
    loading: 'Жұмыс панелі жүктеліп жатыр...',
    loadingReport: 'Meta есебі жиналып жатыр...',
    loadingVerdict: 'AI қорытындысы жасалып жатыр...',
    emptyCampaigns: 'Таңдалған кезең бойынша кампания табылмады.',
    emptyCreatives: 'Бұл кампания үшін Meta креатив превьюін қайтармады.',
    oauthSuccess: 'Meta сәтті қосылды. Кабинет деректері дайын.',
    oauthError: 'Meta қосу кезінде қате болды.',
    chatKeyHint: 'Anthropic, OpenAI және Gemini қолдау табады.',
    helperQuestions: ['Нәтижені қай кампания әкеліп тұр?', 'Лид құны қай жерде өсіп жатыр?', 'Ең алдымен нені өшіру керек?'],
    status: { active: 'Белсенді', paused: 'Пауза', other: 'Басқа' },
    resultKinds: { messages: 'Хабарламалар', leads: 'Лидтер', result: 'Нәтижелер' },
    metricCopy: {
      spend: ['Шығын', 'Кезеңдегі жалпы шығын.'],
      reach: ['Қамту', 'Жарнаманы көрген адамдар саны.'],
      impressions: ['Көрсетілім', 'Барлық көрсетілім саны.'],
      clicks: ['Клик', 'Жарнамаға жасалған өтулер.'],
      ctr: ['CTR', 'Көрсетілімнен клик үлесі.'],
      cpm: ['CPM', '1000 көрсетілім құны.'],
      cpc: ['CPC', 'Бір кликтың орташа бағасы.'],
      results: ['Нәтижелер', 'Meta анықтаған негізгі конверсия.'],
      cost_per_result: ['Нәтиже құны', 'Бір негізгі конверсия бағасы.'],
    },
  },
  en: {
    brand: 'Chatico Ads',
    authLead: 'A single Meta Ads workspace for small business owners.',
    authTitle: 'Connect ad accounts and read performance in plain language.',
    authBody:
      'The app keeps access on the server, builds reports through the Meta Marketing API, and adds AI commentary without exposing platform tokens in the browser.',
    authModeLogin: 'Login',
    authModeRegister: 'Register',
    email: 'Email',
    password: 'Password',
    locale: 'Interface language',
    signIn: 'Sign in',
    signUp: 'Create account',
    authHint: 'Each user sees only their own ad accounts, and refresh sessions stay on the server.',
    workspace: 'Workspace',
    connectMeta: 'Connect Meta',
    accounts: 'Accounts',
    campaigns: 'Campaigns',
    days: 'Range',
    dayOptions: { 7: '7 days', 30: '30 days', 90: '90 days' },
    noAccountsTitle: 'Meta is not connected yet',
    noAccountsBody:
      'Start the OAuth flow. After approval, the account appears on the left and the dashboard plus AI analysis load through the backend proxy.',
    refreshData: 'Refresh report',
    logout: 'Logout',
    activeCampaigns: 'Active campaigns',
    totalCampaigns: 'Total campaigns',
    periodCompare: 'Period comparison',
    campaignFocus: 'Selected campaign',
    creativeFocus: 'Creatives',
    aiVerdict: 'Auto verdict',
    aiVerdictHint: 'The server makes one request to our Claude setup and returns a short summary.',
    aiChat: 'AI chat with data',
    aiChatHint: 'Paste the client key. Requests still go through the server so the browser never calls the provider directly.',
    apiKey: 'Client API key',
    model: 'Model',
    modelDefaultOption: 'Server default',
    modelCustom: 'Custom model',
    modelCustomOption: 'Enter manually',
    modelCustomPlaceholder: 'Example: claude-sonnet-4-6',
    modelDefaultHint: 'The chat will use',
    modelCustomHint: 'If you need a different model id, enter it exactly as the provider expects. Leaving it blank falls back to the server default.',
    provider: 'Provider',
    askPlaceholder: 'Ask about campaigns, creatives, or CPA...',
    send: 'Send',
    loading: 'Loading workspace...',
    loadingReport: 'Building Meta report...',
    loadingVerdict: 'Generating AI verdict...',
    emptyCampaigns: 'No campaigns were returned for this period.',
    emptyCreatives: 'Meta did not return creative previews for this campaign.',
    oauthSuccess: 'Meta connected successfully. Account data is ready.',
    oauthError: 'Meta connection failed.',
    chatKeyHint: 'Anthropic, OpenAI, and Gemini are supported.',
    helperQuestions: ['Which campaign drives the result?', 'Where is cost per lead rising?', 'What should I pause first?'],
    status: { active: 'Active', paused: 'Paused', other: 'Other' },
    resultKinds: { messages: 'Messages', leads: 'Leads', result: 'Results' },
    metricCopy: {
      spend: ['Spend', 'Total spend for the selected period.'],
      reach: ['Reach', 'How many people saw the ads.'],
      impressions: ['Impressions', 'Total ad views.'],
      clicks: ['Clicks', 'Ad clicks across campaigns.'],
      ctr: ['CTR', 'Click-through rate from impressions.'],
      cpm: ['CPM', 'Cost per thousand impressions.'],
      cpc: ['CPC', 'Average cost per click.'],
      results: ['Results', 'Primary Meta conversion result.'],
      cost_per_result: ['Cost per result', 'Average cost of one target result.'],
    },
  },
} as const

const fallbackProviderCatalog: AIProviderCatalog[] = [
  {
    key: 'anthropic',
    label: 'Anthropic',
    default_model: 'claude-sonnet-4-6',
    presets: [{ value: 'claude-sonnet-4-6', label: 'Server default (claude-sonnet-4-6)', is_default: true }],
    supports_custom_model: true,
  },
  {
    key: 'openai',
    label: 'OpenAI',
    default_model: 'gpt-5-mini',
    presets: [{ value: 'gpt-5-mini', label: 'Server default (gpt-5-mini)', is_default: true }],
    supports_custom_model: true,
  },
  {
    key: 'gemini',
    label: 'Gemini',
    default_model: 'gemini-3.5-flash',
    presets: [{ value: 'gemini-3.5-flash', label: 'Server default (gemini-3.5-flash)', is_default: true }],
    supports_custom_model: true,
  },
]

const authMode = ref<AuthMode>('login')
const locale = ref<Locale>((localStorage.getItem(STORAGE_LOCALE_KEY) as Locale) || 'kz')
const registerLocale = ref<Locale>(locale.value)
const accessToken = ref(localStorage.getItem(STORAGE_TOKEN_KEY) ?? '')
const user = ref<User | null>(null)
const oauthStatus = ref<{ status: 'success' | 'error'; message: string } | null>(null)
const authForm = ref({ email: '', password: '' })
const authError = ref('')
const pageError = ref('')
const authLoading = ref(false)
const bootLoading = ref(true)
const metaConnecting = ref(false)
const accountsLoading = ref(false)
const reportLoading = ref(false)
const verdictLoading = ref(false)
const chatLoading = ref(false)
const reportDays = ref(30)
const accounts = ref<MetaAccount[]>([])
const selectedAccountId = ref('')
const report = ref<DashboardReport | null>(null)
const selectedCampaignId = ref('')
const autoVerdict = ref('')
const chatMessages = ref<ChatMessage[]>([])
const chatDraft = ref('')
const chatError = ref('')
const provider = ref<AIProvider>('anthropic')
const providerCatalog = ref<AIProviderCatalog[]>(fallbackProviderCatalog)
const clientApiKey = ref('')
const customModel = ref('')
const selectedModelPreset = ref(
  fallbackProviderCatalog.find((providerOption) => providerOption.key === provider.value)?.default_model ?? '',
)

const copy = computed(() => translations[locale.value])
const isAuthenticated = computed(() => user.value !== null)
const activeProviderConfig = computed(() => {
  return providerCatalog.value.find((providerOption) => providerOption.key === provider.value) ?? null
})
const availableModelPresets = computed(() => {
  return activeProviderConfig.value?.presets ?? []
})
const isCustomModelSelected = computed(() => selectedModelPreset.value === CUSTOM_MODEL_OPTION)
const resolvedModel = computed(() => {
  if (isCustomModelSelected.value) {
    return customModel.value.trim() || null
  }
  return selectedModelPreset.value || activeProviderConfig.value?.default_model || null
})
const modelSelectionHint = computed(() => {
  const activeProvider = activeProviderConfig.value
  if (!activeProvider) {
    return ''
  }
  if (isCustomModelSelected.value) {
    return `${copy.value.modelCustomHint}`
  }
  return `${copy.value.modelDefaultHint}: ${resolvedModel.value || activeProvider.default_model}.`
})
const selectedAccount = computed(() => {
  return accounts.value.find((account) => account.external_id === selectedAccountId.value) ?? null
})
const selectedCampaign = computed(() => {
  const campaigns = report.value?.campaigns ?? []
  return campaigns.find((campaign) => campaign.id === selectedCampaignId.value) ?? campaigns[0] ?? null
})
const overviewMetrics = computed(() => {
  if (!report.value) {
    return []
  }
  return metricOrder.map((key) => ({
    key,
    metric: report.value!.summary.metrics[key],
    label: copy.value.metricCopy[key][0],
    hint: copy.value.metricCopy[key][1],
  }))
})
const workspaceNotice = computed(() => {
  if (!oauthStatus.value) {
    return ''
  }
  return oauthStatus.value.status === 'success'
    ? copy.value.oauthSuccess
    : `${copy.value.oauthError}${oauthStatus.value.message ? `: ${oauthStatus.value.message}` : ''}`
})

function presetLabel(preset: ProviderModelPreset) {
  if (preset.is_default) {
    return `${copy.value.modelDefaultOption} · ${preset.value}`
  }
  return preset.label
}

function applyProviderDefaultPreset() {
  const activeProvider = activeProviderConfig.value
  if (!activeProvider) {
    selectedModelPreset.value = ''
    return
  }

  const defaultPreset = activeProvider.presets.find((preset) => preset.is_default) ?? activeProvider.presets[0]
  selectedModelPreset.value = defaultPreset?.value ?? activeProvider.default_model
}

function syncLocale(nextLocale: Locale) {
  locale.value = nextLocale
  registerLocale.value = nextLocale
  document.documentElement.lang = nextLocale
  localStorage.setItem(STORAGE_LOCALE_KEY, nextLocale)
}

function persistAuth(payload: AuthResponse) {
  accessToken.value = payload.access_token
  user.value = payload.user
  localStorage.setItem(STORAGE_TOKEN_KEY, payload.access_token)
  if (payload.user.locale === 'ru' || payload.user.locale === 'kz' || payload.user.locale === 'en') {
    syncLocale(payload.user.locale)
  }
}

function resetSession() {
  accessToken.value = ''
  user.value = null
  accounts.value = []
  report.value = null
  selectedAccountId.value = ''
  selectedCampaignId.value = ''
  autoVerdict.value = ''
  chatMessages.value = []
  localStorage.removeItem(STORAGE_TOKEN_KEY)
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  const payload = text ? JSON.parse(text) : {}
  if (!response.ok) {
    const detail =
      typeof payload?.detail === 'string'
        ? payload.detail
        : typeof payload?.message === 'string'
          ? payload.message
          : `HTTP ${response.status}`
    throw new Error(detail)
  }
  return payload as T
}

async function refreshAuth(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) {
    return false
  }
  const payload = await parseResponse<AuthResponse>(response)
  persistAuth(payload)
  return true
}

async function apiRequest<T>(
  path: string,
  options: {
    method?: string
    auth?: boolean
    retry?: boolean
    body?: unknown
  } = {},
): Promise<T> {
  const headers = new Headers()
  if (options.body !== undefined) {
    headers.set('content-type', 'application/json')
  }
  if (options.auth !== false && accessToken.value) {
    headers.set('authorization', `Bearer ${accessToken.value}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && options.auth !== false && options.retry !== false) {
    const refreshed = await refreshAuth()
    if (refreshed) {
      return apiRequest<T>(path, { ...options, retry: false })
    }
    resetSession()
  }

  return parseResponse<T>(response)
}

async function bootstrapSession() {
  bootLoading.value = true
  document.documentElement.lang = locale.value

  const callbackUrl = new URL(window.location.href)
  const providerParam = callbackUrl.searchParams.get('provider')
  const statusParam = callbackUrl.searchParams.get('status')
  if (providerParam === 'meta' && (statusParam === 'success' || statusParam === 'error')) {
    oauthStatus.value = {
      status: statusParam,
      message: callbackUrl.searchParams.get('message') ?? '',
    }
    window.history.replaceState({}, '', APP_BASE_PATH)
  }

  try {
    if (accessToken.value) {
      user.value = await apiRequest<User>('/auth/me')
    } else {
      const refreshed = await refreshAuth()
      if (!refreshed) {
        return
      }
    }

    if (!user.value) {
      user.value = await apiRequest<User>('/auth/me')
    }
    await loadAccounts()
  } catch (error) {
    resetSession()
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    bootLoading.value = false
  }
}

async function loadProviderCatalog() {
  try {
    const payload = await apiRequest<AIProviderCatalog[]>('/ai/providers', {
      auth: false,
      retry: false,
    })
    if (payload.length > 0) {
      providerCatalog.value = payload
      applyProviderDefaultPreset()
    }
  } catch {
    providerCatalog.value = fallbackProviderCatalog
    applyProviderDefaultPreset()
  }
}

async function submitAuth() {
  authLoading.value = true
  authError.value = ''

  try {
    const endpoint = authMode.value === 'register' ? '/auth/register' : '/auth/login'
    const payload =
      authMode.value === 'register'
        ? { ...authForm.value, locale: registerLocale.value }
        : { ...authForm.value }

    const result = await apiRequest<AuthResponse>(endpoint, {
      method: 'POST',
      auth: false,
      retry: false,
      body: payload,
    })
    persistAuth(result)
    authForm.value.password = ''
    pageError.value = ''
    await loadAccounts()
  } catch (error) {
    authError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    authLoading.value = false
  }
}

async function logout() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' })
  } catch {
    // Ignore logout transport issues; local session still needs to be cleared.
  } finally {
    resetSession()
  }
}

async function loadAccounts() {
  if (!user.value) {
    return
  }

  accountsLoading.value = true
  pageError.value = ''

  try {
    const payload = await apiRequest<MetaAccount[]>('/meta/ad-accounts')
    accounts.value = payload

    if (payload.length === 0) {
      report.value = null
      selectedAccountId.value = ''
      selectedCampaignId.value = ''
      autoVerdict.value = ''
      return
    }

    const isCurrentAccountValid = payload.some((account) => account.external_id === selectedAccountId.value)
    selectedAccountId.value = isCurrentAccountValid ? selectedAccountId.value : payload[0].external_id
    await loadReport()
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    accountsLoading.value = false
  }
}

async function connectMeta() {
  metaConnecting.value = true
  pageError.value = ''

  try {
    const payload = await apiRequest<{ authorization_url: string }>('/meta/oauth/start')
    window.location.href = payload.authorization_url
  } catch (error) {
    metaConnecting.value = false
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  }
}

async function loadReport() {
  if (!selectedAccountId.value) {
    return
  }

  reportLoading.value = true
  pageError.value = ''
  chatError.value = ''

  try {
    const payload = await apiRequest<DashboardReport>(
      `/dashboard/meta/ad-accounts/${selectedAccountId.value}/report?days=${reportDays.value}`,
    )
    report.value = payload
    selectedCampaignId.value =
      payload.campaigns.find((campaign) => campaign.id === selectedCampaignId.value)?.id ?? payload.campaigns[0]?.id ?? ''
    if (chatMessages.value.length === 0) {
      chatMessages.value = [
        {
          role: 'assistant',
          content: copy.value.aiChatHint,
        },
      ]
    }
    await loadAutoVerdict()
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
    autoVerdict.value = ''
  } finally {
    reportLoading.value = false
  }
}

async function loadAutoVerdict() {
  if (!selectedAccountId.value) {
    return
  }

  verdictLoading.value = true

  try {
    const payload = await apiRequest<{ text: string }>(
      `/ai/meta/ad-accounts/${selectedAccountId.value}/auto-verdict`,
      {
        method: 'POST',
        body: {
          days: reportDays.value,
          language: locale.value,
        },
      },
    )
    autoVerdict.value = payload.text
  } catch (error) {
    autoVerdict.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    verdictLoading.value = false
  }
}

async function sendQuestion(question?: string) {
  const nextQuestion = (question ?? chatDraft.value).trim()
  if (!nextQuestion || !selectedAccountId.value || !clientApiKey.value.trim()) {
    return
  }

  chatError.value = ''
  chatLoading.value = true

  const nextMessages: ChatMessage[] = [...chatMessages.value, { role: 'user', content: nextQuestion }]
  chatMessages.value = nextMessages
  chatDraft.value = ''

  try {
    const payload = await apiRequest<{ text: string }>(`/ai/meta/ad-accounts/${selectedAccountId.value}/chat`, {
      method: 'POST',
      body: {
        days: reportDays.value,
        language: locale.value,
        provider: provider.value,
        api_key: clientApiKey.value.trim(),
        model: resolvedModel.value,
        messages: nextMessages,
      },
    })

    chatMessages.value = [...nextMessages, { role: 'assistant', content: payload.text }]
  } catch (error) {
    chatMessages.value = nextMessages
    chatError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    chatLoading.value = false
  }
}

function selectAccount(accountId: string) {
  if (selectedAccountId.value === accountId) {
    return
  }
  selectedAccountId.value = accountId
  void loadReport()
}

function selectDays(days: number) {
  if (reportDays.value === days) {
    return
  }
  reportDays.value = days
  void loadReport()
}

function selectCampaign(campaignId: string) {
  selectedCampaignId.value = campaignId
}

function formatMetricValue(key: MetricKey, value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '—'
  }

  const currency = report.value?.account.currency || selectedAccount.value?.currency || 'USD'
  if (key === 'spend' || key === 'cpm' || key === 'cpc' || key === 'cost_per_result') {
    return new Intl.NumberFormat(locale.value, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(value)
  }

  if (key === 'ctr') {
    return `${value.toFixed(2)}%`
  }

  return new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: 0,
  }).format(value)
}

function formatCompactNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '—'
  }

  return new Intl.NumberFormat(locale.value, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function formatDelta(delta: number | null | undefined) {
  if (delta === null || delta === undefined) {
    return '—'
  }
  const prefix = delta > 0 ? '+' : ''
  return `${prefix}${delta.toFixed(1)}%`
}

function metricTone(delta: number | null | undefined) {
  if (delta === null || delta === undefined) {
    return 'neutral'
  }
  if (delta > 0) {
    return 'up'
  }
  if (delta < 0) {
    return 'down'
  }
  return 'neutral'
}

function statusTone(status: string) {
  const normalized = status.toUpperCase()
  if (normalized.includes('ACTIVE')) {
    return 'active'
  }
  if (normalized.includes('PAUSED')) {
    return 'paused'
  }
  return 'other'
}

function statusLabel(status: string) {
  const tone = statusTone(status)
  return copy.value.status[tone]
}

function resultKindLabel(kind: string) {
  const normalized = kind as keyof (typeof translations)['ru']['resultKinds']
  return copy.value.resultKinds[normalized] ?? kind
}

function creativePreview(creative: Creative) {
  return creative.thumbnail_url || creative.image_url || ''
}

watch(provider, () => {
  customModel.value = ''
  applyProviderDefaultPreset()
})

onMounted(() => {
  syncLocale(locale.value)
  applyProviderDefaultPreset()
  void loadProviderCatalog()
  void bootstrapSession()
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">{{ copy.brand }}</p>
        <h1>{{ isAuthenticated ? copy.workspace : copy.authLead }}</h1>
      </div>

      <div class="toolbar">
        <div class="lang-switch" role="tablist" :aria-label="copy.locale">
          <button
            v-for="lang in ['kz', 'ru', 'en']"
            :key="lang"
            type="button"
            class="lang-pill"
            :class="{ active: locale === lang }"
            @click="syncLocale(lang as Locale)"
          >
            {{ lang.toUpperCase() }}
          </button>
        </div>

        <button v-if="isAuthenticated" type="button" class="ghost-button" @click="logout">
          {{ copy.logout }}
        </button>
      </div>
    </header>

    <main v-if="bootLoading" class="boot-stage">
      <div class="pulse-dot"></div>
      <p>{{ copy.loading }}</p>
    </main>

    <main v-else-if="!isAuthenticated" class="auth-stage">
      <section class="auth-intro">
        <p class="eyebrow">Meta Marketing API + AI proxy</p>
        <h2>{{ copy.authTitle }}</h2>
        <p class="auth-copy">{{ copy.authBody }}</p>

        <div class="auth-grid">
          <div>
            <span>{{ copy.connectMeta }}</span>
            <strong>OAuth</strong>
          </div>
          <div>
            <span>{{ copy.periodCompare }}</span>
            <strong>Delta KPIs</strong>
          </div>
          <div>
            <span>{{ copy.aiVerdict }}</span>
            <strong>Claude</strong>
          </div>
        </div>
      </section>

      <section class="auth-panel">
        <div class="panel-tabs">
          <button
            type="button"
            class="panel-tab"
            :class="{ active: authMode === 'login' }"
            @click="authMode = 'login'"
          >
            {{ copy.authModeLogin }}
          </button>
          <button
            type="button"
            class="panel-tab"
            :class="{ active: authMode === 'register' }"
            @click="authMode = 'register'"
          >
            {{ copy.authModeRegister }}
          </button>
        </div>

        <form class="auth-form" @submit.prevent="submitAuth">
          <label>
            <span>{{ copy.email }}</span>
            <input v-model.trim="authForm.email" type="email" autocomplete="email" required />
          </label>

          <label>
            <span>{{ copy.password }}</span>
            <input
              v-model="authForm.password"
              type="password"
              autocomplete="current-password"
              minlength="8"
              required
            />
          </label>

          <label v-if="authMode === 'register'">
            <span>{{ copy.locale }}</span>
            <select v-model="registerLocale">
              <option value="kz">Қазақша</option>
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>

          <button type="submit" class="primary-button" :disabled="authLoading">
            {{ authMode === 'register' ? copy.signUp : copy.signIn }}
          </button>
        </form>

        <p class="panel-hint">{{ copy.authHint }}</p>
        <p v-if="authError" class="message error">{{ authError }}</p>
        <p v-else-if="pageError" class="message error">{{ pageError }}</p>
      </section>
    </main>

    <main v-else class="workspace">
      <aside class="rail rail-left">
        <section class="rail-section">
          <div class="section-head">
            <span>{{ copy.accounts }}</span>
            <button type="button" class="rail-link" :disabled="metaConnecting" @click="connectMeta">
              {{ copy.connectMeta }}
            </button>
          </div>

          <div v-if="accountsLoading" class="empty-note">{{ copy.loadingReport }}</div>

          <button
            v-for="account in accounts"
            :key="account.id"
            type="button"
            class="account-item"
            :class="{ active: selectedAccountId === account.external_id }"
            @click="selectAccount(account.external_id)"
          >
            <span>{{ account.name }}</span>
            <small>{{ account.account_id }}</small>
          </button>
        </section>

        <section class="rail-section" v-if="accounts.length > 0">
          <div class="section-head">
            <span>{{ copy.days }}</span>
          </div>

          <div class="range-grid">
            <button
              v-for="days in [7, 30, 90]"
              :key="days"
              type="button"
              class="range-button"
              :class="{ active: reportDays === days }"
              @click="selectDays(days)"
            >
              {{ copy.dayOptions[days as 7 | 30 | 90] }}
            </button>
          </div>
        </section>

        <section class="rail-section" v-if="report?.campaigns?.length">
          <div class="section-head">
            <span>{{ copy.campaigns }}</span>
          </div>

          <button
            v-for="campaign in report.campaigns"
            :key="campaign.id"
            type="button"
            class="campaign-nav"
            :class="{ active: selectedCampaignId === campaign.id }"
            @click="selectCampaign(campaign.id)"
          >
            <i class="status-dot" :class="statusTone(campaign.status)"></i>
            <div>
              <strong>{{ campaign.name }}</strong>
              <small>{{ formatMetricValue('spend', campaign.metrics.spend.current) }}</small>
            </div>
          </button>
        </section>
      </aside>

      <section class="stage-center">
        <div v-if="workspaceNotice" class="message" :class="oauthStatus?.status === 'error' ? 'error' : 'success'">
          {{ workspaceNotice }}
        </div>
        <div v-if="pageError" class="message error">{{ pageError }}</div>

        <section v-if="accounts.length === 0" class="empty-surface">
          <p class="eyebrow">{{ copy.connectMeta }}</p>
          <h2>{{ copy.noAccountsTitle }}</h2>
          <p>{{ copy.noAccountsBody }}</p>
          <button type="button" class="primary-button" :disabled="metaConnecting" @click="connectMeta">
            {{ copy.connectMeta }}
          </button>
        </section>

        <template v-else>
          <section class="hero-strip">
            <div>
              <p class="eyebrow">{{ selectedAccount?.name }}</p>
              <h2>{{ report?.account.name || selectedAccount?.name }}</h2>
              <p class="muted">
                {{ report?.periods.current.since }} - {{ report?.periods.current.until }}
                <span v-if="report?.account.timezone_name"> · {{ report?.account.timezone_name }}</span>
              </p>
            </div>

            <div class="hero-actions">
              <button type="button" class="ghost-button" :disabled="reportLoading" @click="loadReport">
                {{ copy.refreshData }}
              </button>
            </div>
          </section>

          <section class="summary-band">
            <div class="summary-chip">
              <span>{{ copy.activeCampaigns }}</span>
              <strong>{{ report?.summary.active_campaigns ?? 0 }}</strong>
            </div>
            <div class="summary-chip">
              <span>{{ copy.totalCampaigns }}</span>
              <strong>{{ report?.summary.total_campaigns ?? 0 }}</strong>
            </div>
            <div class="summary-chip">
              <span>{{ resultKindLabel(report?.summary.primary_result_kind || 'result') }}</span>
              <strong>{{ formatCompactNumber(report?.summary.metrics.results.current) }}</strong>
            </div>
          </section>

          <section class="compare-strip" v-if="report">
            <p class="eyebrow">{{ copy.periodCompare }}</p>
            <p>
              {{ report.periods.previous.since }} - {{ report.periods.previous.until }}
              <span>vs</span>
              {{ report.periods.current.since }} - {{ report.periods.current.until }}
            </p>
          </section>

          <section class="metric-grid" v-if="report">
            <article v-for="item in overviewMetrics" :key="item.key" class="metric-tile">
              <p>{{ item.label }}</p>
              <strong>{{ formatMetricValue(item.key, item.metric.current) }}</strong>
              <span class="metric-sub">{{ item.hint }}</span>
              <small :class="metricTone(item.metric.delta_pct)">{{ formatDelta(item.metric.delta_pct) }}</small>
            </article>
          </section>

          <section v-if="reportLoading" class="empty-note">{{ copy.loadingReport }}</section>

          <template v-else-if="report">
            <section v-if="selectedCampaign" class="focus-surface">
              <div class="focus-head">
                <div>
                  <p class="eyebrow">{{ copy.campaignFocus }}</p>
                  <h3>{{ selectedCampaign.name }}</h3>
                </div>

                <div class="status-badge" :class="statusTone(selectedCampaign.status)">
                  <i class="status-dot" :class="statusTone(selectedCampaign.status)"></i>
                  {{ statusLabel(selectedCampaign.status) }}
                </div>
              </div>

              <div class="focus-metrics">
                <div v-for="key in metricOrder.slice(0, 6)" :key="key" class="focus-metric">
                  <span>{{ copy.metricCopy[key][0] }}</span>
                  <strong>{{ formatMetricValue(key, selectedCampaign.metrics[key].current) }}</strong>
                  <small :class="metricTone(selectedCampaign.metrics[key].delta_pct)">
                    {{ formatDelta(selectedCampaign.metrics[key].delta_pct) }}
                  </small>
                </div>
              </div>

              <div class="focus-creatives">
                <div class="section-head">
                  <span>{{ copy.creativeFocus }}</span>
                </div>

                <div v-if="selectedCampaign.creatives.length === 0" class="empty-note">
                  {{ copy.emptyCreatives }}
                </div>

                <div v-else class="creative-grid">
                  <article v-for="creative in selectedCampaign.creatives" :key="creative.id" class="creative-card">
                    <img
                      v-if="creativePreview(creative)"
                      :src="creativePreview(creative)"
                      :alt="creative.name"
                      class="creative-image"
                    />
                    <div v-else class="creative-fallback">{{ creative.object_type }}</div>

                    <div class="creative-copy">
                      <p>{{ creative.name }}</p>
                      <small>{{ resultKindLabel(creative.metrics.result_kind) }}</small>
                    </div>

                    <div class="creative-stats">
                      <span>{{ formatMetricValue('spend', creative.metrics.spend) }}</span>
                      <span>{{ formatCompactNumber(creative.metrics.results) }}</span>
                    </div>
                  </article>
                </div>
              </div>
            </section>

            <section class="list-surface">
              <div class="section-head">
                <span>{{ copy.campaigns }}</span>
              </div>

              <div v-if="report.campaigns.length === 0" class="empty-note">{{ copy.emptyCampaigns }}</div>

              <button
                v-for="campaign in report.campaigns"
                :key="campaign.id"
                type="button"
                class="campaign-row"
                :class="{ active: selectedCampaignId === campaign.id }"
                @click="selectCampaign(campaign.id)"
              >
                <div class="campaign-row-main">
                  <i class="status-dot" :class="statusTone(campaign.status)"></i>
                  <div>
                    <strong>{{ campaign.name }}</strong>
                    <small>{{ statusLabel(campaign.status) }}</small>
                  </div>
                </div>

                <div class="campaign-row-metrics">
                  <span>{{ formatMetricValue('spend', campaign.metrics.spend.current) }}</span>
                  <span>{{ formatMetricValue('ctr', campaign.metrics.ctr.current) }}</span>
                  <span>{{ formatMetricValue('cost_per_result', campaign.metrics.cost_per_result.current) }}</span>
                </div>
              </button>
            </section>
          </template>
        </template>
      </section>

      <aside class="rail rail-right">
        <section class="ai-surface verdict-surface">
          <div class="section-head">
            <span>{{ copy.aiVerdict }}</span>
          </div>
          <p class="surface-note">{{ copy.aiVerdictHint }}</p>
          <p v-if="verdictLoading" class="empty-note">{{ copy.loadingVerdict }}</p>
          <p v-else class="verdict-text">{{ autoVerdict || '—' }}</p>
        </section>

        <section class="ai-surface chat-surface">
          <div class="section-head">
            <span>{{ copy.aiChat }}</span>
          </div>
          <p class="surface-note">{{ copy.aiChatHint }}</p>

          <div class="control-grid">
            <label>
              <span>{{ copy.provider }}</span>
              <select v-model="provider">
                <option v-for="providerOption in providerCatalog" :key="providerOption.key" :value="providerOption.key">
                  {{ providerOption.label }}
                </option>
              </select>
            </label>

            <label>
              <span>{{ copy.model }}</span>
              <select v-model="selectedModelPreset">
                <option v-for="preset in availableModelPresets" :key="preset.value" :value="preset.value">
                  {{ presetLabel(preset) }}
                </option>
                <option v-if="activeProviderConfig?.supports_custom_model" :value="CUSTOM_MODEL_OPTION">
                  {{ copy.modelCustomOption }}
                </option>
              </select>
            </label>
          </div>

          <label v-if="isCustomModelSelected">
            <span>{{ copy.modelCustom }}</span>
            <input v-model.trim="customModel" type="text" :placeholder="copy.modelCustomPlaceholder" />
          </label>
          <p class="surface-note">{{ modelSelectionHint }}</p>

          <label>
            <span>{{ copy.apiKey }}</span>
            <input v-model="clientApiKey" type="password" placeholder="sk-..." />
          </label>
          <p class="surface-note">{{ copy.chatKeyHint }}</p>

          <div class="chat-stream">
            <article v-for="(message, index) in chatMessages" :key="index" class="chat-bubble" :class="message.role">
              {{ message.content }}
            </article>
            <p v-if="chatLoading" class="empty-note">{{ copy.loadingVerdict }}</p>
          </div>

          <div class="suggestion-row">
            <button
              v-for="suggestion in copy.helperQuestions"
              :key="suggestion"
              type="button"
              class="chip"
              @click="sendQuestion(suggestion)"
            >
              {{ suggestion }}
            </button>
          </div>

          <div class="chat-compose">
            <input
              v-model="chatDraft"
              type="text"
              :placeholder="copy.askPlaceholder"
              @keyup.enter.prevent="sendQuestion()"
            />
            <button
              type="button"
              class="primary-button compact"
              :disabled="chatLoading || !clientApiKey.trim() || !chatDraft.trim()"
              @click="sendQuestion()"
            >
              {{ copy.send }}
            </button>
          </div>

          <p v-if="chatError" class="message error">{{ chatError }}</p>
        </section>
      </aside>
    </main>
  </div>
</template>
