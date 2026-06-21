<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

type Locale = 'ru' | 'kz' | 'en'
type AuthMode = 'login' | 'register'
type AIProvider = 'anthropic' | 'openai' | 'gemini'
type AppView = 'app' | 'privacy' | 'dataDeletion'
type OAuthProvider = 'meta' | 'google_ads'
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

interface GoogleAdsCustomer {
  id: string
  external_customer_id: string
  resource_name: string
  descriptive_name: string
  currency_code: string | null
  time_zone: string | null
  is_manager: boolean
  is_directly_accessible: boolean
  hierarchy_level: number
  root_customer_id: string | null
  manager_customer_id: string | null
  login_customer_id: string | null
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

interface SavedProviderKey {
  provider: AIProvider
  has_saved_key: boolean
  updated_at: string
}

interface PrivacySection {
  id: string
  title: string
  paragraphs?: readonly string[]
  bullets?: readonly string[]
}

interface OAuthStatus {
  provider: OAuthProvider
  status: 'success' | 'error'
  message: string
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
const LEGACY_STORAGE_LOCALE_KEY = 'chatico.locale'
const STORAGE_LOCALE_OVERRIDE_KEY = 'chatico.locale_override'
const DEFAULT_LOCALE: Locale = 'ru'
const CUSTOM_MODEL_OPTION = '__custom__'
const PRIVACY_CONTACT_EMAIL = 'support@chatico.cc'
const PRIVACY_SERVICE_OPERATOR = 'Chatico Ads'
const PRIVACY_SERVICE_URL = 'https://ads.chatico.cc'
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

function normalizePathname(value: string): string {
  const trimmed = trimTrailingSlash(value.trim())
  return trimmed === '' ? '/' : trimmed
}

function buildRoutePath(segment: string): string {
  const base = trimTrailingSlash(APP_BASE_PATH)
  return normalizePathname(`${base}/${segment}`)
}

const APP_HOME_PATH = normalizePathname(APP_BASE_PATH)
const PRIVACY_ROUTE_PATH = buildRoutePath('privacy-policy')
const DATA_DELETION_ROUTE_PATH = buildRoutePath('data-deletion')

function isLocale(value: string | null | undefined): value is Locale {
  return value === 'ru' || value === 'kz' || value === 'en'
}

function resolveInitialLocale(): Locale {
  const storedOverride = localStorage.getItem(STORAGE_LOCALE_OVERRIDE_KEY)
  return isLocale(storedOverride) ? storedOverride : DEFAULT_LOCALE
}

const privacyContent = {
  ru: {
    privacyPolicy: 'Политика приватности',
    backToApp: 'К приложению',
    dataDeletionLabel: 'Удаление данных',
    privacyTitle: 'Как Chatico Ads обрабатывает данные Meta и данные пользователя',
    privacyLead:
      `Эта политика описывает, какие данные собирает сервис, зачем они используются, кому могут передаваться и как запросить удаление. Официальный адрес сервиса: ${PRIVACY_SERVICE_URL}. Документ предназначен для публичного доступа и соответствует требованиям Meta App Review.`,
    privacyUpdatedLabel: 'Обновлено',
    privacyUpdatedOn: '20 июня 2026',
    privacyMetaScopeLabel: 'Разрешение Meta',
    privacySections: [
      {
        id: 'overview',
        title: '1. Что делает сервис',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} помогает владельцу бизнеса подключить рекламный кабинет Meta и просматривать рекламную статистику в одном интерфейсе.`,
          'Сервис работает в режиме только чтения: не публикует контент, не отправляет сообщения от имени пользователя и не изменяет рекламные кампании.',
          `Оператор сервиса: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}). Контакт по вопросам данных: ${PRIVACY_CONTACT_EMAIL}.`,
        ],
      },
      {
        id: 'data-collected',
        title: '2. Какие данные мы получаем',
        bullets: [
          'данные аккаунта сервиса: email, язык интерфейса, данные для входа и токены сессии',
          'Meta Platform Data по разрешению ads_read: Meta user ID и имя профиля, рекламные аккаунты (ID, название, валюта, часовой пояс, статус), кампании, объявления, креативы, превью медиа и метрики эффективности (spend, impressions, clicks, reach и др.)',
          'кешированные снимки отчётов, сформированные из Meta-данных, хранятся на сервере до истечения срока или удаления',
          'технические данные: IP-адрес, сведения о браузере и запросе, серверные логи — для безопасности, диагностики и предотвращения злоупотреблений',
          'по явному выбору пользователя для AI-функций: текст вопроса, выбранный AI-провайдер, ответ модели; при сохранении — API-ключ провайдера в зашифрованном виде',
        ],
      },
      {
        id: 'data-use',
        title: '3. Зачем мы используем данные',
        bullets: [
          'для регистрации, входа и изоляции данных между пользователями',
          'для подключения Meta, загрузки, кеширования и отображения рекламной статистики',
          'для формирования AI-сводки и AI-ответов только по явному запросу пользователя',
          'для обеспечения безопасности, мониторинга ошибок и стабильной работы сервиса',
        ],
      },
      {
        id: 'meta-permissions',
        title: '4. Какие Meta permissions использует приложение',
        paragraphs: [
          'Приложение запрашивает только разрешение ads_read.',
          'Оно используется исключительно для чтения рекламных данных и построения отчётов. Приложение не запрашивает ads_management, business_management, права на публикацию, редактирование рекламы или управление страницами.',
        ],
      },
      {
        id: 'storage-security',
        title: '5. Хранение, передача и защита данных',
        bullets: [
          'Meta access tokens и пользовательские API-ключи AI-провайдеров хранятся на сервере в зашифрованном виде',
          'данные не продаются и не передаются третьим лицам для их собственного маркетинга или рекламы',
          'для AI-функций мы можем передавать выбранному процессору (например, Google Gemini или Anthropic) только вопрос пользователя и агрегированный контекст отчёта; Meta access tokens и полные сырые выгрузки Meta не передаются',
          'отчёты кешируются кратковременно в памяти и могут сохраняться как снимки в базе данных до истечения срока хранения или удаления по запросу',
          'данные хранятся только столько, сколько нужно для работы сервиса, соблюдения закона, срока действия токенов или снимков, либо до выполнения запроса на удаление',
        ],
      },
      {
        id: 'data-deletion',
        title: '6. Как запросить удаление данных',
        paragraphs: [
          'Вы можете прекратить доступ приложения к Meta в настройках Facebook: Settings & Privacy → Settings → Apps and Websites → выберите приложение → Remove.',
          `Чтобы удалить данные, сохранённые в ${PRIVACY_SERVICE_OPERATOR}, напишите на ${PRIVACY_CONTACT_EMAIL} с темой "Data deletion request". Укажите email аккаунта сервиса; если известен Meta ad account ID — приложите его.`,
        ],
        bullets: [
          'мы подтвердим получение запроса',
          'удалим аккаунт сервиса, токены, Meta-подключения, записи рекламных аккаунтов, снимки отчётов и сохранённые AI-ключи, если закон не требует временно сохранить часть данных',
          'сообщим, когда удаление завершено',
        ],
      },
      {
        id: 'rights',
        title: '7. Права пользователя',
        bullets: [
          'запросить доступ к данным, исправление или удаление',
          'отозвать доступ Meta через настройки Facebook или запросить удаление данных у нас',
          'не использовать AI-функции и не сохранять свой API-ключ провайдера',
        ],
      },
      {
        id: 'contact',
        title: '8. Контакты',
        paragraphs: [
          `По вопросам конфиденциальности, использования Meta Platform Data и удаления данных: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
  kz: {
    privacyPolicy: 'Құпиялылық саясаты',
    backToApp: 'Қосымшаға оралу',
    dataDeletionLabel: 'Деректерді жою',
    privacyTitle: 'Chatico Ads Meta және пайдаланушы деректерін қалай өңдейді',
    privacyLead:
      `Бұл саясат сервис қандай деректерді жинайтынын, не үшін пайдаланатынын, кімге берілетінін және оларды қалай жоюға болатынын түсіндіреді. Сервистің ресми мекенжайы: ${PRIVACY_SERVICE_URL}. Құжат жария қолдануға жарайды және Meta App Review талаптарына сәйкес.`,
    privacyUpdatedLabel: 'Жаңартылды',
    privacyUpdatedOn: '2026 жылғы 20 маусым',
    privacyMetaScopeLabel: 'Meta рұқсаты',
    privacySections: [
      {
        id: 'overview',
        title: '1. Сервис не істейді',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} бизнес иесіне Meta жарнама кабинетін қосып, жарнама статистикасын бір интерфейсте көруге көмектеседі.`,
          'Сервис тек оқу режимінде жұмыс істейді: пайдаланушы атынан контент жарияламайды, хабарлама жібермейді және жарнамалық кампанияларды өзгертпейді.',
          `Сервис операторы: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}). Деректер бойынша байланыс: ${PRIVACY_CONTACT_EMAIL}.`,
        ],
      },
      {
        id: 'data-collected',
        title: '2. Қандай деректер жиналады',
        bullets: [
          'сервис аккаунты деректері: email, интерфейс тілі, кіру деректері және сессия токендері',
          'ads_read рұқсаты арқылы Meta Platform Data: Meta user ID және профиль аты, жарнама аккаунттары (ID, атау, валюта, уақыт белдеуі, статус), кампаниялар, жарнамалар, креативтер, медиа-превью және тиімділік метрикалары (spend, impressions, clicks, reach және т.б.)',
          'Meta деректерінен құрылған кештеулі есеп снимоктары серверде мерзімі біткенше немесе жойылғанша сақталады',
          'техникалық деректер: IP-мекенжай, браузер/сұрау деректері, сервер логтары — қауіпсіздік, диагностика және теріс пайдалануды болдырмау үшін',
          'AI-функцияларды пайдаланушы таңдағанда: сұрақ мәтіні, таңдалған AI-провайдер, модель жауабы; сақталса — провайдер API-килті шифрланған түрде',
        ],
      },
      {
        id: 'data-use',
        title: '3. Деректер не үшін қолданылады',
        bullets: [
          'тіркелу, кіру және пайдаланушылар арасында деректерді оқшаулау үшін',
          'Meta қосу, жарнама статистикасын жүктеу, кэштеу және көрсету үшін',
          'пайдаланушы нақты сұрағанда AI-қорытынды мен AI-жауап беру үшін',
          'қауіпсіздік, қателерді бақылау және сервистің тұрақты жұмысы үшін',
        ],
      },
      {
        id: 'meta-permissions',
        title: '4. Қандай Meta permission қолданылады',
        paragraphs: [
          'Қолданба тек ads_read рұқсатын сұрайды.',
          'Ол тек жарнама деректерін оқу және есеп құру үшін қолданылады. Қолданба ads_management, business_management, жариялау, жарнаманы өзгерту немесе беттерді басқару рұқсаттарын сұрамайды.',
        ],
      },
      {
        id: 'storage-security',
        title: '5. Сақтау, беру және қорғау',
        bullets: [
          'Meta access token-дері және пайдаланушы AI API-килттері серверде шифрланған түрде сақталады',
          'деректер сатылмайды және үшінші тараптардың өз маркетинг/жарнама мақсаттарына берілмейді',
          'AI-функциялар үшін таңдалған процессорға (мысалы, Google Gemini немесе Anthropic) тек пайдаланушы сұрағы мен агрегатталған есеп контексті берілуі мүмкін; Meta access token-дері мен толық шикі Meta деректері берілмейді',
          'есептер қысқа уақытқа жадта кэштеледі және дерекқорда снимок ретінде мерзімге дейін сақталуы мүмкін',
          'деректер сервис жұмысына, заң талаптарына, токен/снимок мерзіміне немесе жою сұрауына дейін ғана сақталады',
        ],
      },
      {
        id: 'data-deletion',
        title: '6. Деректерді жоюды қалай сұрауға болады',
        paragraphs: [
          'Meta-ға қолданба доступын Facebook баптауларынан өшіруге болады: Settings & Privacy → Settings → Apps and Websites → қолданбаны таңдаңыз → Remove.',
          `${PRIVACY_SERVICE_OPERATOR} сақтаған деректерді жою үшін ${PRIVACY_CONTACT_EMAIL} адресіне "Data deletion request" тақырыбымен хат жіберіңіз. Сервис email-ін көрсетіңіз; Meta ad account ID белгілі болса, қосыңыз.`,
        ],
        bullets: [
          'сұраудың алынғанын растаймыз',
          'сервис аккаунты, токендер, Meta байланыстары, жарнама аккаунттары, есеп снимоктары және AI-килттер жойылады; заң уақытша сақтау талап етпесе',
          'жою аяқталған соң хабарлаймыз',
        ],
      },
      {
        id: 'rights',
        title: '7. Пайдаланушы құқықтары',
        bullets: [
          'деректерге қол жеткізуді, түзетуді немесе жоюды сұрау',
          'Facebook баптаулары арқылы Meta доступын кері алу немесе бізден деректерді жоюды сұрау',
          'AI-функцияларды қолданбау және провайдер API-килтін сақтамау',
        ],
      },
      {
        id: 'contact',
        title: '8. Байланыс',
        paragraphs: [
          `Құпиялылық, Meta Platform Data және деректерді жою бойынша: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
  en: {
    privacyPolicy: 'Privacy Policy',
    backToApp: 'Back to App',
    dataDeletionLabel: 'Data Deletion',
    privacyTitle: 'Privacy Policy — Chatico Ads',
    privacyLead:
      `This Privacy Policy explains what data Chatico Ads collects, why we use it, which third parties may process it, and how you can request deletion. The official production URL is ${PRIVACY_SERVICE_URL}. This document is published for public access and is intended to meet Meta App Review requirements.`,
    privacyUpdatedLabel: 'Last updated',
    privacyUpdatedOn: 'June 20, 2026',
    privacyMetaScopeLabel: 'Meta permission',
    privacySections: [
      {
        id: 'overview',
        title: '1. What the service does',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} helps business owners connect a Meta ad account and review advertising performance in one dashboard.`,
          'The service is read-only: it does not publish content, send messages on behalf of users, or modify advertising campaigns.',
          `Service operator: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}). Data protection contact: ${PRIVACY_CONTACT_EMAIL}.`,
        ],
      },
      {
        id: 'data-collected',
        title: '2. What data we collect',
        bullets: [
          'account data you provide to Chatico Ads: email address, interface language, login credentials, and session tokens',
          'Meta Platform Data obtained through the ads_read permission: Meta user ID and profile name, ad account metadata (ID, name, currency, timezone, status), campaigns, ads, creatives, media preview URLs, and performance metrics such as spend, impressions, clicks, and reach',
          'cached report snapshots derived from Meta data, stored on our servers until they expire or are deleted',
          'technical data collected automatically: IP address, browser and request metadata, and server logs for security, troubleshooting, and abuse prevention',
          'when you choose to use AI features: your question, selected AI provider, model response, and—if you save it—your provider API key in encrypted form',
        ],
      },
      {
        id: 'data-use',
        title: '3. How and why we use data',
        bullets: [
          'to register and authenticate users and keep each customer\'s data isolated',
          'to connect Meta accounts, fetch advertising statistics, cache reports, and display dashboards',
          'to generate AI summaries and chat answers only when you explicitly request them',
          'to operate the service securely, monitor errors, and prevent abuse',
        ],
      },
      {
        id: 'meta-permissions',
        title: '4. Meta permissions used by the app',
        paragraphs: [
          'The app requests only the ads_read permission.',
          'It is used solely to read advertising data and build reports. The app does not request ads_management, business_management, publishing, ad editing, or page management permissions.',
        ],
      },
      {
        id: 'storage-security',
        title: '5. Storage, sharing, and security',
        bullets: [
          'Meta access tokens and user-provided AI provider API keys are stored on our servers in encrypted form',
          'we do not sell data and do not share it with third parties for their own marketing or advertising',
          'for AI features, we may send your question and an aggregated report summary to the processor you select (for example, Google Gemini or Anthropic); we do not send Meta access tokens or full raw Meta exports',
          'reports are cached briefly in memory and may also be stored as time-limited snapshots in our database',
          'we retain data only as long as needed to operate the service, comply with law, honor token or snapshot expiry, or until a valid deletion request is completed',
        ],
      },
      {
        id: 'data-deletion',
        title: '6. How to request deletion of your data',
        paragraphs: [
          'To revoke the app\'s access to Meta, go to Facebook settings: Settings & Privacy → Settings → Apps and Websites → select the app → Remove.',
          `To delete data stored by ${PRIVACY_SERVICE_OPERATOR}, email ${PRIVACY_CONTACT_EMAIL} with the subject line "Data deletion request". Include the email address linked to your Chatico Ads account. If you know your Meta ad account ID, include it as well.`,
        ],
        bullets: [
          'we will confirm receipt of your request',
          'we will delete your service account, tokens, Meta connections, ad account records, report snapshots, and saved AI keys unless we are legally required to retain specific data temporarily',
          'we will notify you when deletion is complete',
        ],
      },
      {
        id: 'rights',
        title: '7. Your choices and rights',
        bullets: [
          'request access to, correction of, or deletion of your data',
          'revoke Meta access through Facebook settings or ask us to delete stored data',
          'avoid AI features and choose not to store a provider API key',
        ],
      },
      {
        id: 'contact',
        title: '8. Contact',
        paragraphs: [
          `For privacy questions, Meta Platform Data usage, or deletion requests, contact ${PRIVACY_CONTACT_EMAIL}. Operator: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
} as const

const translations = {
  ru: {
    ...privacyContent.ru,
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
    connectGoogle: 'Подключить Google Ads',
    accounts: 'Кабинеты',
    googleAds: 'Google Ads',
    googleAccountsEmpty: 'Google Ads пока не подключён.',
    directAccess: 'Прямой доступ',
    viaManager: 'Через MCC',
    managerAccount: 'MCC',
    clientAccount: 'Клиент',
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
    aiVerdict: 'ИИ анализ',
    aiVerdictHint: 'После загрузки данных сервис показывает короткий вывод: что работает, что проседает и что стоит сделать дальше.',
    aiVerdictInfoLabel: 'Что это',
    showVerdictDetails: 'Подробнее',
    hideVerdictDetails: 'Скрыть детали',
    aiChat: 'AI-чат по данным',
    aiChatHint: 'Задайте вопрос по рекламным данным и получите короткий ответ.',
    chatDefaultModeHint: 'По умолчанию чат использует встроенный Gemini 3.5 Flash.',
    useOwnApiKey: 'Использовать свой API ключ',
    hideOwnApiKey: 'Скрыть свой API ключ',
    customAiSettingsHint: 'Если хотите использовать свой провайдер, модель и ключ, откройте настройки ниже.',
    missingCustomKeyError: 'Чтобы использовать свой API ключ, вставьте его в поле ниже или сохраните ключ для выбранного провайдера.',
    apiKey: 'API ключ клиента',
    saveApiKey: 'Сохранить ключ',
    replaceApiKey: 'Заменить ключ',
    removeApiKey: 'Удалить ключ',
    cancel: 'Отмена',
    model: 'Модель',
    modelDefaultOption: 'Рекомендуемая',
    modelCustom: 'Своя модель',
    modelCustomOption: 'Указать вручную',
    modelCustomPlaceholder: 'Например: claude-sonnet-4-6',
    modelDefaultHint: 'Сейчас выбрана модель',
    modelCustomHint: 'Если нужна другая модель, укажите её точное имя у провайдера. Если оставить поле пустым, будет использована выбранная выше модель.',
    provider: 'Провайдер',
    askPlaceholder: 'Спросить по кампаниям, креативам или CPA...',
    send: 'Отправить',
    loading: 'Загружаем рабочую панель...',
    loadingReport: 'Собираем Meta-отчёт...',
    loadingVerdict: 'Готовим ИИ-анализ...',
    loadingChat: 'Готовим ответ...',
    emptyCampaigns: 'Кампании не найдены для выбранного периода.',
    emptyCreatives: 'Meta не вернула превью креативов по этой кампании.',
    oauthSuccess: 'Meta успешно подключена. Данные кабинета уже доступны.',
    oauthError: 'Подключение Meta завершилось ошибкой.',
    googleOauthSuccess: 'Google Ads успешно подключён. Аккаунты синхронизированы.',
    googleOauthError: 'Подключение Google Ads завершилось ошибкой.',
    chatKeyHint: 'Можно использовать ключ Anthropic, OpenAI или Gemini.',
    savedKeyHint: 'Ключ для выбранного провайдера уже сохранён на сервере и будет использоваться автоматически.',
    apiKeySavedNotice: 'Ключ сохранён и теперь будет использоваться автоматически.',
    apiKeyRemovedNotice: 'Сохранённый ключ удалён.',
    creativeMetricLabels: {
      spend: 'Потрачено',
      impressions: 'Показы',
      clicks: 'Клики',
      ctr: 'CTR',
    },
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
    ...privacyContent.kz,
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
    connectGoogle: 'Google Ads қосу',
    accounts: 'Кабинеттер',
    googleAds: 'Google Ads',
    googleAccountsEmpty: 'Google Ads әлі қосылмаған.',
    directAccess: 'Тікелей қолжетім',
    viaManager: 'MCC арқылы',
    managerAccount: 'MCC',
    clientAccount: 'Клиент',
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
    aiVerdict: 'AI талдау',
    aiVerdictHint: 'Деректер жүктелгеннен кейін сервис не жұмыс істеп тұрғанын, не әлсірегенін және келесі қадамды қысқа түрде көрсетеді.',
    aiVerdictInfoLabel: 'Бұл не',
    showVerdictDetails: 'Толығырақ',
    hideVerdictDetails: 'Жасыру',
    aiChat: 'Дерекпен AI-чат',
    aiChatHint: 'Жарнама деректері бойынша сұрақ қойып, қысқа жауап алыңыз.',
    chatDefaultModeHint: 'Әдепкіде чат кіріктірілген Gemini 3.5 Flash моделін қолданады.',
    useOwnApiKey: 'Өз API кілтіңізді қолдану',
    hideOwnApiKey: 'Өз API кілтін жасыру',
    customAiSettingsHint: 'Егер өз провайдеріңізді, моделіңізді және кілтіңізді қолданғыңыз келсе, төмендегі баптауларды ашыңыз.',
    missingCustomKeyError: 'Өз API кілтіңізді пайдалану үшін оны төмендегі өріске енгізіңіз немесе таңдалған провайдер үшін кілтті сақтаңыз.',
    apiKey: 'Клиент API кілті',
    saveApiKey: 'Кілтті сақтау',
    replaceApiKey: 'Кілтті ауыстыру',
    removeApiKey: 'Кілтті жою',
    cancel: 'Бас тарту',
    model: 'Модель',
    modelDefaultOption: 'Ұсынылатын',
    modelCustom: 'Өз моделі',
    modelCustomOption: 'Қолмен енгізу',
    modelCustomPlaceholder: 'Мысалы: claude-sonnet-4-6',
    modelDefaultHint: 'Қазір мына модель қолданылады',
    modelCustomHint: 'Егер басқа модель керек болса, оның атауын провайдердегідей дәл енгізіңіз. Өріс бос қалса, жоғарыда таңдалған модель қолданылады.',
    provider: 'Провайдер',
    askPlaceholder: 'Кампания, креатив немесе CPA туралы сұраңыз...',
    send: 'Жіберу',
    loading: 'Жұмыс панелі жүктеліп жатыр...',
    loadingReport: 'Meta есебі жиналып жатыр...',
    loadingVerdict: 'AI талдау дайындалып жатыр...',
    loadingChat: 'Жауап дайындалып жатыр...',
    emptyCampaigns: 'Таңдалған кезең бойынша кампания табылмады.',
    emptyCreatives: 'Бұл кампания үшін Meta креатив превьюін қайтармады.',
    oauthSuccess: 'Meta сәтті қосылды. Кабинет деректері дайын.',
    oauthError: 'Meta қосу кезінде қате болды.',
    googleOauthSuccess: 'Google Ads сәтті қосылды. Аккаунттар синхрондалды.',
    googleOauthError: 'Google Ads қосу кезінде қате болды.',
    chatKeyHint: 'Anthropic, OpenAI немесе Gemini кілтін қолдануға болады.',
    savedKeyHint: 'Таңдалған провайдер кілті серверде сақталған және автоматты түрде қолданылады.',
    apiKeySavedNotice: 'Кілт сақталды және енді автоматты түрде қолданылады.',
    apiKeyRemovedNotice: 'Сақталған кілт жойылды.',
    creativeMetricLabels: {
      spend: 'Жұмсалған',
      impressions: 'Көрсетілім',
      clicks: 'Клик',
      ctr: 'CTR',
    },
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
    ...privacyContent.en,
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
    connectGoogle: 'Connect Google Ads',
    accounts: 'Accounts',
    googleAds: 'Google Ads',
    googleAccountsEmpty: 'Google Ads is not connected yet.',
    directAccess: 'Direct access',
    viaManager: 'Via MCC',
    managerAccount: 'MCC',
    clientAccount: 'Client',
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
    aiVerdict: 'AI analysis',
    aiVerdictHint: 'After the data loads, the app shows a short summary of what is working, what is slipping, and what to do next.',
    aiVerdictInfoLabel: 'What is this',
    showVerdictDetails: 'Show details',
    hideVerdictDetails: 'Hide details',
    aiChat: 'AI chat with data',
    aiChatHint: 'Ask about the ad data and get a short answer.',
    chatDefaultModeHint: 'By default, chat uses the built-in Gemini 3.5 Flash.',
    useOwnApiKey: 'Use your own API key',
    hideOwnApiKey: 'Hide your API key',
    customAiSettingsHint: 'If you want your own provider, model, and key, open the settings below.',
    missingCustomKeyError: 'To use your own API key, enter it below or save a key for the selected provider.',
    apiKey: 'Client API key',
    saveApiKey: 'Save key',
    replaceApiKey: 'Replace key',
    removeApiKey: 'Delete key',
    cancel: 'Cancel',
    model: 'Model',
    modelDefaultOption: 'Recommended',
    modelCustom: 'Custom model',
    modelCustomOption: 'Enter manually',
    modelCustomPlaceholder: 'Example: claude-sonnet-4-6',
    modelDefaultHint: 'Current model',
    modelCustomHint: 'If you need a different model, enter its exact provider name. Leaving the field empty keeps the selected model above.',
    provider: 'Provider',
    askPlaceholder: 'Ask about campaigns, creatives, or CPA...',
    send: 'Send',
    loading: 'Loading workspace...',
    loadingReport: 'Building Meta report...',
    loadingVerdict: 'Preparing AI analysis...',
    loadingChat: 'Preparing the answer...',
    emptyCampaigns: 'No campaigns were returned for this period.',
    emptyCreatives: 'Meta did not return creative previews for this campaign.',
    oauthSuccess: 'Meta connected successfully. Account data is ready.',
    oauthError: 'Meta connection failed.',
    googleOauthSuccess: 'Google Ads connected successfully. Accounts are synced.',
    googleOauthError: 'Google Ads connection failed.',
    chatKeyHint: 'You can use an Anthropic, OpenAI, or Gemini key.',
    savedKeyHint: 'A key for the selected provider is already stored on the server and will be used automatically.',
    apiKeySavedNotice: 'The key has been saved and will now be used automatically.',
    apiKeyRemovedNotice: 'The saved key has been removed.',
    creativeMetricLabels: {
      spend: 'Spend',
      impressions: 'Impressions',
      clicks: 'Clicks',
      ctr: 'CTR',
    },
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
    key: 'gemini',
    label: 'Gemini',
    default_model: 'gemini-3.5-flash',
    presets: [
      { value: 'gemini-3.5-flash', label: 'gemini-3.5-flash', is_default: true },
      { value: 'gemini-3.1-flash-lite', label: 'gemini-3.1-flash-lite', is_default: false },
    ],
    supports_custom_model: true,
  },
  {
    key: 'anthropic',
    label: 'Anthropic',
    default_model: 'claude-sonnet-4-6',
    presets: [{ value: 'claude-sonnet-4-6', label: 'claude-sonnet-4-6', is_default: true }],
    supports_custom_model: true,
  },
  {
    key: 'openai',
    label: 'OpenAI',
    default_model: 'gpt-5-mini',
    presets: [{ value: 'gpt-5-mini', label: 'gpt-5-mini', is_default: true }],
    supports_custom_model: true,
  },
]

const authMode = ref<AuthMode>('login')
const locale = ref<Locale>(resolveInitialLocale())
const registerLocale = ref<Locale>(locale.value)
const accessToken = ref(localStorage.getItem(STORAGE_TOKEN_KEY) ?? '')
const user = ref<User | null>(null)
const currentView = ref<AppView>(resolveCurrentView(window.location.pathname))
const oauthStatus = ref<OAuthStatus | null>(null)
const authForm = ref({ email: '', password: '' })
const authError = ref('')
const pageError = ref('')
const authLoading = ref(false)
const bootLoading = ref(true)
const metaConnecting = ref(false)
const googleConnecting = ref(false)
const accountsLoading = ref(false)
const googleAccountsLoading = ref(false)
const reportLoading = ref(false)
const verdictLoading = ref(false)
const chatLoading = ref(false)
const reportDays = ref(30)
const accounts = ref<MetaAccount[]>([])
const googleAccounts = ref<GoogleAdsCustomer[]>([])
const selectedAccountId = ref('')
const report = ref<DashboardReport | null>(null)
const selectedCampaignId = ref('')
const autoVerdict = ref('')
const autoVerdictExpanded = ref(false)
const chatMessages = ref<ChatMessage[]>([])
const chatDraft = ref('')
const chatError = ref('')
const useClientCredentials = ref(false)
const provider = ref<AIProvider>('gemini')
const providerCatalog = ref<AIProviderCatalog[]>(fallbackProviderCatalog)
const savedProviderKeys = ref<Partial<Record<AIProvider, SavedProviderKey>>>({})
const clientApiKey = ref('')
const providerKeyLoading = ref(false)
const providerKeyEditing = ref(false)
const providerKeyError = ref('')
const providerKeyNotice = ref('')
const localeUpdateRequestId = ref(0)
const reportContextKey = ref('')
const customModel = ref('')
const selectedModelPreset = ref(
  fallbackProviderCatalog.find((providerOption) => providerOption.key === provider.value)?.default_model ?? '',
)
const appViewInitialized = ref(false)

const copy = computed(() => translations[locale.value])
const isAuthenticated = computed(() => user.value !== null)
const isPolicyView = computed(() => currentView.value === 'privacy' || currentView.value === 'dataDeletion')
const headerTitle = computed(() => {
  if (isPolicyView.value) {
    return copy.value.privacyPolicy
  }
  return isAuthenticated.value ? copy.value.workspace : copy.value.authLead
})
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
const currentSavedProviderKey = computed(() => {
  return savedProviderKeys.value[provider.value] ?? null
})
const hasSavedProviderKey = computed(() => {
  return Boolean(currentSavedProviderKey.value?.has_saved_key)
})
const showProviderKeyInput = computed(() => {
  return useClientCredentials.value && (!hasSavedProviderKey.value || providerKeyEditing.value)
})
const canUseSavedProviderKey = computed(() => {
  return useClientCredentials.value && hasSavedProviderKey.value && !providerKeyEditing.value && clientApiKey.value.trim() === ''
})
const canSendChat = computed(() => {
  if (!chatDraft.value.trim() || !selectedAccountId.value) {
    return false
  }
  if (!useClientCredentials.value) {
    return true
  }
  return canUseSavedProviderKey.value || Boolean(clientApiKey.value.trim())
})
const autoVerdictSections = computed(() => splitAutoVerdict(autoVerdict.value))
const autoVerdictSummary = computed(() => {
  return autoVerdictSections.value.summary || autoVerdict.value.trim() || ''
})
const autoVerdictDetails = computed(() => {
  return autoVerdictSections.value.details
})
const hasAutoVerdictDetails = computed(() => Boolean(autoVerdictDetails.value))
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
  const successMessage = oauthStatus.value.provider === 'google_ads' ? copy.value.googleOauthSuccess : copy.value.oauthSuccess
  const errorMessage = oauthStatus.value.provider === 'google_ads' ? copy.value.googleOauthError : copy.value.oauthError
  return oauthStatus.value.status === 'success'
    ? successMessage
    : `${errorMessage}${oauthStatus.value.message ? `: ${oauthStatus.value.message}` : ''}`
})
const policySections = computed<readonly PrivacySection[]>(() => copy.value.privacySections)

function resolveCurrentView(pathname: string): AppView {
  const normalized = normalizePathname(pathname)
  if (normalized === PRIVACY_ROUTE_PATH) {
    return 'privacy'
  }
  if (normalized === DATA_DELETION_ROUTE_PATH) {
    return 'dataDeletion'
  }
  return 'app'
}

function routePathForView(view: AppView): string {
  if (view === 'privacy') {
    return PRIVACY_ROUTE_PATH
  }
  if (view === 'dataDeletion') {
    return DATA_DELETION_ROUTE_PATH
  }
  return APP_HOME_PATH
}

async function syncView(view: AppView) {
  if (view === 'app') {
    if (!appViewInitialized.value) {
      appViewInitialized.value = true
      await loadProviderCatalog()
      await bootstrapSession()
    }
    window.scrollTo({ top: 0, behavior: 'auto' })
    return
  }

  await nextTick()
  const sectionId = view === 'dataDeletion' ? 'data-deletion' : 'overview'
  document.getElementById(sectionId)?.scrollIntoView({ block: 'start' })
}

function navigateToView(view: AppView) {
  const target = routePathForView(view)
  if (normalizePathname(window.location.pathname) !== target) {
    window.history.pushState({}, '', target)
  }
  currentView.value = view
}

function openPrivacyPolicy() {
  navigateToView('privacy')
}

function openDataDeletion() {
  navigateToView('dataDeletion')
}

function openAppView() {
  navigateToView('app')
}

function handlePopState() {
  currentView.value = resolveCurrentView(window.location.pathname)
}

function updateDocumentTitle() {
  if (isPolicyView.value) {
    document.title = `${copy.value.privacyPolicy} · ${copy.value.brand}`
    return
  }
  document.title = copy.value.brand
}

function formatUnexpectedError(error: unknown) {
  return error instanceof Error ? error.message : 'Unexpected error'
}

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }
    return entities[character] ?? character
  })
}

function renderInlineMarkdown(value: string) {
  const tokenPrefix = `@@MD_${Math.random().toString(36).slice(2)}_${Date.now()}_`
  const tokens: string[] = []
  const reserveToken = (replacement: string) => {
    const token = `${tokenPrefix}${tokens.length}@@`
    tokens.push(replacement)
    return token
  }

  let text = value.replace(/`([^`\n]+)`/g, (_match, code: string) => {
    return reserveToken(`<code>${escapeHtml(code)}</code>`)
  })

  text = text.replace(/\[([^\]\n]+)\]\(((?:https?:\/\/|mailto:)[^\s)]+)\)/g, (_match, label: string, href: string) => {
    return reserveToken(
      `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer noopener">${escapeHtml(label)}</a>`,
    )
  })

  text = escapeHtml(text)
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/(^|[^\*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')

  for (const [index, token] of tokens.entries()) {
    text = text.split(`${tokenPrefix}${index}@@`).join(token)
  }

  return text
}

function renderMarkdown(value: string) {
  const normalized = value.replace(/\r\n?/g, '\n').trim()
  if (!normalized) {
    return ''
  }

  const blocks: string[] = []
  const lines = normalized.split('\n')
  let paragraphLines: string[] = []
  let listType: 'ul' | 'ol' | null = null
  let listItems: string[] = []
  let inCodeBlock = false
  let codeLines: string[] = []

  const flushParagraph = () => {
    if (paragraphLines.length === 0) {
      return
    }
    const paragraphHtml = renderInlineMarkdown(paragraphLines.join('\n')).replace(/\n/g, '<br />')
    blocks.push(`<p>${paragraphHtml}</p>`)
    paragraphLines = []
  }

  const flushList = () => {
    if (!listType || listItems.length === 0) {
      return
    }
    const itemsHtml = listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')
    blocks.push(`<${listType}>${itemsHtml}</${listType}>`)
    listType = null
    listItems = []
  }

  const flushCodeBlock = () => {
    if (!codeLines.length) {
      return
    }
    blocks.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    codeLines = []
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (trimmed.startsWith('```')) {
      flushParagraph()
      flushList()
      if (inCodeBlock) {
        flushCodeBlock()
        inCodeBlock = false
      } else {
        inCodeBlock = true
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }

    if (!trimmed) {
      flushParagraph()
      flushList()
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = Math.min(headingMatch[1].length + 3, 6)
      blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }

    const unorderedItemMatch = trimmed.match(/^[-*]\s+(.*)$/)
    if (unorderedItemMatch) {
      flushParagraph()
      if (listType && listType !== 'ul') {
        flushList()
      }
      listType = 'ul'
      listItems.push(unorderedItemMatch[1])
      continue
    }

    const orderedItemMatch = trimmed.match(/^\d+\.\s+(.*)$/)
    if (orderedItemMatch) {
      flushParagraph()
      if (listType && listType !== 'ol') {
        flushList()
      }
      listType = 'ol'
      listItems.push(orderedItemMatch[1])
      continue
    }

    if (listType) {
      flushList()
    }
    paragraphLines.push(trimmed)
  }

  flushParagraph()
  flushList()
  if (inCodeBlock) {
    flushCodeBlock()
  }

  return blocks.join('')
}

function splitMarkdownBlocks(value: string) {
  return value
    .replace(/\r\n/g, '\n')
    .trim()
    .split(/\n\s*\n+/)
    .map((block) => block.trim())
    .filter(Boolean)
}

function splitAutoVerdict(value: string) {
  const normalized = value.replace(/\r\n/g, '\n').trim()
  if (!normalized) {
    return { summary: '', details: '' }
  }

  const blocks = splitMarkdownBlocks(normalized)
  if (blocks.length > 1) {
    return {
      summary: blocks[0],
      details: blocks.slice(1).join('\n\n'),
    }
  }

  const lines = normalized.split('\n')
  const listLinePattern = /^([-*+]\s+|\d+\.\s+)/
  const headingPattern = /^#{1,6}\s+/

  const listStartIndex = lines.findIndex((line, index) => index > 0 && listLinePattern.test(line.trim()))
  if (listStartIndex > 0) {
    return {
      summary: lines.slice(0, listStartIndex).join('\n').trim(),
      details: lines.slice(listStartIndex).join('\n').trim(),
    }
  }

  const headingStartIndex = lines.findIndex((line, index) => index > 0 && headingPattern.test(line.trim()))
  if (headingStartIndex > 0) {
    return {
      summary: lines.slice(0, headingStartIndex).join('\n').trim(),
      details: lines.slice(headingStartIndex).join('\n').trim(),
    }
  }

  if (lines.length > 1 && listLinePattern.test(lines[0].trim())) {
    return {
      summary: lines[0].trim(),
      details: lines.slice(1).join('\n').trim(),
    }
  }

  return { summary: normalized, details: '' }
}

function resetAutoVerdict() {
  autoVerdict.value = ''
  autoVerdictExpanded.value = false
}

function triggerAutoVerdictLoad() {
  void loadAutoVerdict().catch((error) => {
    autoVerdict.value = formatUnexpectedError(error)
    autoVerdictExpanded.value = false
    verdictLoading.value = false
  })
}

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

function applyLocale(nextLocale: Locale, options: { persist?: boolean } = {}) {
  const persist = options.persist ?? true
  locale.value = nextLocale
  registerLocale.value = nextLocale
  document.documentElement.lang = nextLocale
  if (persist) {
    localStorage.setItem(STORAGE_LOCALE_OVERRIDE_KEY, nextLocale)
  }
}

function applyAuthenticatedLocale(userLocale: string) {
  if (isLocale(userLocale)) {
    applyLocale(userLocale, { persist: false })
    return
  }
  applyLocale(DEFAULT_LOCALE, { persist: false })
}

function reloadAutoVerdictForCurrentLocale() {
  if (selectedAccountId.value && report.value) {
    resetAutoVerdict()
    triggerAutoVerdictLoad()
  }
}

async function syncLocale(
  nextLocale: Locale,
  options: {
    persist?: boolean
    reloadVerdict?: boolean
    persistAccount?: boolean
  } = {},
) {
  const persist = options.persist ?? true
  const reloadVerdict = options.reloadVerdict ?? true
  const persistAccount = options.persistAccount ?? true
  const requestUserId = user.value?.id ?? null
  const persistGuestOverride = persist && !requestUserId
  const previousLocale = locale.value
  const shouldReloadVerdict = reloadVerdict && selectedAccountId.value && report.value

  if (nextLocale === previousLocale && (!requestUserId || user.value?.locale === nextLocale || !persistAccount)) {
    return
  }

  applyLocale(nextLocale, { persist: persistGuestOverride })

  if (!requestUserId || !persistAccount) {
    if (shouldReloadVerdict) {
      reloadAutoVerdictForCurrentLocale()
    }
    return
  }

  const requestId = localeUpdateRequestId.value + 1
  localeUpdateRequestId.value = requestId

  try {
    const payload = await apiRequest<User>('/auth/me/locale', {
      method: 'PATCH',
      body: {
        locale: nextLocale,
      },
    })
    if (localeUpdateRequestId.value !== requestId || user.value?.id !== requestUserId) {
      return
    }

    user.value = payload
    applyAuthenticatedLocale(payload.locale)
    pageError.value = ''
    if (shouldReloadVerdict) {
      reloadAutoVerdictForCurrentLocale()
    }
  } catch (error) {
    if (localeUpdateRequestId.value !== requestId || user.value?.id !== requestUserId) {
      return
    }

    applyLocale(previousLocale, { persist: persistGuestOverride })
    pageError.value = formatUnexpectedError(error)
    if (shouldReloadVerdict) {
      reloadAutoVerdictForCurrentLocale()
    }
  }
}

function persistAuth(payload: AuthResponse) {
  accessToken.value = payload.access_token
  user.value = payload.user
  localStorage.setItem(STORAGE_TOKEN_KEY, payload.access_token)
  applyAuthenticatedLocale(payload.user.locale)
}

function resetSession() {
  localeUpdateRequestId.value += 1
  accessToken.value = ''
  user.value = null
  accounts.value = []
  googleAccounts.value = []
  report.value = null
  selectedAccountId.value = ''
  selectedCampaignId.value = ''
  resetAutoVerdict()
  resetChatState()
  useClientCredentials.value = false
  savedProviderKeys.value = {}
  clientApiKey.value = ''
  providerKeyLoading.value = false
  providerKeyEditing.value = false
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  reportContextKey.value = ''
  googleConnecting.value = false
  googleAccountsLoading.value = false
  localStorage.removeItem(STORAGE_TOKEN_KEY)
  applyLocale(resolveInitialLocale(), { persist: false })
}

function resetChatState() {
  chatMessages.value = []
  chatDraft.value = ''
  chatError.value = ''
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  let payload: Record<string, unknown> = {}

  if (text) {
    try {
      const parsed = JSON.parse(text)
      if (parsed && typeof parsed === 'object') {
        payload = parsed as Record<string, unknown>
      }
    } catch {
      if (!response.ok) {
        throw new Error(text.trim() || `HTTP ${response.status}`)
      }
      throw new Error('Invalid JSON response')
    }
  }

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
  if ((providerParam === 'meta' || providerParam === 'google_ads') && (statusParam === 'success' || statusParam === 'error')) {
    oauthStatus.value = {
      provider: providerParam as OAuthProvider,
      status: statusParam,
      message: callbackUrl.searchParams.get('message') ?? '',
    }
    window.history.replaceState({}, '', APP_BASE_PATH)
  }

  try {
    if (accessToken.value) {
      user.value = await apiRequest<User>('/auth/me')
      applyAuthenticatedLocale(user.value.locale)
    } else {
      const refreshed = await refreshAuth()
      if (!refreshed) {
        return
      }
    }

    if (!user.value) {
      user.value = await apiRequest<User>('/auth/me')
      applyAuthenticatedLocale(user.value.locale)
    }
    await Promise.all([loadAccounts(), loadGoogleAccounts(), loadSavedProviderKeys()])
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

async function loadSavedProviderKeys() {
  if (!user.value) {
    savedProviderKeys.value = {}
    return
  }

  providerKeyError.value = ''

  try {
    const payload = await apiRequest<SavedProviderKey[]>('/ai/provider-keys')
    savedProviderKeys.value = payload.reduce<Partial<Record<AIProvider, SavedProviderKey>>>((accumulator, item) => {
      accumulator[item.provider] = item
      return accumulator
    }, {})
  } catch (error) {
    providerKeyError.value = formatUnexpectedError(error)
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
    await Promise.all([loadAccounts(), loadGoogleAccounts(), loadSavedProviderKeys()])
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
      resetAutoVerdict()
      reportContextKey.value = ''
      resetChatState()
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

async function loadGoogleAccounts() {
  if (!user.value) {
    googleAccounts.value = []
    return
  }

  googleAccountsLoading.value = true

  try {
    const payload = await apiRequest<GoogleAdsCustomer[]>('/google-ads/customers')
    googleAccounts.value = payload
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    googleAccountsLoading.value = false
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

async function connectGoogle() {
  googleConnecting.value = true
  pageError.value = ''

  try {
    const payload = await apiRequest<{ authorization_url: string }>('/google-ads/oauth/start')
    window.location.href = payload.authorization_url
  } catch (error) {
    googleConnecting.value = false
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  }
}

async function loadReport(options: { forceRefresh?: boolean } = {}) {
  if (!selectedAccountId.value) {
    return
  }

  const nextContextKey = `${selectedAccountId.value}:${reportDays.value}`
  reportLoading.value = true
  pageError.value = ''
  chatError.value = ''
  resetAutoVerdict()

  if (reportContextKey.value !== nextContextKey) {
    resetChatState()
  }

  try {
    const query = new URLSearchParams({
      days: String(reportDays.value),
    })
    if (options.forceRefresh) {
      query.set('force_refresh', 'true')
    }
    const payload = await apiRequest<DashboardReport>(
      `/dashboard/meta/ad-accounts/${selectedAccountId.value}/report?${query.toString()}`,
    )
    report.value = payload
    reportContextKey.value = nextContextKey
    selectedCampaignId.value =
      payload.campaigns.find((campaign) => campaign.id === selectedCampaignId.value)?.id ?? payload.campaigns[0]?.id ?? ''
    triggerAutoVerdictLoad()
  } catch (error) {
    pageError.value = formatUnexpectedError(error)
    resetAutoVerdict()
  } finally {
    reportLoading.value = false
  }
}

async function loadAutoVerdict() {
  try {
    if (!selectedAccountId.value) {
      return
    }

    verdictLoading.value = true
    autoVerdictExpanded.value = false
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
    autoVerdict.value = formatUnexpectedError(error)
    autoVerdictExpanded.value = false
  } finally {
    verdictLoading.value = false
  }
}

async function sendQuestion(question?: string) {
  const nextQuestion = (question ?? chatDraft.value).trim()
  const apiKey = useClientCredentials.value ? clientApiKey.value.trim() || null : null
  if (!nextQuestion || !selectedAccountId.value) {
    return
  }
  if (useClientCredentials.value && !apiKey && !canUseSavedProviderKey.value) {
    chatError.value = copy.value.missingCustomKeyError
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
        use_client_credentials: useClientCredentials.value,
        ...(useClientCredentials.value
          ? {
              provider: provider.value,
              api_key: apiKey,
              model: resolvedModel.value,
            }
          : {}),
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

async function saveProviderKey() {
  const nextKey = clientApiKey.value.trim()
  if (!nextKey) {
    return
  }

  providerKeyLoading.value = true
  providerKeyError.value = ''
  providerKeyNotice.value = ''

  try {
    const payload = await apiRequest<SavedProviderKey>(`/ai/provider-keys/${provider.value}`, {
      method: 'PUT',
      body: {
        api_key: nextKey,
      },
    })
    savedProviderKeys.value = {
      ...savedProviderKeys.value,
      [provider.value]: payload,
    }
    clientApiKey.value = ''
    providerKeyEditing.value = false
    providerKeyNotice.value = copy.value.apiKeySavedNotice
  } catch (error) {
    providerKeyError.value = formatUnexpectedError(error)
  } finally {
    providerKeyLoading.value = false
  }
}

async function deleteProviderKey() {
  if (!hasSavedProviderKey.value) {
    return
  }

  providerKeyLoading.value = true
  providerKeyError.value = ''
  providerKeyNotice.value = ''

  try {
    await apiRequest(`/ai/provider-keys/${provider.value}`, {
      method: 'DELETE',
    })
    const nextSavedProviderKeys = { ...savedProviderKeys.value }
    delete nextSavedProviderKeys[provider.value]
    savedProviderKeys.value = nextSavedProviderKeys
    clientApiKey.value = ''
    providerKeyEditing.value = false
    providerKeyNotice.value = copy.value.apiKeyRemovedNotice
  } catch (error) {
    providerKeyError.value = formatUnexpectedError(error)
  } finally {
    providerKeyLoading.value = false
  }
}

function startProviderKeyEdit() {
  providerKeyEditing.value = true
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  clientApiKey.value = ''
}

function cancelProviderKeyEdit() {
  providerKeyEditing.value = false
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  clientApiKey.value = ''
}

function selectAccount(accountId: string) {
  if (selectedAccountId.value === accountId) {
    return
  }
  selectedAccountId.value = accountId
  resetChatState()
  void loadReport()
}

function selectDays(days: number) {
  if (reportDays.value === days) {
    return
  }
  reportDays.value = days
  resetChatState()
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

function formatGoogleCustomerId(customerId: string) {
  const normalized = customerId.replace(/\D/g, '')
  if (normalized.length !== 10) {
    return customerId
  }
  return `${normalized.slice(0, 3)}-${normalized.slice(3, 6)}-${normalized.slice(6)}`
}

function formatGoogleCustomerLabel(customer: GoogleAdsCustomer) {
  const accountKind = customer.is_manager ? copy.value.managerAccount : copy.value.clientAccount
  const accessKind = customer.is_directly_accessible ? copy.value.directAccess : copy.value.viaManager
  return `${accountKind} · ${accessKind} · ${formatGoogleCustomerId(customer.external_customer_id)}`
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
  return creative.image_url || creative.thumbnail_url || ''
}

function creativeTypeLabel(creative: Creative) {
  return (creative.object_type || 'ad').toUpperCase()
}

function creativeTitle(creative: Creative) {
  return creative.name?.trim() || creativeTypeLabel(creative)
}

function creativeStats(creative: Creative) {
  return [
    {
      key: 'spend',
      label: copy.value.creativeMetricLabels.spend,
      value: formatMetricValue('spend', creative.metrics.spend),
      tone: 'blue',
    },
    {
      key: 'impressions',
      label: copy.value.creativeMetricLabels.impressions,
      value: formatCompactNumber(creative.metrics.impressions),
      tone: '',
    },
    {
      key: 'clicks',
      label: copy.value.creativeMetricLabels.clicks,
      value: formatCompactNumber(creative.metrics.clicks),
      tone: '',
    },
    {
      key: 'ctr',
      label: copy.value.creativeMetricLabels.ctr,
      value: formatMetricValue('ctr', creative.metrics.ctr),
      tone: '',
    },
    {
      key: 'results',
      label: resultKindLabel(creative.metrics.result_kind),
      value: formatCompactNumber(creative.metrics.results),
      tone: 'green',
    },
  ]
}

watch(provider, () => {
  customModel.value = ''
  clientApiKey.value = ''
  providerKeyEditing.value = false
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  applyProviderDefaultPreset()
})

watch(useClientCredentials, (enabled) => {
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  chatError.value = ''
  if (!enabled) {
    providerKeyEditing.value = false
    clientApiKey.value = ''
  }
})

watch(
  () => [currentView.value, locale.value, isAuthenticated.value],
  () => {
    updateDocumentTitle()
  },
  { immediate: true },
)

onMounted(() => {
  localStorage.removeItem(LEGACY_STORAGE_LOCALE_KEY)
  applyLocale(locale.value, { persist: false })
  applyProviderDefaultPreset()
  window.addEventListener('popstate', handlePopState)
  void syncView(currentView.value)
})

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)
})

watch(currentView, (view) => {
  void syncView(view)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">{{ copy.brand }}</p>
        <h1>{{ headerTitle }}</h1>
      </div>

      <div class="toolbar">
        <div class="lang-switch" role="tablist" :aria-label="copy.locale">
          <button
            v-for="lang in ['ru', 'kz', 'en']"
            :key="lang"
            type="button"
            class="lang-pill"
            :class="{ active: locale === lang }"
            @click="void syncLocale(lang as Locale)"
          >
            {{ lang.toUpperCase() }}
          </button>
        </div>

        <button
          type="button"
          class="ghost-button"
          :class="{ active: isPolicyView }"
          :disabled="currentView === 'privacy'"
          @click="openPrivacyPolicy"
        >
          {{ copy.privacyPolicy }}
        </button>

        <button v-if="isPolicyView" type="button" class="ghost-button" @click="openAppView">
          {{ copy.backToApp }}
        </button>

        <button v-if="isAuthenticated" type="button" class="ghost-button" @click="logout">
          {{ copy.logout }}
        </button>
      </div>
    </header>

    <main v-if="isPolicyView" class="policy-stage">
      <section class="policy-surface">
        <div class="policy-hero">
          <p class="eyebrow">{{ copy.privacyPolicy }}</p>
          <h2>{{ copy.privacyTitle }}</h2>
          <p class="auth-copy">{{ copy.privacyLead }}</p>

          <div class="policy-meta">
            <span class="policy-chip">{{ copy.privacyUpdatedLabel }}: {{ copy.privacyUpdatedOn }}</span>
            <span class="policy-chip">{{ copy.privacyMetaScopeLabel }}: ads_read</span>
            <a class="ghost-link" :href="`mailto:${PRIVACY_CONTACT_EMAIL}`">{{ PRIVACY_CONTACT_EMAIL }}</a>
            <button type="button" class="ghost-button" @click="openDataDeletion">
              {{ copy.dataDeletionLabel }}
            </button>
          </div>
        </div>

        <div class="policy-grid">
          <section
            v-for="section in policySections"
            :id="section.id"
            :key="section.id"
            class="policy-block"
          >
            <h3>{{ section.title }}</h3>
            <p v-for="paragraph in section.paragraphs ?? []" :key="paragraph">{{ paragraph }}</p>
            <ul v-if="section.bullets?.length" class="policy-list">
              <li v-for="item in section.bullets" :key="item">{{ item }}</li>
            </ul>
          </section>
        </div>
      </section>
    </main>

    <main v-else-if="bootLoading" class="boot-stage">
      <div class="pulse-dot"></div>
      <p>{{ copy.loading }}</p>
    </main>

    <main v-else-if="!isAuthenticated" class="auth-stage">
      <section class="auth-intro">
        <p class="eyebrow">Meta + Google Ads + AI proxy</p>
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
            <strong>Gemini Flash</strong>
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
              <option value="ru">Русский</option>
              <option value="kz">Қазақша</option>
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

        <section class="rail-section">
          <div class="section-head">
            <span>{{ copy.googleAds }}</span>
            <button type="button" class="rail-link" :disabled="googleConnecting" @click="connectGoogle">
              {{ copy.connectGoogle }}
            </button>
          </div>

          <div v-if="googleAccountsLoading" class="empty-note">{{ copy.loading }}</div>
          <div v-else-if="googleAccounts.length === 0" class="empty-note">{{ copy.googleAccountsEmpty }}</div>

          <div v-for="customer in googleAccounts" :key="customer.id" class="account-item account-item-static">
            <span>{{ customer.descriptive_name }}</span>
            <small>{{ formatGoogleCustomerLabel(customer) }}</small>
          </div>
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
          <div class="empty-surface-actions">
            <button type="button" class="primary-button" :disabled="metaConnecting" @click="connectMeta">
              {{ copy.connectMeta }}
            </button>
            <button type="button" class="ghost-button" :disabled="googleConnecting" @click="connectGoogle">
              {{ copy.connectGoogle }}
            </button>
          </div>
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
              <button
                type="button"
                class="ghost-button"
                :disabled="reportLoading"
                @click="loadReport({ forceRefresh: true })"
              >
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
                      :alt="creativeTitle(creative)"
                      class="creative-image"
                      loading="lazy"
                      decoding="async"
                    />
                    <div v-else class="creative-fallback">{{ creativeTypeLabel(creative) }}</div>

                    <div class="creative-copy">
                      <div class="creative-headline">
                        <small class="creative-type">{{ creativeTypeLabel(creative) }}</small>
                        <p :title="creativeTitle(creative)">{{ creativeTitle(creative) }}</p>
                      </div>
                    </div>

                    <div class="creative-stats">
                      <div v-for="item in creativeStats(creative)" :key="item.key" class="cstat">
                        <div class="cstat-l">{{ item.label }}</div>
                        <div class="cstat-v" :class="item.tone">{{ item.value }}</div>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </section>
            <section v-else class="focus-surface">
              <div class="empty-note">{{ copy.emptyCampaigns }}</div>
            </section>
          </template>
        </template>
      </section>

      <aside class="rail rail-right">
        <section class="ai-surface verdict-surface">
          <div class="section-head">
            <div class="verdict-title">
              <span>{{ copy.aiVerdict }}</span>
              <div class="info-tooltip">
                <button
                  type="button"
                  class="info-tooltip-trigger"
                  :aria-label="copy.aiVerdictInfoLabel"
                  aria-describedby="ai-verdict-tooltip"
                >
                  i
                </button>
                <span id="ai-verdict-tooltip" class="info-tooltip-panel" role="tooltip">{{ copy.aiVerdictHint }}</span>
              </div>
            </div>
          </div>
          <p v-if="verdictLoading" class="empty-note">{{ copy.loadingVerdict }}</p>
          <div v-else class="verdict-body">
            <div
              class="verdict-text verdict-summary markdown-body"
              v-html="renderMarkdown(autoVerdictSummary || '—')"
            ></div>
            <button
              v-if="hasAutoVerdictDetails"
              type="button"
              class="ghost-button compact-button verdict-toggle"
              @click="autoVerdictExpanded = !autoVerdictExpanded"
            >
              {{ autoVerdictExpanded ? copy.hideVerdictDetails : copy.showVerdictDetails }}
            </button>
            <div
              v-if="autoVerdictExpanded && autoVerdictDetails"
              class="verdict-text verdict-details markdown-body"
              v-html="renderMarkdown(autoVerdictDetails)"
            ></div>
          </div>
        </section>

        <section class="ai-surface chat-surface">
          <div class="section-head">
            <span>{{ copy.aiChat }}</span>
          </div>
          <p class="surface-note">{{ copy.aiChatHint }}</p>
          <p class="surface-note">{{ copy.chatDefaultModeHint }}</p>

          <div class="chat-stream">
            <article
              v-for="(message, index) in chatMessages"
              :key="index"
              class="chat-bubble markdown-body"
              :class="message.role"
              v-html="renderMarkdown(message.content)"
            ></article>
            <p v-if="chatLoading" class="empty-note">{{ copy.loadingChat }}</p>
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
              :disabled="chatLoading || !canSendChat"
              @click="sendQuestion()"
            >
              {{ copy.send }}
            </button>
          </div>

          <p v-if="chatError" class="message error">{{ chatError }}</p>

          <div class="chat-advanced-toggle">
            <button
              type="button"
              class="ghost-button compact-button"
              @click="useClientCredentials = !useClientCredentials"
            >
              {{ useClientCredentials ? copy.hideOwnApiKey : copy.useOwnApiKey }}
            </button>
          </div>

          <div v-if="useClientCredentials" class="chat-advanced">
            <p class="surface-note">{{ copy.customAiSettingsHint }}</p>

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

            <div class="provider-key-card">
              <div class="provider-key-head">
                <span>{{ copy.apiKey }}</span>
                <div v-if="hasSavedProviderKey && !showProviderKeyInput" class="provider-key-actions">
                  <button type="button" class="ghost-button compact-button" @click="startProviderKeyEdit">
                    {{ copy.replaceApiKey }}
                  </button>
                  <button
                    type="button"
                    class="ghost-button compact-button"
                    :disabled="providerKeyLoading"
                    @click="deleteProviderKey"
                  >
                    {{ copy.removeApiKey }}
                  </button>
                </div>
              </div>

              <p v-if="hasSavedProviderKey && !showProviderKeyInput" class="surface-note">
                {{ copy.savedKeyHint }}
              </p>

              <template v-if="showProviderKeyInput">
                <label class="provider-key-input">
                  <input v-model="clientApiKey" type="password" placeholder="sk-..." />
                </label>
                <div class="provider-key-actions">
                  <button
                    type="button"
                    class="ghost-button compact-button"
                    :disabled="providerKeyLoading || !clientApiKey.trim()"
                    @click="saveProviderKey"
                  >
                    {{ copy.saveApiKey }}
                  </button>
                  <button
                    v-if="hasSavedProviderKey"
                    type="button"
                    class="ghost-button compact-button"
                    :disabled="providerKeyLoading"
                    @click="cancelProviderKeyEdit"
                  >
                    {{ copy.cancel }}
                  </button>
                </div>
              </template>
            </div>

            <p class="surface-note">{{ copy.chatKeyHint }}</p>
            <p v-if="providerKeyNotice" class="message success">{{ providerKeyNotice }}</p>
            <p v-if="providerKeyError" class="message error">{{ providerKeyError }}</p>
          </div>
        </section>
      </aside>
    </main>
  </div>
</template>
