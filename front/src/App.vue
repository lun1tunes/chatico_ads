<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

type Locale = 'ru' | 'kz' | 'en'
type AuthMode = 'login' | 'register'
type AIProvider = 'anthropic' | 'openai' | 'gemini'
type AppView = 'app' | 'privacy' | 'dataDeletion' | 'terms'
type WorkspaceSection = 'overview' | 'campaign' | 'accounts' | 'settings'
type OAuthProvider = 'meta' | 'google_ads' | 'tiktok_ads'
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

interface TikTokAdsAdvertiser {
  id: string
  advertiser_id: string
  name: string
  currency: string | null
  timezone_name: string | null
  status: string | null
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

interface TrendPoint {
  date: string
  spend: number
  results: number
  impressions: number
}

interface DashboardTrend {
  current: TrendPoint[]
  previous: TrendPoint[]
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
  trend?: DashboardTrend
  campaigns: Campaign[]
}

interface SurfaceMetricCard {
  key: MetricKey
  label: string
  value: string
  subtitle: string
  deltaLabel: string
  deltaTone: 'good' | 'warning' | 'neutral'
}

interface TrendChartPointView extends TrendPoint {
  x: number
  spendY: number
  resultsY: number
  label: string
}

interface TrendChartGridLine {
  y: number
  spendLabel: string
  resultsLabel: string
}

interface TrendChartTick {
  x: number
  label: string
}

interface TrendChartModel {
  hasData: boolean
  points: TrendChartPointView[]
  spendLine: string
  spendArea: string
  resultsLine: string
  resultsArea: string
  gridLines: TrendChartGridLine[]
  ticks: TrendChartTick[]
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

interface LegalSection {
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

interface WorkspaceAccountOption {
  provider: OAuthProvider
  id: string
  name: string
  subtitle: string
}

interface WorkspaceProviderOption {
  key: OAuthProvider
  label: string
  subtitle: string
  count: number
  connected: boolean
}

interface WorkspaceRoute {
  section: WorkspaceSection
  campaignId: string
}

interface WorkspaceAccountCard {
  provider: OAuthProvider
  id: string
  name: string
  subtitle: string
  currency: string
  timezone: string
  accent: 'meta' | 'google_ads' | 'tiktok_ads'
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
const STORAGE_TOKEN_KEY = 'chatico_ads.access_token'
const LEGACY_STORAGE_TOKEN_KEY = 'chatico.access_token'
const LEGACY_STORAGE_LOCALE_KEY = 'chatico.locale'
const STORAGE_LOCALE_OVERRIDE_KEY = 'chatico.locale_override'
const DEFAULT_LOCALE: Locale = 'ru'
const CUSTOM_MODEL_OPTION = '__custom__'
const PRIVACY_CONTACT_EMAIL = 'support@chatico.cc'
const PRIVACY_SERVICE_OPERATOR = 'Chatico Ads'
const PRIVACY_SERVICE_URL = trimTrailingSlash(`${window.location.origin}${APP_BASE_PATH}`)
const overviewMetricKeys: MetricKey[] = ['spend', 'results', 'cost_per_result', 'impressions']
const trendChartFrame = {
  width: 760,
  height: 320,
  left: 52,
  right: 52,
  top: 18,
  bottom: 38,
}

function normalizePathname(value: string): string {
  const trimmed = trimTrailingSlash(value.trim())
  return trimmed === '' ? '/' : trimmed
}

function buildRoutePath(segment: string): string {
  const base = trimTrailingSlash(APP_BASE_PATH)
  return normalizePathname(`${base}/${segment}`)
}

const APP_HOME_PATH = normalizePathname(APP_BASE_PATH)
const ACCOUNTS_ROUTE_PATH = buildRoutePath('accounts')
const SETTINGS_ROUTE_PATH = buildRoutePath('settings')
const CAMPAIGNS_ROUTE_PATH = buildRoutePath('campaigns')
const PRIVACY_ROUTE_PATH = buildRoutePath('privacy-policy')
const DATA_DELETION_ROUTE_PATH = buildRoutePath('data-deletion')
const TERMS_ROUTE_PATH = buildRoutePath('terms-of-service')

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
    privacyTitle: 'Как Chatico Ads обрабатывает данные Meta, Google, TikTok и пользователя',
    privacyLead:
      `Эта политика описывает, какие данные собирает приложение Chatico Ads, зачем они используются, кому могут передаваться и как запросить удаление. Официальный адрес сервиса: ${PRIVACY_SERVICE_URL}. Документ опубликован для публичного доступа и соответствует требованиям Meta App Review, Google OAuth / Google API Services User Data Policy (Limited Use) и business onboarding/review для TikTok Ads.`,
    privacyUpdatedLabel: 'Обновлено',
    privacyUpdatedOn: '5 июля 2026',
    privacyMetaScopeLabel: 'Разрешение Meta',
    privacyGoogleScopeLabel: 'Google OAuth scope',
    privacyTikTokScopeLabel: 'TikTok API for Business',
    privacySections: [
      {
        id: 'overview',
        title: '1. Что делает сервис',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} помогает владельцу бизнеса подключить рекламные кабинеты Meta, Google Ads и TikTok Ads и просматривать рекламную статистику в одном интерфейсе.`,
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
          'Google user data через Google Ads API и OAuth scope https://www.googleapis.com/auth/adwords: идентификатор Google-аккаунта и email (из OAuth), OAuth refresh/access tokens, Google Ads customer account IDs, названия, валюта, часовой пояс, метаданные кампаний/объявлений/креативов и метрики эффективности (расход, показы, клики, конверсии и др.)',
          'данные TikTok Ads через TikTok API for Business: OAuth access/refresh tokens, advertiser account IDs, названия, валюта, часовой пояс, статусы, метаданные кампаний/объявлений и read-only метрики эффективности (расход, показы, клики, конверсии и др.)',
          'кешированные снимки отчётов, сформированные из Meta-, Google- и TikTok-данных, хранятся на сервере до истечения срока или удаления',
          'технические данные: IP-адрес, сведения о браузере и запросе, серверные логи — для безопасности, диагностики и предотвращения злоупотреблений',
          'по явному выбору пользователя для AI-функций: текст вопроса, выбранный AI-провайдер, ответ модели; при сохранении — API-ключ провайдера в зашифрованном виде',
        ],
      },
      {
        id: 'data-use',
        title: '3. Зачем мы используем данные',
        bullets: [
          'для регистрации, входа и изоляции данных между пользователями',
          'для подключения Meta, Google Ads и TikTok Ads, загрузки, кеширования и отображения рекламной статистики',
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
        id: 'google-user-data',
        title: '5. Google user data и Google Ads API',
        paragraphs: [
          'Приложение Chatico Ads использует Google OAuth и scope https://www.googleapis.com/auth/adwords для доступа к Google Ads API в режиме только чтения.',
          'Мы используем Google user data исключительно для функций приложения, которые вы запрашиваете: подключение аккаунта, выбор customer account, отображение отчётов и сравнение периодов.',
          'Мы не используем Google user data для таргетированной рекламы, interest-based advertising, ретаргетинга, продажи брокерам данных, оценки кредитоспособности, кредитования или создания баз данных, не связанных с функциональностью приложения.',
          'Мы не используем Google user data для обучения обобщённых AI/ML-моделей.',
          'Мы не продаём Google user data. Передача ограничена subprocessors, необходимыми для хостинга и защиты сервиса (облачная инфраструктура). AI-процессоры получают только агрегированный контекст отчёта при явном запросе AI-функций — не OAuth-токены Google и не полные сырые выгрузки Google Ads.',
          'Google OAuth tokens хранятся на сервере в зашифрованном виде; передача данных — по HTTPS. Доступ ограничен аутентифицированными пользователями и серверной логикой приложения.',
          'Google user data хранится, пока активно подключение и до отключения, отзыва доступа в Google Account, истечения токена или выполнения запроса на удаление. Снимки отчётов удаляются по истечении срока хранения или по запросу.',
          'Чтобы отозвать доступ: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access. Также можно отключить Google в приложении или написать на support@chatico.cc.',
          'Использование Google user data соответствует Google API Services User Data Policy, включая требования Limited Use.',
        ],
      },
      {
        id: 'storage-security',
        title: '6. Хранение, передача и защита данных',
        bullets: [
          'Meta, Google и TikTok OAuth tokens, а также пользовательские API-ключи AI-провайдеров хранятся на сервере в зашифрованном виде',
          'данные не продаются и не передаются третьим лицам для их собственного маркетинга, рекламы или профилирования',
          'для AI-функций мы можем передавать выбранному процессору (например, Google Gemini или Anthropic) только вопрос пользователя и агрегированный контекст отчёта; OAuth-токены Meta/Google/TikTok и полные сырые выгрузки не передаются',
          'отчёты кешируются кратковременно в памяти и могут сохраняться как снимки в базе данных до истечения срока хранения или удаления по запросу',
          'данные хранятся только столько, сколько нужно для работы сервиса, соблюдения закона, срока действия токенов или снимков, либо до выполнения запроса на удаление',
        ],
      },
      {
        id: 'data-deletion',
        title: '7. Как запросить удаление данных',
        paragraphs: [
          'Meta: Settings & Privacy → Settings → Apps and Websites → выберите приложение → Remove.',
          'Google: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access.',
          'TikTok: отключите Chatico Ads в настройках TikTok for Business / TikTok Developer App authorization или через отключение в приложении.',
          `Чтобы удалить данные, сохранённые в ${PRIVACY_SERVICE_OPERATOR}, напишите на ${PRIVACY_CONTACT_EMAIL} с темой "Data deletion request". Укажите email аккаунта сервиса; если известны Meta ad account ID, Google Ads customer ID или TikTok advertiser ID — приложите их.`,
          'Для запросов, инициированных через Meta Platform, приложение также поддерживает автоматический серверный callback удаления данных.',
        ],
        bullets: [
          'мы подтвердим получение запроса',
          'удалим аккаунт сервиса, токены, Meta-, Google- и TikTok-подключения, записи рекламных аккаунтов, снимки отчётов и сохранённые AI-ключи, если закон не требует временно сохранить часть данных',
          'сообщим, когда удаление завершено',
        ],
      },
      {
        id: 'rights',
        title: '8. Права пользователя',
        bullets: [
          'запросить доступ к данным, исправление или удаление',
          'отозвать доступ Meta через настройки Facebook, Google через Google Account или TikTok через настройки авторизации приложения',
          'отключить рекламные интеграции в приложении и запросить удаление данных у нас',
          'не использовать AI-функции и не сохранять свой API-ключ провайдера',
        ],
      },
      {
        id: 'contact',
        title: '9. Контакты и связанные документы',
        paragraphs: [
          `По вопросам конфиденциальности, Meta Platform Data, Google user data, TikTok Ads data и удаления данных: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
          `Условия использования сервиса: ${PRIVACY_SERVICE_URL}/terms-of-service`,
        ],
      },
    ],
  },
  kz: {
    privacyPolicy: 'Құпиялылық саясаты',
    backToApp: 'Қосымшаға оралу',
    dataDeletionLabel: 'Деректерді жою',
    privacyTitle: 'Chatico Ads Meta, Google, TikTok және пайдаланушы деректерін қалай өңдейді',
    privacyLead:
      `Бұл саясат Chatico Ads қосымшасы қандай деректерді жинайтынын, не үшін пайдаланатынын, кімге берілетінін және оларды қалай жоюға болатынын түсіндіреді. Сервистің ресми мекенжайы: ${PRIVACY_SERVICE_URL}. Құжат жария қолдануға жарайды және Meta App Review, Google OAuth / Google API Services User Data Policy (Limited Use) және TikTok Ads business onboarding/review талаптарына сәйкес.`,
    privacyUpdatedLabel: 'Жаңартылды',
    privacyUpdatedOn: '2026 жылғы 5 шілде',
    privacyMetaScopeLabel: 'Meta рұқсаты',
    privacyGoogleScopeLabel: 'Google OAuth scope',
    privacyTikTokScopeLabel: 'TikTok API for Business',
    privacySections: [
      {
        id: 'overview',
        title: '1. Сервис не істейді',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} бизнес иесіне Meta, Google Ads және TikTok Ads жарнама кабинеттерін қосып, жарнама статистикасын бір интерфейсте көруге көмектеседі.`,
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
          'Google Ads API және OAuth scope https://www.googleapis.com/auth/adwords арқылы Google user data: Google аккаунт ID және email, OAuth refresh/access tokens, Google Ads customer account ID-лері, атаулар, валюта, уақыт белдеуі, кампания/жарнама/креатив метадатасы және тиімділік метрикалары (шек, көрсетілім, клик, конверсия және т.б.)',
          'TikTok API for Business арқылы TikTok Ads деректері: OAuth access/refresh tokens, advertiser account ID-лері, атаулар, валюта, уақыт белдеуі, статус, кампания/жарнама метадатасы және read-only тиімділік метрикалары',
          'Meta, Google және TikTok деректерінен құрылған кештеулі есеп снимоктары серверде мерзімі біткенше немесе жойылғанша сақталады',
          'техникалық деректер: IP-мекенжай, браузер/сұрау деректері, сервер логтары — қауіпсіздік, диагностика және теріс пайдалануды болдырмау үшін',
          'AI-функцияларды пайдаланушы таңдағанда: сұрақ мәтіні, таңдалған AI-провайдер, модель жауабы; сақталса — провайдер API-килті шифрланған түрде',
        ],
      },
      {
        id: 'data-use',
        title: '3. Деректер не үшін қолданылады',
        bullets: [
          'тіркелу, кіру және пайдаланушылар арасында деректерді оқшаулау үшін',
          'Meta, Google Ads және TikTok Ads қосу, жарнама статистикасын жүктеу, кэштеу және көрсету үшін',
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
        id: 'google-user-data',
        title: '5. Google user data және Google Ads API',
        paragraphs: [
          'Chatico Ads қосымшасы Google OAuth және scope https://www.googleapis.com/auth/adwords арқылы Google Ads API-ге тек оқу режимінде қол жеткізеді.',
          'Google user data тек сіз сұраған қосымша функциялар үшін қолданылады: аккаунт қосу, customer account таңдау, есептерді көрсету және кезеңдерді салыстыру.',
          'Google user data таргеттелген жарнама, interest-based advertising, ретаргетинг, деректер брокерлеріне сату, несиеге қабілеттілікті бағалау, несие беру немесе қосымша функциясына байланысты емес базалар құру үшін қолданылмайды.',
          'Google user data жалпы AI/ML модельдерін оқыту үшін қолданылмайды.',
          'Google user data сатылмайды. Беру тек сервисті хостингтеу және қорғау үшін қажет subprocessors-мен шектеледі. AI-процессорлар OAuth токендер мен толық шикі Google Ads деректерін емес, тек агрегатталған есеп контекстін алады.',
          'Google OAuth token-дері серверде шифрланған түрде сақталады; деректер HTTPS арқылы беріледі.',
          'Google user data байланыс белсенді болғанша сақталады; Google Account-тан доступ кері алу, қосымшада ажырату немесе жою сұрауы орындалғанша.',
          'Доступты кері алу: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access. Немесе қосымшада Google ажырату немесе support@chatico.cc.',
          'Google user data Google API Services User Data Policy, соның ішінде Limited Use талаптарына сәйкес пайдаланылады.',
        ],
      },
      {
        id: 'storage-security',
        title: '6. Сақтау, беру және қорғау',
        bullets: [
          'Meta, Google және TikTok OAuth token-дері, сондай-ақ пайдаланушы AI API-килттері серверде шифрланған түрде сақталады',
          'деректер сатылмайды және үшінші тараптардың өз маркетинг/жарнама/профильдеу мақсаттарына берілмейді',
          'AI-функциялар үшін таңдалған процессорға тек пайдаланушы сұрағы мен агрегатталған есеп контексті берілуі мүмкін; Meta/Google/TikTok OAuth token-дері мен толық шикі деректер берілмейді',
          'есептер қысқа уақытқа жадта кэштеледі және дерекқорда снимок ретінде мерзімге дейін сақталуы мүмкін',
          'деректер сервис жұмысына, заң талаптарына, токен/снимок мерзіміне немесе жою сұрауына дейін ғана сақталады',
        ],
      },
      {
        id: 'data-deletion',
        title: '7. Деректерді жоюды қалай сұрауға болады',
        paragraphs: [
          'Meta: Settings & Privacy → Settings → Apps and Websites → қолданбаны таңдаңыз → Remove.',
          'Google: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access.',
          `${PRIVACY_SERVICE_OPERATOR} сақтаған деректерді жою үшін ${PRIVACY_CONTACT_EMAIL} адресіне "Data deletion request" тақырыбымен хат жіберіңіз. Сервис email-ін көрсетіңіз; Meta ad account ID, Google Ads customer ID немесе TikTok advertiser ID белгілі болса, қосыңыз.`,
          'Meta Platform арқылы басталған сұраулар үшін қолданба деректерді жоюға арналған автоматты серверлік callback-ты да қолдайды.',
        ],
        bullets: [
          'сұраудың алынғанын растаймыз',
          'сервис аккаунты, токендер, Meta/Google/TikTok байланыстары, жарнама аккаунттары, есеп снимоктары және AI-килттер жойылады; заң уақытша сақтау талап етпесе',
          'жою аяқталған соң хабарлаймыз',
        ],
      },
      {
        id: 'rights',
        title: '8. Пайдаланушы құқықтары',
        bullets: [
          'деректерге қол жеткізуді, түзетуді немесе жоюды сұрау',
          'Facebook баптаулары арқылы Meta доступын, Google Account арқылы Google доступын немесе TikTok авторизация баптаулары арқылы TikTok доступын кері алу',
          'қосымшада интеграцияларды ажырату және бізден деректерді жоюды сұрау',
          'AI-функцияларды қолданбау және провайдер API-килтін сақтамау',
        ],
      },
      {
        id: 'contact',
        title: '9. Байланыс және байланысты құжаттар',
        paragraphs: [
          `Құпиялылық, Meta Platform Data, Google user data, TikTok Ads data және деректерді жою бойынша: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
          `Пайдалану шарттары: ${PRIVACY_SERVICE_URL}/terms-of-service`,
        ],
      },
    ],
  },
  en: {
    privacyPolicy: 'Privacy Policy',
    backToApp: 'Back to App',
    dataDeletionLabel: 'Data Deletion',
    privacyTitle: 'Privacy Policy — Chatico Ads (Meta, Google, and TikTok Ads)',
    privacyLead:
      `This Privacy Policy explains what data the Chatico Ads application collects, why we use it, which third parties may process it, and how you can request deletion. The official production URL is ${PRIVACY_SERVICE_URL}. This document is published for public access and is intended to meet Meta App Review, Google OAuth / Google API Services User Data Policy (Limited Use), and TikTok Ads business onboarding/review requirements.`,
    privacyUpdatedLabel: 'Last updated',
    privacyUpdatedOn: 'July 5, 2026',
    privacyMetaScopeLabel: 'Meta permission',
    privacyGoogleScopeLabel: 'Google OAuth scope',
    privacyTikTokScopeLabel: 'TikTok API for Business',
    privacySections: [
      {
        id: 'overview',
        title: '1. What the service does',
        paragraphs: [
          `${PRIVACY_SERVICE_OPERATOR} helps business owners connect Meta, Google Ads, and TikTok Ads accounts and review advertising performance in one dashboard.`,
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
          'Google user data obtained through the Google Ads API and OAuth scope https://www.googleapis.com/auth/adwords: Google account identifier and email (from OAuth), OAuth refresh/access tokens, Google Ads customer account IDs, names, currency, timezone, campaign/ad/creative metadata, and performance metrics such as spend, impressions, clicks, and conversions',
          'TikTok Ads data obtained through TikTok API for Business: OAuth access/refresh tokens, advertiser account IDs, names, currency, timezone, status, campaign/ad metadata, and read-only performance metrics such as spend, impressions, clicks, and conversions',
          'cached report snapshots derived from Meta, Google, and TikTok data, stored on our servers until they expire or are deleted',
          'technical data collected automatically: IP address, browser and request metadata, and server logs for security, troubleshooting, and abuse prevention',
          'when you choose to use AI features: your question, selected AI provider, model response, and—if you save it—your provider API key in encrypted form',
        ],
      },
      {
        id: 'data-use',
        title: '3. How and why we use data',
        bullets: [
          'to register and authenticate users and keep each customer\'s data isolated',
          'to connect Meta, Google Ads, and TikTok Ads accounts, fetch advertising statistics, cache reports, and display dashboards',
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
        id: 'google-user-data',
        title: '5. Google user data and Google Ads API',
        paragraphs: [
          'The Chatico Ads application uses Google OAuth and the scope https://www.googleapis.com/auth/adwords to access the Google Ads API in read-only mode.',
          'We use Google user data solely to provide app features you request: connecting your account, selecting a customer account, displaying reports, and comparing time periods.',
          'We do not use Google user data for serving targeted ads, interest-based advertising, retargeting, selling to data brokers, determining creditworthiness, lending, or building databases unrelated to app functionality.',
          'We do not use Google user data to train generalized AI or machine learning models.',
          'We do not sell Google user data. Disclosure is limited to subprocessors required to host and secure the service (cloud infrastructure). AI processors receive only aggregated report context when you explicitly use AI features—not Google OAuth tokens or full raw Google Ads exports.',
          'Google OAuth tokens are stored on our servers in encrypted form; data is transmitted over HTTPS. Access is limited to authenticated users and server-side application logic.',
          'Google user data is retained while your connection is active and until you disconnect, revoke access in your Google Account, the token expires, or we complete a valid deletion request. Report snapshots are removed when they expire or upon request.',
          'To revoke access: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access. You may also disconnect Google in the app or email support@chatico.cc.',
          'Our use of Google user data complies with the Google API Services User Data Policy, including Limited Use requirements.',
        ],
      },
      {
        id: 'storage-security',
        title: '6. Storage, sharing, and security',
        bullets: [
          'Meta, Google, and TikTok OAuth tokens and user-provided AI provider API keys are stored on our servers in encrypted form',
          'we do not sell data and do not share it with third parties for their own marketing, advertising, or profiling',
          'for AI features, we may send your question and an aggregated report summary to the processor you select (for example, Google Gemini or Anthropic); we do not send Meta, Google, or TikTok OAuth tokens or full raw platform exports',
          'reports are cached briefly in memory and may also be stored as time-limited snapshots in our database',
          'we retain data only as long as needed to operate the service, comply with law, honor token or snapshot expiry, or until a valid deletion request is completed',
        ],
      },
      {
        id: 'data-deletion',
        title: '7. How to request deletion of your data',
        paragraphs: [
          'Meta: Settings & Privacy → Settings → Apps and Websites → select the app → Remove.',
          'Google: Google Account → Security → Third-party apps with account access → Chatico Ads → Remove access.',
          'TikTok: disconnect Chatico Ads in TikTok for Business / TikTok Developer app authorization settings or inside the app.',
          `To delete data stored by ${PRIVACY_SERVICE_OPERATOR}, email ${PRIVACY_CONTACT_EMAIL} with the subject line "Data deletion request". Include the email address linked to your Chatico Ads account. If you know your Meta ad account ID, Google Ads customer ID, or TikTok advertiser ID, include it as well.`,
          'For deletion requests initiated through Meta Platform, the app also supports an automated server-side data deletion callback.',
        ],
        bullets: [
          'we will confirm receipt of your request',
          'we will delete your service account, tokens, Meta, Google, and TikTok connections, ad account records, report snapshots, and saved AI keys unless we are legally required to retain specific data temporarily',
          'we will notify you when deletion is complete',
        ],
      },
      {
        id: 'rights',
        title: '8. Your choices and rights',
        bullets: [
          'request access to, correction of, or deletion of your data',
          'revoke Meta access through Facebook settings, Google access through your Google Account, or TikTok access through TikTok authorization settings',
          'disconnect advertising integrations in the app and ask us to delete stored data',
          'avoid AI features and choose not to store a provider API key',
        ],
      },
      {
        id: 'contact',
        title: '9. Contact and related documents',
        paragraphs: [
          `For privacy questions, Meta Platform Data, Google user data, TikTok Ads data, or deletion requests, contact ${PRIVACY_CONTACT_EMAIL}. Operator: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
          `Terms of Service: ${PRIVACY_SERVICE_URL}/terms-of-service`,
        ],
      },
    ],
  },
} as const

const termsContent = {
  ru: {
    termsOfService: 'Условия использования',
    termsTitle: 'Условия использования Chatico Ads',
    termsLead:
      `Настоящие Условия регулируют доступ к веб-приложению Chatico Ads (${PRIVACY_SERVICE_URL}). Используя сервис, вы соглашаетесь с этими Условиями и с Политикой приватности.`,
    termsUpdatedLabel: 'Обновлено',
    termsUpdatedOn: '5 июля 2026',
    termsPrivacyLinkLabel: 'Политика приватности',
    termsSections: [
      {
        id: 'agreement',
        title: '1. Принятие условий',
        paragraphs: [
          'Chatico Ads — SaaS-приложение для владельцев бизнеса, которое в режиме только чтения отображает рекламную статистику из подключённых кабинетов Meta, Google Ads и TikTok Ads.',
          `Оператор сервиса: ${PRIVACY_SERVICE_OPERATOR}. Контакт: ${PRIVACY_CONTACT_EMAIL}.`,
          `Политика приватности доступна по адресу ${PRIVACY_SERVICE_URL}/privacy-policy и является неотъемлемой частью этих Условий.`,
        ],
      },
      {
        id: 'account',
        title: '2. Регистрация и аккаунт',
        bullets: [
          'для использования сервиса необходимо создать аккаунт с действительным email и надёжным паролем',
          'вы несёте ответственность за сохранность учётных данных и все действия в вашем аккаунте',
          'вы подтверждаете, что имеете право подключать рекламные кабинеты Meta, Google и TikTok, данные которых отображаются в сервисе',
          'мы можем приостановить или закрыть аккаунт при нарушении Условий, злоупотреблениях или по требованию закона',
        ],
      },
      {
        id: 'service',
        title: '3. Описание сервиса',
        bullets: [
          'сервис предоставляет дашборды, отчёты, сравнение периодов и опциональные AI-функции по вашему запросу',
          'сервис не создаёт, не редактирует и не останавливает рекламные кампании от вашего имени',
          'данные рекламных платформ предоставляются «как есть»; мы не гарантируем их полноту, актуальность или доступность API третьих сторон',
          'функции и интерфейс могут изменяться по мере развития продукта',
        ],
      },
      {
        id: 'third-party',
        title: '4. Интеграции с Meta, Google и TikTok',
        paragraphs: [
          'Подключая Meta, Google Ads или TikTok Ads, вы авторизуете Chatico Ads получать данные в объёме запрошенных OAuth-разрешений (Meta: ads_read; Google: https://www.googleapis.com/auth/adwords; TikTok: read-only advertiser/reporting scopes).',
          'Использование данных Meta, Google и TikTok регулируется также политиками соответствующих платформ и нашей Политикой приватности.',
        ],
        bullets: [
          'вы можете отключить интеграции в приложении или отозвать доступ в настройках Meta, Google или TikTok',
          'мы не несём ответственности за изменения, ограничения или сбои API Meta, Google, TikTok или AI-провайдеров',
        ],
      },
      {
        id: 'ai',
        title: '5. AI-функции',
        bullets: [
          'AI-сводки и чат доступны только по вашему явному запросу',
          'вы можете указать собственный API-ключ выбранного провайдера; ключ хранится в зашифрованном виде',
          'ответы AI носят информационный характер и не являются профессиональной, юридической или финансовой консультацией',
          'вы несёте ответственность за соблюдение условий выбранного AI-провайдера',
        ],
      },
      {
        id: 'acceptable-use',
        title: '6. Допустимое использование',
        bullets: [
          'запрещено нарушать закон, права третьих лиц или условия Meta, Google, TikTok и AI-провайдеров',
          'запрещены попытки взлома, обратной разработки, чрезмерной нагрузки на сервис или доступа к чужим данным',
          'запрещено использовать сервис для перепродажи доступа без нашего письменного согласия',
        ],
      },
      {
        id: 'ip',
        title: '7. Интеллектуальная собственность',
        paragraphs: [
          'Интерфейс, код и бренд Chatico Ads принадлежат оператору сервиса. Данные ваших рекламных кабинетов остаются вашими; мы получаем ограниченную лицензию обрабатывать их для предоставления сервиса.',
        ],
      },
      {
        id: 'disclaimer',
        title: '8. Отказ от гарантий и ограничение ответственности',
        paragraphs: [
          'Сервис предоставляется «как есть» и «по мере доступности». В максимально допустимой законом степени мы отказываемся от подразумеваемых гарантий.',
          `${PRIVACY_SERVICE_OPERATOR} не несёт ответственности за косвенные, incidental или consequential убытки, упущенную выгоду или решения, принятые на основе отчётов или AI-ответов.`,
        ],
      },
      {
        id: 'termination',
        title: '9. Прекращение использования',
        bullets: [
          'вы можете прекратить использование в любой момент и запросить удаление данных',
          'мы можем прекратить или ограничить доступ при нарушении Условий или по операционным причинам с разумным уведомлением, когда это возможно',
        ],
      },
      {
        id: 'changes',
        title: '10. Изменения условий',
        paragraphs: [
          'Мы можем обновлять эти Условия. Актуальная версия публикуется на этой странице с указанием даты обновления. Продолжение использования после публикации изменений означает согласие с обновлённой версией.',
        ],
      },
      {
        id: 'contact',
        title: '11. Контакты',
        paragraphs: [
          `По вопросам Условий использования: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
  kz: {
    termsOfService: 'Пайдалану шарттары',
    termsTitle: 'Chatico Ads пайдалану шарттары',
    termsLead:
      `Бұл Шарттар Chatico Ads (${PRIVACY_SERVICE_URL}) веб-қосымшасына қол жеткізуді реттейді. Сервисті пайдалану арқылы сіз осы Шарттармен және Құпиялылық саясатымен келісесіз.`,
    termsUpdatedLabel: 'Жаңартылды',
    termsUpdatedOn: '2026 жылғы 5 шілде',
    termsPrivacyLinkLabel: 'Құпиялылық саясаты',
    termsSections: [
      {
        id: 'agreement',
        title: '1. Шарттарды қабылдау',
        paragraphs: [
          'Chatico Ads — бизнес иелері үшін Meta, Google Ads және TikTok Ads кабинеттерінен жарнама статистикасын тек оқу режимінде көрсететін SaaS-қосымша.',
          `Сервис операторы: ${PRIVACY_SERVICE_OPERATOR}. Байланыс: ${PRIVACY_CONTACT_EMAIL}.`,
          `Құпиялылық саясаты ${PRIVACY_SERVICE_URL}/privacy-policy мекенжайында жарияланған және осы Шарттардың бөлігі.`,
        ],
      },
      {
        id: 'account',
        title: '2. Тіркелу және аккаунт',
        bullets: [
          'сервисті пайдалану үшін жарамды email және надежді пароль қажет',
          'логин/пароль қауіпсіздігі және аккаунтадағы барлық әрекеттер үшін жауапкершілік сізде',
          'сервисте көрсетілетін Meta, Google және TikTok жарнама кабинеттерін қосуға құқығыңыз бар екенін растайсыз',
          'Шарттар бұзылғанда, теріс пайдалануда немесе заң талабы бойынша аккаунт тоқтатылуы мүмкін',
        ],
      },
      {
        id: 'service',
        title: '3. Сервис сипаттамасы',
        bullets: [
          'дашборд, есеп, кезең салыстыру және сіз сұраған AI-функциялар',
          'қосымша сіздің атынан жарнама кампанияларын жасамайды, өзгертпейді және тоқтатпайды',
          'жарнама платформалары деректері «как есть» беріледі; API-тің толықтығы мен қолжетімділігіне кепілдік берілмейді',
          'функциялар мен интерфейс даму барысында өзгеруі мүмкін',
        ],
      },
      {
        id: 'third-party',
        title: '4. Meta, Google және TikTok интеграциялары',
        paragraphs: [
          'Meta, Google Ads немесе TikTok Ads қосу арқылы Chatico Ads-ке сұралған OAuth рұқсаттары шегінде деректер алуға рұқсат бересіз (Meta: ads_read; Google: https://www.googleapis.com/auth/adwords; TikTok: read-only advertiser/reporting scopes).',
          'Meta, Google және TikTok деректерін пайдалану платформалар саясаттарымен және біздің Құпиялылық саясатымен реттеледі.',
        ],
        bullets: [
          'интеграцияларды қосымшада ажырату немесе Meta, Google немесе TikTok баптауларынан доступ кері алуға болады',
          'Meta, Google, TikTok немесе AI-провайдер API өзгерістері үшін жауапкершілік шектелген',
        ],
      },
      {
        id: 'ai',
        title: '5. AI-функциялар',
        bullets: [
          'AI-қорытынды мен чат тек сіздің нақты сұрауыңызбен',
          'өз AI-провайдер API-килтіңізді сақтауға болады; ол шифрланған түрде сақталады',
          'AI жауаптары ақпараттық сипатта; кәсіби кеңес емес',
          'таңдалған AI-провайдер шарттарын сіз орындайсыз',
        ],
      },
      {
        id: 'acceptable-use',
        title: '6. Рұқсат етілген пайдалану',
        bullets: [
          'заңды, Meta/Google/TikTok/AI шарттарын және үшінші тарап құқықтарын бұзуға болмайды',
          'бұзу, кері инженерия, артық жүктеме немесе басқа пайдаланушы деректеріне қол жеткізуге болмайды',
          'біздің жазарсыз келісімсіз доступты қайта сатуға болмайды',
        ],
      },
      {
        id: 'ip',
        title: '7. Зияткерлік меншік',
        paragraphs: [
          'Chatico Ads интерфейсі, коды және бренді операторға тиесілі. Жарнама кабинеті деректері сіздікі; біз оларды сервис көрсету үшін шектеулі лицензиямен өңдейміз.',
        ],
      },
      {
        id: 'disclaimer',
        title: '8. Кепілдіктерден бас тарту',
        paragraphs: [
          'Сервис «как есть» және «қолжетімділігі бойынша» ұсынылады. Заң рұқсат ететін шектеуде кепілдіктерден бас тартылады.',
          `${PRIVACY_SERVICE_OPERATOR} жанама зиян, жоғалған пайда немесе есеп/AI негізіндегі шешімдер үшін жауап бермейді.`,
        ],
      },
      {
        id: 'termination',
        title: '9. Пайдалануды тоқтату',
        bullets: [
          'кез келген уақытта пайдалануды тоқтатып, деректерді жоюды сұрауға болады',
          'Шарттар бұзылғанда немесе операциялық себептермен доступ шектелуі мүмкін',
        ],
      },
      {
        id: 'changes',
        title: '10. Шарттарды өзгерту',
        paragraphs: [
          'Бұл Шарттар жаңартылуы мүмкін. Актуалды нұсқа осы бетте жарияланады. Өзгерістерден кейін пайдалану — жаңа нұсқаға келісім.',
        ],
      },
      {
        id: 'contact',
        title: '11. Байланыс',
        paragraphs: [
          `Пайдалану шарттары бойынша: ${PRIVACY_CONTACT_EMAIL}. Оператор: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
  en: {
    termsOfService: 'Terms of Service',
    termsTitle: 'Terms of Service — Chatico Ads',
    termsLead:
      `These Terms govern access to the Chatico Ads web application (${PRIVACY_SERVICE_URL}). By using the service, you agree to these Terms and our Privacy Policy.`,
    termsUpdatedLabel: 'Last updated',
    termsUpdatedOn: 'July 5, 2026',
    termsPrivacyLinkLabel: 'Privacy Policy',
    termsSections: [
      {
        id: 'agreement',
        title: '1. Agreement',
        paragraphs: [
          'Chatico Ads is a SaaS application that helps business owners view advertising statistics from connected Meta, Google Ads, and TikTok Ads accounts in read-only mode.',
          `Service operator: ${PRIVACY_SERVICE_OPERATOR}. Contact: ${PRIVACY_CONTACT_EMAIL}.`,
          `Our Privacy Policy is available at ${PRIVACY_SERVICE_URL}/privacy-policy and is incorporated into these Terms.`,
        ],
      },
      {
        id: 'account',
        title: '2. Registration and account',
        bullets: [
          'you must create an account with a valid email address and a strong password',
          'you are responsible for safeguarding your credentials and all activity under your account',
          'you confirm that you have the right to connect the Meta, Google, and TikTok ad accounts whose data is displayed in the service',
          'we may suspend or terminate accounts for violations, abuse, or legal requirements',
        ],
      },
      {
        id: 'service',
        title: '3. Service description',
        bullets: [
          'the service provides dashboards, reports, period comparisons, and optional AI features upon your request',
          'the service does not create, edit, pause, or publish advertising campaigns on your behalf',
          'third-party advertising data is provided as-is; we do not guarantee completeness, timeliness, or API availability',
          'features and the interface may change as the product evolves',
        ],
      },
      {
        id: 'third-party',
        title: '4. Meta, Google, and TikTok integrations',
        paragraphs: [
          'By connecting Meta, Google Ads, or TikTok Ads, you authorize Chatico Ads to receive data within the requested OAuth scopes (Meta: ads_read; Google: https://www.googleapis.com/auth/adwords; TikTok: read-only advertiser/reporting scopes).',
          'Use of Meta, Google, and TikTok data is also subject to those platforms\' policies and our Privacy Policy.',
        ],
        bullets: [
          'you may disconnect integrations in the app or revoke access in Meta, Google, or TikTok settings',
          'we are not liable for changes, limits, or outages of Meta, Google, TikTok, or AI provider APIs',
        ],
      },
      {
        id: 'ai',
        title: '5. AI features',
        bullets: [
          'AI summaries and chat are provided only when you explicitly request them',
          'you may store your own API key for a selected provider; keys are stored encrypted',
          'AI outputs are informational only and are not professional, legal, or financial advice',
          'you are responsible for complying with your chosen AI provider\'s terms',
        ],
      },
      {
        id: 'acceptable-use',
        title: '6. Acceptable use',
        bullets: [
          'you must not violate law, third-party rights, or Meta, Google, TikTok, or AI provider terms',
          'you must not attempt to hack, reverse engineer, overload the service, or access other users\' data',
          'you must not resell access without our written consent',
        ],
      },
      {
        id: 'ip',
        title: '7. Intellectual property',
        paragraphs: [
          'The Chatico Ads interface, code, and brand belong to the service operator. Your ad account data remains yours; we receive a limited license to process it to provide the service.',
        ],
      },
      {
        id: 'disclaimer',
        title: '8. Disclaimer and limitation of liability',
        paragraphs: [
          'The service is provided "as is" and "as available." To the maximum extent permitted by law, we disclaim implied warranties.',
          `${PRIVACY_SERVICE_OPERATOR} is not liable for indirect, incidental, or consequential damages, lost profits, or decisions made based on reports or AI responses.`,
        ],
      },
      {
        id: 'termination',
        title: '9. Termination',
        bullets: [
          'you may stop using the service at any time and request deletion of your data',
          'we may suspend or terminate access for violations or operational reasons, with reasonable notice when feasible',
        ],
      },
      {
        id: 'changes',
        title: '10. Changes to these Terms',
        paragraphs: [
          'We may update these Terms. The current version is published on this page with an updated date. Continued use after changes are posted constitutes acceptance of the revised Terms.',
        ],
      },
      {
        id: 'contact',
        title: '11. Contact',
        paragraphs: [
          `For questions about these Terms: ${PRIVACY_CONTACT_EMAIL}. Operator: ${PRIVACY_SERVICE_OPERATOR} (${PRIVACY_SERVICE_URL}).`,
        ],
      },
    ],
  },
} as const

const translations = {
  ru: {
    ...privacyContent.ru,
    ...termsContent.ru,
    brand: 'Chatico Ads',
    authLead: 'Единая панель рекламы для владельца бизнеса: Meta, Google и TikTok.',
    authTitle: 'Подключайте кабинеты Meta, Google и TikTok — читайте рекламу простым языком.',
    authBody:
      'Сервис хранит доступы на сервере, собирает отчёты через API рекламных платформ и показывает AI-вывод без ручных токенов в браузере.',
    authFeaturePlatforms: 'Рекламные платформы',
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
    disconnectMeta: 'Отвязать Meta',
    disconnectMetaConfirm: 'Это удалит все Meta-подключения, кабинеты и сохранённые отчёты из вашего аккаунта. Продолжить?',
    metaDisconnectSuccess: 'Meta-данные удалены из аккаунта.',
    connectGoogle: 'Подключить Google Ads',
    disconnectGoogle: 'Отвязать Google Ads',
    disconnectGoogleConfirm: 'Это удалит подключение Google Ads и связанные аккаунты из вашего профиля. Продолжить?',
    googleDisconnectSuccess: 'Google Ads данные удалены из аккаунта.',
    connectTikTok: 'Подключить TikTok Ads',
    disconnectTikTok: 'Отвязать TikTok Ads',
    disconnectTikTokConfirm: 'Это удалит подключение TikTok Ads и связанные рекламные аккаунты из вашего профиля. Продолжить?',
    tiktokDisconnectSuccess: 'TikTok Ads данные удалены из аккаунта.',
    accounts: 'Кабинеты',
    googleAds: 'Google Ads',
    tiktokAds: 'TikTok Ads',
    googleAccountsEmpty: 'Google Ads пока не подключён.',
    tiktokAccountsEmpty: 'TikTok Ads пока не подключён.',
    directAccess: 'Прямой доступ',
    viaManager: 'Через MCC',
    managerAccount: 'MCC',
    clientAccount: 'Клиент',
    googleManagerNoReports: 'Метрики недоступны — выберите клиентский аккаунт',
    campaigns: 'Кампании',
    days: 'Период',
    dayOptions: { 7: '7 дней', 30: '30 дней', 90: '90 дней' },
    noAccountsTitle: 'Подключите Meta, Google Ads или TikTok Ads',
    noAccountsBody:
      'После OAuth подключённые кабинеты появятся слева, а отчёт и AI-анализ загрузятся через серверный прокси.',
    sidebarOverview: 'Обзор аккаунта',
    sidebarAccounts: 'Аккаунты',
    sidebarSettings: 'Настройки',
    overviewAccount: 'Обзор аккаунта',
    overviewLead: 'Главные показатели рекламы простым языком.',
    accountSwitcherLabel: 'Рекламный кабинет',
    accountSwitcherEmpty: 'Нет кабинета',
    accountSwitcherHint: 'Выберите кабинет для текущей платформы.',
    yourAccounts: 'Ваши кабинеты',
    platforms: 'Рекламный инструмент',
    manageConnections: 'Управление подключениями',
    aiConsultant: 'ИИ-консультант',
    aiConsultantOnline: 'Chatico AI · на связи',
    askAi: 'Спросить AI',
    refreshData: 'Обновить отчёт',
    logout: 'Выйти',
    accountsPageTitle: 'Рекламные кабинеты',
    accountsPageLead: 'Управляйте подключёнными кабинетами Meta, Google Ads и TikTok Ads из одного места.',
    accountsPageEmptyTitle: 'Подключённых кабинетов пока нет',
    accountsPageEmptyBody: 'Подключите хотя бы одну рекламную платформу, чтобы переключаться между кабинетами и получать отчёты.',
    accountsPageSelect: 'Сделать активным',
    accountsPageSelected: 'Сейчас выбран',
    accountsPageConnected: 'Подключено кабинетов',
    accountCardId: 'Идентификатор',
    accountCardCurrency: 'Валюта',
    accountCardTimezone: 'Часовой пояс',
    accountCardConnected: 'Подключено',
    settingsPageTitle: 'Настройки',
    settingsPageLead: 'Язык интерфейса, AI-провайдер и параметры аккаунта.',
    settingsProfileTitle: 'Профиль',
    settingsProfileLead: 'Данные текущей сессии и быстрые действия.',
    settingsLanguageTitle: 'Язык интерфейса',
    settingsLanguageLead: 'Меняет интерфейс и язык AI-резюме для текущего аккаунта.',
    settingsAiTitle: 'AI-настройки',
    settingsAiLead: 'Выберите провайдера, модель и режим использования своего ключа.',
    settingsLegalTitle: 'Юридическая информация',
    settingsLegalLead: 'Быстрые ссылки на политику конфиденциальности и условия сервиса.',
    settingsSavedKey: 'Ключ сохранён на сервере',
    settingsNoSavedKey: 'Сохранённого ключа нет',
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
    loadingReport: 'Собираем отчёт...',
    loadingVerdict: 'Готовим ИИ-анализ...',
    loadingChat: 'Готовим ответ...',
    emptyCampaigns: 'Кампании не найдены для выбранного периода.',
    emptyCreatives: 'По этой кампании нет доступных объявлений или превью.',
    oauthSuccess: 'Meta успешно подключена. Данные кабинета уже доступны.',
    oauthError: 'Подключение Meta завершилось ошибкой.',
    googleOauthSuccess: 'Google Ads успешно подключён. Аккаунты синхронизированы.',
    googleOauthError: 'Подключение Google Ads завершилось ошибкой.',
    tiktokOauthSuccess: 'TikTok Ads успешно подключён. Рекламные аккаунты синхронизированы.',
    tiktokOauthError: 'Подключение TikTok Ads завершилось ошибкой.',
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
    resultKinds: { messages: 'Сообщения', leads: 'Лиды', result: 'Результаты', conversions: 'Конверсии' },
    metricCopy: {
      spend: ['Расход', 'Сколько потрачено за период.'],
      reach: ['Охват', 'Сколько людей увидели рекламу.'],
      impressions: ['Показы', 'Общее число показов.'],
      clicks: ['Клики', 'Переходы по объявлениям.'],
      ctr: ['CTR', 'Доля кликов от показов.'],
      cpm: ['CPM', 'Стоимость 1000 показов.'],
      cpc: ['CPC', 'Средняя цена клика.'],
      results: ['Результаты', 'Основная целевая конверсия платформы.'],
      cost_per_result: ['Цена результата', 'Сколько стоит одна целевая конверсия.'],
    },
    metricTrendGood: 'Динамика улучшилась',
    metricTrendWarning: 'Требует внимания',
    metricTrendNeutral: 'Без резких изменений',
    trendTitle: 'Расходы и результаты по дням',
    trendLead: 'Динамика за выбранный период',
    trendEmpty: 'Подневная динамика появится после следующего обновления отчёта.',
    campaignMetricsTitle: 'Показатели кампании',
    campaignCreativesTitle: 'Объявления и креативы',
  },
  kz: {
    ...privacyContent.kz,
    ...termsContent.kz,
    brand: 'Chatico Ads',
    authLead: 'Шағын бизнес иесі үшін Meta, Google және TikTok Ads панелі.',
    authTitle: 'Meta, Google және TikTok кабинеттерін қосып, жарнаманы түсінікті тілде бақылаңыз.',
    authBody:
      'Сервис рұқсаттарды серверде сақтайды, жарнама платформалары API арқылы есепті өзі жинайды және браузерге токен шығармай AI-қорытынды береді.',
    authFeaturePlatforms: 'Жарнама платформалары',
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
    disconnectMeta: 'Meta-ны ажырату',
    disconnectMetaConfirm: 'Бұл сіздің аккаунтыңыздан барлық Meta байланыстарын, кабинеттерін және сақталған есептерін жояды. Жалғастырасыз ба?',
    metaDisconnectSuccess: 'Meta деректері аккаунттан өшірілді.',
    connectGoogle: 'Google Ads қосу',
    disconnectGoogle: 'Google Ads ажырату',
    disconnectGoogleConfirm: 'Бұл Google Ads байланысын және қатысты аккаунттарды өшіреді. Жалғастырасыз ба?',
    googleDisconnectSuccess: 'Google Ads деректері аккаунттан өшірілді.',
    connectTikTok: 'TikTok Ads қосу',
    disconnectTikTok: 'TikTok Ads ажырату',
    disconnectTikTokConfirm: 'Бұл TikTok Ads байланысын және қатысты жарнама аккаунттарын өшіреді. Жалғастырасыз ба?',
    tiktokDisconnectSuccess: 'TikTok Ads деректері аккаунттан өшірілді.',
    accounts: 'Кабинеттер',
    googleAds: 'Google Ads',
    tiktokAds: 'TikTok Ads',
    googleAccountsEmpty: 'Google Ads әлі қосылмаған.',
    tiktokAccountsEmpty: 'TikTok Ads әлі қосылмаған.',
    directAccess: 'Тікелей қолжетім',
    viaManager: 'MCC арқылы',
    managerAccount: 'MCC',
    clientAccount: 'Клиент',
    googleManagerNoReports: 'Метрикалар қолжетімсіз — клиенттік аккаунтты таңдаңыз',
    campaigns: 'Кампаниялар',
    days: 'Кезең',
    dayOptions: { 7: '7 күн', 30: '30 күн', 90: '90 күн' },
    noAccountsTitle: 'Meta, Google Ads немесе TikTok Ads қосыңыз',
    noAccountsBody:
      'OAuth аяқталған соң қосылған кабинеттер сол жақта көрінеді, ал есеп пен AI-талдау серверлік прокси арқылы жүктеледі.',
    sidebarOverview: 'Аккаунт шолуы',
    sidebarAccounts: 'Аккаунттар',
    sidebarSettings: 'Баптаулар',
    overviewAccount: 'Аккаунт шолуы',
    overviewLead: 'Жарнаманың басты көрсеткіштері қарапайым тілмен.',
    accountSwitcherLabel: 'Жарнама кабинеті',
    accountSwitcherEmpty: 'Кабинет жоқ',
    accountSwitcherHint: 'Ағымдағы платформа үшін кабинетті таңдаңыз.',
    yourAccounts: 'Сіздің кабинеттеріңіз',
    platforms: 'Жарнама құралы',
    manageConnections: 'Байланыстарды басқару',
    aiConsultant: 'AI-кеңесші',
    aiConsultantOnline: 'Chatico AI · байланыста',
    askAi: 'AI сұрау',
    refreshData: 'Есепті жаңарту',
    logout: 'Шығу',
    accountsPageTitle: 'Жарнама кабинеттері',
    accountsPageLead: 'Meta, Google Ads және TikTok Ads кабинеттерін бір жерден басқарыңыз.',
    accountsPageEmptyTitle: 'Қосылған кабинет әлі жоқ',
    accountsPageEmptyBody: 'Кабинеттер арасында ауысу және есеп алу үшін кемінде бір жарнама платформасын қосыңыз.',
    accountsPageSelect: 'Белсенді ету',
    accountsPageSelected: 'Қазір таңдалған',
    accountsPageConnected: 'Қосылған кабинет саны',
    accountCardId: 'Идентификатор',
    accountCardCurrency: 'Валюта',
    accountCardTimezone: 'Уақыт белдеуі',
    accountCardConnected: 'Қосылған',
    settingsPageTitle: 'Баптаулар',
    settingsPageLead: 'Интерфейс тілі, AI-провайдер және аккаунт параметрлері.',
    settingsProfileTitle: 'Профиль',
    settingsProfileLead: 'Ағымдағы сессия деректері және жылдам әрекеттер.',
    settingsLanguageTitle: 'Интерфейс тілі',
    settingsLanguageLead: 'Интерфейс пен AI-қорытынды тілін ағымдағы аккаунт үшін өзгертеді.',
    settingsAiTitle: 'AI баптаулары',
    settingsAiLead: 'Провайдерді, модельді және өз кілтіңізді пайдалану режимін таңдаңыз.',
    settingsLegalTitle: 'Заңдық ақпарат',
    settingsLegalLead: 'Құпиялылық саясаты мен сервис шарттарына жылдам сілтемелер.',
    settingsSavedKey: 'Кілт серверде сақталған',
    settingsNoSavedKey: 'Сақталған кілт жоқ',
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
    loadingReport: 'Есеп жиналып жатыр...',
    loadingVerdict: 'AI талдау дайындалып жатыр...',
    loadingChat: 'Жауап дайындалып жатыр...',
    emptyCampaigns: 'Таңдалған кезең бойынша кампания табылмады.',
    emptyCreatives: 'Бұл кампания үшін жарнамалар немесе превьюлар табылмады.',
    oauthSuccess: 'Meta сәтті қосылды. Кабинет деректері дайын.',
    oauthError: 'Meta қосу кезінде қате болды.',
    googleOauthSuccess: 'Google Ads сәтті қосылды. Аккаунттар синхрондалды.',
    googleOauthError: 'Google Ads қосу кезінде қате болды.',
    tiktokOauthSuccess: 'TikTok Ads сәтті қосылды. Жарнама аккаунттары синхрондалды.',
    tiktokOauthError: 'TikTok Ads қосу кезінде қате болды.',
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
    resultKinds: { messages: 'Хабарламалар', leads: 'Лидтер', result: 'Нәтижелер', conversions: 'Конверсиялар' },
    metricCopy: {
      spend: ['Шығын', 'Кезеңдегі жалпы шығын.'],
      reach: ['Қамту', 'Жарнаманы көрген адамдар саны.'],
      impressions: ['Көрсетілім', 'Барлық көрсетілім саны.'],
      clicks: ['Клик', 'Жарнамаға жасалған өтулер.'],
      ctr: ['CTR', 'Көрсетілімнен клик үлесі.'],
      cpm: ['CPM', '1000 көрсетілім құны.'],
      cpc: ['CPC', 'Бір кликтың орташа бағасы.'],
      results: ['Нәтижелер', 'Платформа анықтаған негізгі конверсия.'],
      cost_per_result: ['Нәтиже құны', 'Бір негізгі конверсия бағасы.'],
    },
    metricTrendGood: 'Динамика жақсарды',
    metricTrendWarning: 'Назар қажет',
    metricTrendNeutral: 'Айқын өзгеріс жоқ',
    trendTitle: 'Күндер бойынша шығын мен нәтиже',
    trendLead: 'Таңдалған кезеңдегі динамика',
    trendEmpty: 'Күндік динамика есеп келесі рет жаңарғанда көрінеді.',
    campaignMetricsTitle: 'Кампания көрсеткіштері',
    campaignCreativesTitle: 'Жарнамалар мен креативтер',
  },
  en: {
    ...privacyContent.en,
    ...termsContent.en,
    brand: 'Chatico Ads',
    authLead: 'One ad analytics workspace for small business owners: Meta, Google, and TikTok.',
    authTitle: 'Connect Meta, Google, and TikTok ad accounts and read performance in plain language.',
    authBody:
      'The app keeps access on the server, builds reports through Meta, Google Ads, and TikTok APIs, and adds AI commentary without exposing platform tokens in the browser.',
    authFeaturePlatforms: 'Ad platforms',
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
    disconnectMeta: 'Disconnect Meta',
    disconnectMetaConfirm: 'This will remove all Meta connections, ad accounts, and saved reports from your account. Continue?',
    metaDisconnectSuccess: 'Meta data has been removed from your account.',
    connectGoogle: 'Connect Google Ads',
    disconnectGoogle: 'Disconnect Google Ads',
    disconnectGoogleConfirm: 'This will remove the Google Ads connection and synced accounts from your profile. Continue?',
    googleDisconnectSuccess: 'Google Ads data has been removed from your account.',
    connectTikTok: 'Connect TikTok Ads',
    disconnectTikTok: 'Disconnect TikTok Ads',
    disconnectTikTokConfirm: 'This will remove the TikTok Ads connection and synced advertiser accounts from your profile. Continue?',
    tiktokDisconnectSuccess: 'TikTok Ads data has been removed from your account.',
    accounts: 'Accounts',
    googleAds: 'Google Ads',
    tiktokAds: 'TikTok Ads',
    googleAccountsEmpty: 'Google Ads is not connected yet.',
    tiktokAccountsEmpty: 'TikTok Ads is not connected yet.',
    directAccess: 'Direct access',
    viaManager: 'Via MCC',
    managerAccount: 'MCC',
    clientAccount: 'Client',
    googleManagerNoReports: 'Metrics unavailable — select a client account',
    campaigns: 'Campaigns',
    days: 'Range',
    dayOptions: { 7: '7 days', 30: '30 days', 90: '90 days' },
    noAccountsTitle: 'Connect Meta, Google Ads, or TikTok Ads',
    noAccountsBody:
      'Start either OAuth flow. After approval, the connected accounts appear on the left and the dashboard plus AI analysis load through the backend proxy.',
    sidebarOverview: 'Account overview',
    sidebarAccounts: 'Accounts',
    sidebarSettings: 'Settings',
    overviewAccount: 'Account overview',
    overviewLead: 'The main ad performance numbers in plain language.',
    accountSwitcherLabel: 'Ad account',
    accountSwitcherEmpty: 'No account',
    accountSwitcherHint: 'Choose an account for the current platform.',
    yourAccounts: 'Your accounts',
    platforms: 'Ad platform',
    manageConnections: 'Manage connections',
    aiConsultant: 'AI consultant',
    aiConsultantOnline: 'Chatico AI · online',
    askAi: 'Ask AI',
    refreshData: 'Refresh report',
    logout: 'Logout',
    accountsPageTitle: 'Ad accounts',
    accountsPageLead: 'Manage connected Meta, Google Ads, and TikTok Ads workspaces from one place.',
    accountsPageEmptyTitle: 'No connected ad accounts yet',
    accountsPageEmptyBody: 'Connect at least one ad platform to switch accounts and load reports.',
    accountsPageSelect: 'Make active',
    accountsPageSelected: 'Currently selected',
    accountsPageConnected: 'Connected accounts',
    accountCardId: 'ID',
    accountCardCurrency: 'Currency',
    accountCardTimezone: 'Timezone',
    accountCardConnected: 'Connected',
    settingsPageTitle: 'Settings',
    settingsPageLead: 'Interface language, AI provider, and account preferences.',
    settingsProfileTitle: 'Profile',
    settingsProfileLead: 'Current session details and quick actions.',
    settingsLanguageTitle: 'Interface language',
    settingsLanguageLead: 'Changes the interface and AI summary language for the current account.',
    settingsAiTitle: 'AI settings',
    settingsAiLead: 'Choose the provider, model, and whether to use your own API key.',
    settingsLegalTitle: 'Legal',
    settingsLegalLead: 'Quick links to the privacy policy and service terms.',
    settingsSavedKey: 'A key is saved on the server',
    settingsNoSavedKey: 'No saved key',
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
    loadingReport: 'Building report...',
    loadingVerdict: 'Preparing AI analysis...',
    loadingChat: 'Preparing the answer...',
    emptyCampaigns: 'No campaigns were returned for this period.',
    emptyCreatives: 'No ads or previews were returned for this campaign.',
    oauthSuccess: 'Meta connected successfully. Account data is ready.',
    oauthError: 'Meta connection failed.',
    googleOauthSuccess: 'Google Ads connected successfully. Accounts are synced.',
    googleOauthError: 'Google Ads connection failed.',
    tiktokOauthSuccess: 'TikTok Ads connected successfully. Advertiser accounts are synced.',
    tiktokOauthError: 'TikTok Ads connection failed.',
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
    resultKinds: { messages: 'Messages', leads: 'Leads', result: 'Results', conversions: 'Conversions' },
    metricCopy: {
      spend: ['Spend', 'Total spend for the selected period.'],
      reach: ['Reach', 'How many people saw the ads.'],
      impressions: ['Impressions', 'Total ad views.'],
      clicks: ['Clicks', 'Ad clicks across campaigns.'],
      ctr: ['CTR', 'Click-through rate from impressions.'],
      cpm: ['CPM', 'Cost per thousand impressions.'],
      cpc: ['CPC', 'Average cost per click.'],
      results: ['Results', 'Primary platform conversion result.'],
      cost_per_result: ['Cost per result', 'Average cost of one target result.'],
    },
    metricTrendGood: 'Momentum improved',
    metricTrendWarning: 'Needs attention',
    metricTrendNeutral: 'No sharp changes',
    trendTitle: 'Spend and results by day',
    trendLead: 'Trend for the selected period',
    trendEmpty: 'Daily trend will appear after the next report refresh.',
    campaignMetricsTitle: 'Campaign metrics',
    campaignCreativesTitle: 'Ads and creatives',
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

function readStoredAccessToken(): string {
  const currentToken = localStorage.getItem(STORAGE_TOKEN_KEY)
  if (currentToken) {
    return currentToken
  }

  const legacyToken = localStorage.getItem(LEGACY_STORAGE_TOKEN_KEY)
  if (!legacyToken) {
    return ''
  }

  localStorage.setItem(STORAGE_TOKEN_KEY, legacyToken)
  localStorage.removeItem(LEGACY_STORAGE_TOKEN_KEY)
  return legacyToken
}

const initialWorkspaceRoute = resolveWorkspaceRoute(window.location.pathname)
const authMode = ref<AuthMode>('login')
const locale = ref<Locale>(resolveInitialLocale())
const registerLocale = ref<Locale>(locale.value)
const accessToken = ref(readStoredAccessToken())
const user = ref<User | null>(null)
const currentView = ref<AppView>(resolveCurrentView(window.location.pathname))
const oauthStatus = ref<OAuthStatus | null>(null)
const authForm = ref({ email: '', password: '' })
const authError = ref('')
const pageError = ref('')
const pageNotice = ref('')
const authLoading = ref(false)
const bootLoading = ref(true)
const metaConnecting = ref(false)
const metaDisconnecting = ref(false)
const googleConnecting = ref(false)
const googleDisconnecting = ref(false)
const tiktokConnecting = ref(false)
const tiktokDisconnecting = ref(false)
const accountsLoading = ref(false)
const googleAccountsLoading = ref(false)
const tiktokAccountsLoading = ref(false)
const reportLoading = ref(false)
const verdictLoading = ref(false)
const chatLoading = ref(false)
const reportDays = ref(30)
const accounts = ref<MetaAccount[]>([])
const googleAccounts = ref<GoogleAdsCustomer[]>([])
const tiktokAccounts = ref<TikTokAdsAdvertiser[]>([])
const selectedProvider = ref<OAuthProvider>('meta')
const selectedAccountId = ref('')
const report = ref<DashboardReport | null>(null)
const workspaceSection = ref<WorkspaceSection>(initialWorkspaceRoute.section)
const selectedCampaignId = ref(initialWorkspaceRoute.campaignId)
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
const accountSwitcherOpen = ref(false)
const platformMenuOpen = ref(false)
const connectModalOpen = ref(false)
const connectModalProvider = ref<OAuthProvider | null>(null)
const sidebarCollapsed = ref(false)
const campaignsExpanded = ref(true)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)
const aiPanelOpen = ref(typeof window !== 'undefined' ? window.innerWidth >= 1280 : true)
const accountSwitcherRef = ref<HTMLElement | null>(null)
const platformMenuRef = ref<HTMLElement | null>(null)
const localeUpdateRequestId = ref(0)
const reportContextKey = ref('')
const customModel = ref('')
const selectedModelPreset = ref(
  fallbackProviderCatalog.find((providerOption) => providerOption.key === provider.value)?.default_model ?? '',
)
const appViewInitialized = ref(false)
const AUTO_VERDICT_PREVIEW_BLOCKS = 2

const copy = computed(() => translations[locale.value])
const isAuthenticated = computed(() => user.value !== null)
const isPolicyView = computed(() => currentView.value === 'privacy' || currentView.value === 'dataDeletion')
const isTermsView = computed(() => currentView.value === 'terms')
const isLegalView = computed(() => isPolicyView.value || isTermsView.value)
const isCampaignSection = computed(() => workspaceSection.value === 'campaign')
const isAccountsSection = computed(() => workspaceSection.value === 'accounts')
const isSettingsSection = computed(() => workspaceSection.value === 'settings')
const isAiOverlay = computed(() => viewportWidth.value < 1280)
const workspaceGridStyle = computed(() => ({
  '--sidebar-width': sidebarCollapsed.value ? '80px' : '288px',
}))
const headerTitle = computed(() => {
  if (isTermsView.value) {
    return copy.value.termsOfService
  }
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
const autoVerdictBlocks = computed(() => splitAutoVerdictBlocks(autoVerdict.value))
const visibleAutoVerdictBlocks = computed(() => {
  if (autoVerdictExpanded.value) {
    return autoVerdictBlocks.value
  }
  return autoVerdictBlocks.value.slice(0, AUTO_VERDICT_PREVIEW_BLOCKS)
})
const hasCollapsedAutoVerdict = computed(() => autoVerdictBlocks.value.length > AUTO_VERDICT_PREVIEW_BLOCKS)
const hasAnyConnectedAccounts = computed(
  () => accounts.value.length > 0 || googleAccounts.value.length > 0 || tiktokAccounts.value.length > 0,
)
const reportableGoogleAccounts = computed(() => googleAccounts.value.filter((customer) => isGoogleReportableCustomer(customer)))
const selectedMetaAccount = computed(() => {
  return accounts.value.find((account) => account.external_id === selectedAccountId.value) ?? null
})
const selectedGoogleAccount = computed(() => {
  return googleAccounts.value.find((customer) => customer.external_customer_id === selectedAccountId.value) ?? null
})
const selectedTikTokAccount = computed(() => {
  return tiktokAccounts.value.find((advertiser) => advertiser.advertiser_id === selectedAccountId.value) ?? null
})
const selectedAccount = computed(() => {
  if (selectedProvider.value === 'google_ads') {
    const customer = selectedGoogleAccount.value
    if (!customer) {
      return null
    }
    return {
      id: customer.id,
      account_id: customer.external_customer_id,
      name: customer.descriptive_name,
      currency: customer.currency_code,
      timezone_name: customer.time_zone,
    }
  }

  if (selectedProvider.value === 'tiktok_ads') {
    const advertiser = selectedTikTokAccount.value
    if (!advertiser) {
      return null
    }
    return {
      id: advertiser.id,
      account_id: advertiser.advertiser_id,
      name: advertiser.name,
      currency: advertiser.currency,
      timezone_name: advertiser.timezone_name,
    }
  }

  const account = selectedMetaAccount.value
  if (!account) {
    return null
  }

  return {
    id: account.id,
    account_id: account.account_id,
    name: account.name,
    currency: account.currency,
    timezone_name: account.timezone_name,
  }
})
const selectedProviderLabel = computed(() => {
  if (selectedProvider.value === 'google_ads') {
    return copy.value.googleAds
  }
  if (selectedProvider.value === 'tiktok_ads') {
    return copy.value.tiktokAds
  }
  return 'Meta'
})
const selectedCampaign = computed(() => {
  const campaigns = report.value?.campaigns ?? []
  return campaigns.find((campaign) => campaign.id === selectedCampaignId.value) ?? null
})
const workspaceMode = computed<WorkspaceSection>(() => {
  if (isAccountsSection.value) {
    return 'accounts'
  }
  if (isSettingsSection.value) {
    return 'settings'
  }
  if (isCampaignSection.value && selectedCampaign.value) {
    return 'campaign'
  }
  return 'overview'
})
const providerOptions = computed<readonly WorkspaceProviderOption[]>(() => [
  {
    key: 'meta',
    label: 'Meta Ads',
    subtitle: 'Facebook / Instagram',
    count: accounts.value.length,
    connected: accounts.value.length > 0,
  },
  {
    key: 'google_ads',
    label: copy.value.googleAds,
    subtitle: 'Google Search / Display',
    count: reportableGoogleAccounts.value.length,
    connected: reportableGoogleAccounts.value.length > 0,
  },
  {
    key: 'tiktok_ads',
    label: copy.value.tiktokAds,
    subtitle: 'TikTok Ads Manager',
    count: tiktokAccounts.value.length,
    connected: tiktokAccounts.value.length > 0,
  },
])
const currentProviderOption = computed(() => {
  return providerOptions.value.find((providerOption) => providerOption.key === selectedProvider.value) ?? providerOptions.value[0]
})
const connectModalProviders = computed(() => {
  if (connectModalProvider.value === null) {
    return providerOptions.value
  }
  return providerOptions.value.filter((providerOption) => providerOption.key === connectModalProvider.value)
})
const currentProviderAccounts = computed<readonly WorkspaceAccountOption[]>(() => {
  if (selectedProvider.value === 'google_ads') {
    return reportableGoogleAccounts.value.map((customer) => ({
      provider: 'google_ads',
      id: customer.external_customer_id,
      name: customer.descriptive_name,
      subtitle: formatGoogleCustomerLabel(customer),
    }))
  }
  if (selectedProvider.value === 'tiktok_ads') {
    return tiktokAccounts.value.map((advertiser) => ({
      provider: 'tiktok_ads',
      id: advertiser.advertiser_id,
      name: advertiser.name,
      subtitle: formatTikTokAdvertiserLabel(advertiser),
    }))
  }
  return accounts.value.map((account) => ({
    provider: 'meta',
    id: account.external_id,
    name: account.name,
    subtitle: account.account_id,
  }))
})
const currentProviderHasAccounts = computed(() => currentProviderAccounts.value.length > 0)
const accountSwitcherLabel = computed(() => selectedAccount.value?.name || copy.value.accountSwitcherEmpty)
const accountSwitcherSubtitle = computed(() => {
  if (selectedProvider.value === 'google_ads') {
    return selectedGoogleAccount.value ? formatGoogleCustomerLabel(selectedGoogleAccount.value) : copy.value.accountSwitcherHint
  }
  if (selectedProvider.value === 'tiktok_ads') {
    return selectedTikTokAccount.value ? formatTikTokAdvertiserLabel(selectedTikTokAccount.value) : copy.value.accountSwitcherHint
  }
  return selectedMetaAccount.value?.account_id || copy.value.accountSwitcherHint
})
const currentProviderEmptyMessage = computed(() => {
  if (selectedProvider.value === 'google_ads') {
    return copy.value.googleAccountsEmpty
  }
  if (selectedProvider.value === 'tiktok_ads') {
    return copy.value.tiktokAccountsEmpty
  }
  return copy.value.noAccountsBody
})
const overviewMetrics = computed<SurfaceMetricCard[]>(() => {
  if (!report.value) {
    return []
  }
  return buildSurfaceMetricCards(report.value.summary.metrics, report.value.summary.primary_result_kind)
})
const campaignSummaryMetrics = computed<SurfaceMetricCard[]>(() => {
  if (!selectedCampaign.value) {
    return []
  }
  return buildSurfaceMetricCards(selectedCampaign.value.metrics, selectedCampaign.value.primary_result_kind)
})
const overviewTrendPoints = computed<TrendPoint[]>(() => report.value?.trend?.current ?? [])
const overviewTrendResultLabel = computed(() => {
  if (!report.value) {
    return copy.value.metricCopy.results[0]
  }
  return resultKindLabel(report.value.summary.primary_result_kind || 'result')
})
const overviewTrendChart = computed<TrendChartModel>(() => buildTrendChartModel(overviewTrendPoints.value))
const workspaceNotice = computed(() => {
  if (pageNotice.value) {
    return pageNotice.value
  }
  if (!oauthStatus.value) {
    return ''
  }
  const successMessage =
    oauthStatus.value.provider === 'google_ads'
      ? copy.value.googleOauthSuccess
      : oauthStatus.value.provider === 'tiktok_ads'
        ? copy.value.tiktokOauthSuccess
        : copy.value.oauthSuccess
  const errorMessage =
    oauthStatus.value.provider === 'google_ads'
      ? copy.value.googleOauthError
      : oauthStatus.value.provider === 'tiktok_ads'
        ? copy.value.tiktokOauthError
        : copy.value.oauthError
  return oauthStatus.value.status === 'success'
    ? successMessage
    : `${errorMessage}${oauthStatus.value.message ? `: ${oauthStatus.value.message}` : ''}`
})
const workspaceNoticeTone = computed(() => {
  if (pageNotice.value) {
    return 'success'
  }
  return oauthStatus.value?.status === 'error' ? 'error' : 'success'
})
const legalSections = computed<readonly LegalSection[]>(() => {
  if (isTermsView.value) {
    return copy.value.termsSections
  }
  return copy.value.privacySections
})
const legalEyebrow = computed(() => (isTermsView.value ? copy.value.termsOfService : copy.value.privacyPolicy))
const legalTitle = computed(() => (isTermsView.value ? copy.value.termsTitle : copy.value.privacyTitle))
const legalLead = computed(() => (isTermsView.value ? copy.value.termsLead : copy.value.privacyLead))
const legalUpdatedLabel = computed(() =>
  isTermsView.value ? copy.value.termsUpdatedLabel : copy.value.privacyUpdatedLabel,
)
const legalUpdatedOn = computed(() => (isTermsView.value ? copy.value.termsUpdatedOn : copy.value.privacyUpdatedOn))
const userInitial = computed(() => user.value?.email.trim().charAt(0).toUpperCase() || 'C')
const topbarContextLine = computed(() => {
  if (isLegalView.value) {
    return `${legalUpdatedLabel.value}: ${legalUpdatedOn.value}`
  }
  if (!isAuthenticated.value) {
    return copy.value.authLead
  }

  const accountName = report.value?.account.name || selectedAccount.value?.name || ''
  return accountName ? `${selectedProviderLabel.value} · ${accountName}` : selectedProviderLabel.value
})
const workspaceScreenTitle = computed(() => {
  if (workspaceMode.value === 'campaign') {
    return selectedCampaign.value?.name || copy.value.overviewAccount
  }
  if (workspaceMode.value === 'accounts') {
    return copy.value.accountsPageTitle
  }
  if (workspaceMode.value === 'settings') {
    return copy.value.settingsPageTitle
  }
  return copy.value.overviewAccount
})
const connectedAccountGroups = computed<
  readonly { provider: OAuthProvider; label: string; subtitle: string; connected: boolean; cards: WorkspaceAccountCard[] }[]
>(() => [
  {
    provider: 'meta',
    label: 'Meta Ads',
    subtitle: 'Facebook / Instagram',
    connected: accounts.value.length > 0,
    cards: accounts.value.map((account) => ({
      provider: 'meta' as const,
      id: account.external_id,
      name: account.name,
      subtitle: account.account_id,
      currency: account.currency || '—',
      timezone: account.timezone_name || '—',
      accent: 'meta' as const,
    })),
  },
  {
    provider: 'google_ads',
    label: copy.value.googleAds,
    subtitle: 'Google Search / Display',
    connected: reportableGoogleAccounts.value.length > 0,
    cards: reportableGoogleAccounts.value.map((customer) => ({
      provider: 'google_ads' as const,
      id: customer.external_customer_id,
      name: customer.descriptive_name,
      subtitle: formatGoogleCustomerLabel(customer),
      currency: customer.currency_code || '—',
      timezone: customer.time_zone || '—',
      accent: 'google_ads' as const,
    })),
  },
  {
    provider: 'tiktok_ads',
    label: copy.value.tiktokAds,
    subtitle: 'TikTok Ads Manager',
    connected: tiktokAccounts.value.length > 0,
    cards: tiktokAccounts.value.map((advertiser) => ({
      provider: 'tiktok_ads' as const,
      id: advertiser.advertiser_id,
      name: advertiser.name,
      subtitle: formatTikTokAdvertiserLabel(advertiser),
      currency: advertiser.currency || '—',
      timezone: advertiser.timezone_name || '—',
      accent: 'tiktok_ads' as const,
    })),
  },
])
const connectedAccountCount = computed(() => connectedAccountGroups.value.reduce((sum, group) => sum + group.cards.length, 0))

function resolveCurrentView(pathname: string): AppView {
  const normalized = normalizePathname(pathname)
  if (normalized === PRIVACY_ROUTE_PATH) {
    return 'privacy'
  }
  if (normalized === DATA_DELETION_ROUTE_PATH) {
    return 'dataDeletion'
  }
  if (normalized === TERMS_ROUTE_PATH) {
    return 'terms'
  }
  return 'app'
}

function resolveWorkspaceRoute(pathname: string): WorkspaceRoute {
  const normalized = normalizePathname(pathname)
  if (normalized === ACCOUNTS_ROUTE_PATH) {
    return { section: 'accounts', campaignId: '' }
  }
  if (normalized === SETTINGS_ROUTE_PATH) {
    return { section: 'settings', campaignId: '' }
  }
  if (normalized === CAMPAIGNS_ROUTE_PATH || normalized.startsWith(`${CAMPAIGNS_ROUTE_PATH}/`)) {
    const campaignId = decodeURIComponent(normalized.slice(CAMPAIGNS_ROUTE_PATH.length + 1))
    return campaignId ? { section: 'campaign', campaignId } : { section: 'overview', campaignId: '' }
  }
  return { section: 'overview', campaignId: '' }
}

function buildCampaignRoutePath(campaignId: string): string {
  return normalizePathname(`${CAMPAIGNS_ROUTE_PATH}/${encodeURIComponent(campaignId)}`)
}

function routePathForView(view: AppView): string {
  if (view === 'privacy') {
    return PRIVACY_ROUTE_PATH
  }
  if (view === 'dataDeletion') {
    return DATA_DELETION_ROUTE_PATH
  }
  if (view === 'terms') {
    return TERMS_ROUTE_PATH
  }
  return APP_HOME_PATH
}

function routePathForWorkspace(section: WorkspaceSection, campaignId = selectedCampaignId.value): string {
  if (section === 'accounts') {
    return ACCOUNTS_ROUTE_PATH
  }
  if (section === 'settings') {
    return SETTINGS_ROUTE_PATH
  }
  if (section === 'campaign' && campaignId) {
    return buildCampaignRoutePath(campaignId)
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
    const nextWorkspaceRoute = resolveWorkspaceRoute(window.location.pathname)
    workspaceSection.value = nextWorkspaceRoute.section
    if (nextWorkspaceRoute.section === 'campaign') {
      selectedCampaignId.value = nextWorkspaceRoute.campaignId
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

function navigateToWorkspace(section: WorkspaceSection, options: { campaignId?: string; replace?: boolean } = {}) {
  const campaignId = options.campaignId ?? selectedCampaignId.value
  const target = routePathForWorkspace(section, campaignId)
  const method = options.replace ? 'replaceState' : 'pushState'
  if (normalizePathname(window.location.pathname) !== target) {
    window.history[method]({}, '', target)
  }
  workspaceSection.value = section
  if (section === 'campaign' && options.campaignId) {
    selectedCampaignId.value = options.campaignId
  }
  currentView.value = 'app'
}

function openTermsOfService() {
  navigateToView('terms')
}

function openPrivacyPolicy() {
  navigateToView('privacy')
}

function openDataDeletion() {
  navigateToView('dataDeletion')
}

function openOverview() {
  navigateToWorkspace('overview')
}

function openAccountsPage() {
  accountSwitcherOpen.value = false
  navigateToWorkspace('accounts')
}

function openSettingsPage() {
  navigateToWorkspace('settings')
}

function openAppView() {
  openOverview()
}

function handlePopState() {
  currentView.value = resolveCurrentView(window.location.pathname)
  if (currentView.value === 'app') {
    const nextWorkspaceRoute = resolveWorkspaceRoute(window.location.pathname)
    workspaceSection.value = nextWorkspaceRoute.section
    if (nextWorkspaceRoute.section === 'campaign') {
      selectedCampaignId.value = nextWorkspaceRoute.campaignId
    }
  }
}

function updateDocumentTitle() {
  if (isTermsView.value) {
    document.title = `${copy.value.termsOfService} · ${copy.value.brand}`
    return
  }
  if (isPolicyView.value) {
    document.title = `${copy.value.privacyPolicy} · ${copy.value.brand}`
    return
  }
  if (isAuthenticated.value) {
    document.title = `${workspaceScreenTitle.value} · ${copy.value.brand}`
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

function splitAutoVerdictBlocks(value: string) {
  const normalized = value.replace(/\r\n/g, '\n').trim()
  if (!normalized) {
    return []
  }

  const blocks = splitMarkdownBlocks(normalized)
  if (blocks.length > 1) {
    return blocks
  }

  const lines = normalized.split('\n')
  const listLinePattern = /^([-*+]\s+|\d+\.\s+)/
  const headingPattern = /^#{1,6}\s+/

  const listStartIndex = lines.findIndex((line, index) => index > 0 && listLinePattern.test(line.trim()))
  if (listStartIndex > 0) {
    return [lines.slice(0, listStartIndex).join('\n').trim(), lines.slice(listStartIndex).join('\n').trim()].filter(
      Boolean,
    )
  }

  const headingStartIndex = lines.findIndex((line, index) => index > 0 && headingPattern.test(line.trim()))
  if (headingStartIndex > 0) {
    return [lines.slice(0, headingStartIndex).join('\n').trim(), lines.slice(headingStartIndex).join('\n').trim()].filter(
      Boolean,
    )
  }

  if (lines.length > 1 && listLinePattern.test(lines[0].trim())) {
    return [lines[0].trim(), lines.slice(1).join('\n').trim()].filter(Boolean)
  }

  return [normalized]
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

function clearReportState() {
  report.value = null
  resetAutoVerdict()
  reportContextKey.value = ''
  resetChatState()
}

function isGoogleReportableCustomer(customer: GoogleAdsCustomer) {
  return !customer.is_manager
}

function firstGoogleReportableAccountId() {
  const customer = googleAccounts.value.find((item) => isGoogleReportableCustomer(item))
  return customer?.external_customer_id ?? ''
}

function firstProviderAccountId(provider: OAuthProvider) {
  if (provider === 'google_ads') {
    return firstGoogleReportableAccountId()
  }
  if (provider === 'tiktok_ads') {
    return tiktokAccounts.value[0]?.advertiser_id ?? ''
  }
  return accounts.value[0]?.external_id ?? ''
}

function hasValidSelectedAccount(provider: OAuthProvider, accountId: string) {
  if (!accountId) {
    return false
  }
  if (provider === 'google_ads') {
    return googleAccounts.value.some(
      (customer) => customer.external_customer_id === accountId && isGoogleReportableCustomer(customer),
    )
  }
  if (provider === 'tiktok_ads') {
    return tiktokAccounts.value.some((advertiser) => advertiser.advertiser_id === accountId)
  }
  return accounts.value.some((account) => account.external_id === accountId)
}

function resolvePreferredAccountSelection(preferredProvider: OAuthProvider | null = null) {
  if (hasValidSelectedAccount(selectedProvider.value, selectedAccountId.value)) {
    return {
      provider: selectedProvider.value,
      accountId: selectedAccountId.value,
    }
  }

  if (preferredProvider === 'google_ads') {
    const accountId = firstGoogleReportableAccountId()
    if (accountId) {
      return {
        provider: 'google_ads' as const,
        accountId,
      }
    }
  }

  if (preferredProvider === 'tiktok_ads' && tiktokAccounts.value.length > 0) {
    return {
      provider: 'tiktok_ads' as const,
      accountId: tiktokAccounts.value[0].advertiser_id,
    }
  }

  if (preferredProvider === 'meta' && accounts.value.length > 0) {
    return {
      provider: 'meta' as const,
      accountId: accounts.value[0].external_id,
    }
  }

  if (accounts.value.length > 0) {
    return {
      provider: 'meta' as const,
      accountId: accounts.value[0].external_id,
    }
  }

  const googleAccountId = firstGoogleReportableAccountId()
  if (googleAccountId) {
    return {
      provider: 'google_ads' as const,
      accountId: googleAccountId,
    }
  }

  if (tiktokAccounts.value.length > 0) {
    return {
      provider: 'tiktok_ads' as const,
      accountId: tiktokAccounts.value[0].advertiser_id,
    }
  }

  return null
}

function buildReportContextKey(provider: OAuthProvider, accountId: string, days: number) {
  return `${provider}:${accountId}:${days}`
}

function buildDashboardReportPath(provider: OAuthProvider, accountId: string, query: string) {
  if (provider === 'google_ads') {
    return `/dashboard/google-ads/customers/${accountId}/report?${query}`
  }
  if (provider === 'tiktok_ads') {
    return `/dashboard/tiktok-ads/advertisers/${accountId}/report?${query}`
  }
  return `/dashboard/meta/ad-accounts/${accountId}/report?${query}`
}

function buildAutoVerdictPath(provider: OAuthProvider, accountId: string) {
  if (provider === 'google_ads') {
    return `/ai/google-ads/customers/${accountId}/auto-verdict`
  }
  if (provider === 'tiktok_ads') {
    return `/ai/tiktok-ads/advertisers/${accountId}/auto-verdict`
  }
  return `/ai/meta/ad-accounts/${accountId}/auto-verdict`
}

function buildChatPath(provider: OAuthProvider, accountId: string) {
  if (provider === 'google_ads') {
    return `/ai/google-ads/customers/${accountId}/chat`
  }
  if (provider === 'tiktok_ads') {
    return `/ai/tiktok-ads/advertisers/${accountId}/chat`
  }
  return `/ai/meta/ad-accounts/${accountId}/chat`
}

async function syncSelectedAccount(options: { preferredProvider?: OAuthProvider | null; forceReload?: boolean } = {}) {
  const nextSelection = resolvePreferredAccountSelection(options.preferredProvider ?? null)
  if (!nextSelection) {
    selectedProvider.value = 'meta'
    selectedAccountId.value = ''
    clearReportState()
    return
  }

  const selectionChanged =
    nextSelection.provider !== selectedProvider.value || nextSelection.accountId !== selectedAccountId.value

  selectedProvider.value = nextSelection.provider
  selectedAccountId.value = nextSelection.accountId

  if (selectionChanged) {
    resetChatState()
    selectedCampaignId.value = ''
  }

  const nextContextKey = buildReportContextKey(nextSelection.provider, nextSelection.accountId, reportDays.value)
  if (selectionChanged || options.forceReload || reportContextKey.value !== nextContextKey || !report.value) {
    await loadReport()
  }
}

function resetSession() {
  localeUpdateRequestId.value += 1
  accessToken.value = ''
  user.value = null
  oauthStatus.value = null
  accounts.value = []
  googleAccounts.value = []
  tiktokAccounts.value = []
  selectedProvider.value = 'meta'
  selectedAccountId.value = ''
  clearReportState()
  useClientCredentials.value = false
  savedProviderKeys.value = {}
  clientApiKey.value = ''
  authLoading.value = false
  metaConnecting.value = false
  metaDisconnecting.value = false
  googleDisconnecting.value = false
  tiktokConnecting.value = false
  tiktokDisconnecting.value = false
  providerKeyLoading.value = false
  providerKeyEditing.value = false
  providerKeyError.value = ''
  providerKeyNotice.value = ''
  pageNotice.value = ''
  googleConnecting.value = false
  googleAccountsLoading.value = false
  tiktokAccountsLoading.value = false
  localStorage.removeItem(STORAGE_TOKEN_KEY)
  localStorage.removeItem(LEGACY_STORAGE_TOKEN_KEY)
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
  pageNotice.value = ''
  accounts.value = []
  googleAccounts.value = []
  tiktokAccounts.value = []
  selectedProvider.value = 'meta'
  selectedAccountId.value = ''
  clearReportState()

  const callbackUrl = new URL(window.location.href)
  const providerParam = callbackUrl.searchParams.get('provider')
  const statusParam = callbackUrl.searchParams.get('status')
  if (
    (providerParam === 'meta' || providerParam === 'google_ads' || providerParam === 'tiktok_ads') &&
    (statusParam === 'success' || statusParam === 'error')
  ) {
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
    await loadAccounts()
    await loadGoogleAccounts()
    await loadTikTokAccounts()
    await loadSavedProviderKeys()
    await syncSelectedAccount({
      preferredProvider: oauthStatus.value?.status === 'success' ? oauthStatus.value.provider : null,
      forceReload: true,
    })
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
  pageNotice.value = ''
  user.value = null
  accessToken.value = ''
  accounts.value = []
  googleAccounts.value = []
  tiktokAccounts.value = []
  selectedProvider.value = 'meta'
  selectedAccountId.value = ''
  clearReportState()
  localStorage.removeItem(STORAGE_TOKEN_KEY)
  localStorage.removeItem(LEGACY_STORAGE_TOKEN_KEY)

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
    await loadGoogleAccounts()
    await loadTikTokAccounts()
    await loadSavedProviderKeys()
    await syncSelectedAccount({ forceReload: true })
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
    accounts.value = []
    return
  }

  accountsLoading.value = true
  pageError.value = ''

  try {
    accounts.value = await apiRequest<MetaAccount[]>('/meta/ad-accounts')
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
    googleAccounts.value = await apiRequest<GoogleAdsCustomer[]>('/google-ads/customers')
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    googleAccountsLoading.value = false
  }
}

async function loadTikTokAccounts() {
  if (!user.value) {
    tiktokAccounts.value = []
    return
  }

  tiktokAccountsLoading.value = true

  try {
    tiktokAccounts.value = await apiRequest<TikTokAdsAdvertiser[]>('/tiktok-ads/advertisers')
  } catch (error) {
    if (!(error instanceof Error) || !error.message.includes('Not Found')) {
      pageError.value = error instanceof Error ? error.message : 'Unexpected error'
    }
  } finally {
    tiktokAccountsLoading.value = false
  }
}

async function connectMeta() {
  metaConnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    const payload = await apiRequest<{ authorization_url: string }>('/meta/oauth/start')
    window.location.href = payload.authorization_url
  } catch (error) {
    metaConnecting.value = false
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  }
}

async function disconnectMeta() {
  if (metaDisconnecting.value || !window.confirm(copy.value.disconnectMetaConfirm)) {
    return
  }

  metaDisconnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    await apiRequest('/meta/connections', { method: 'DELETE' })
    oauthStatus.value = null
    await loadAccounts()
    await loadGoogleAccounts()
    await syncSelectedAccount({ preferredProvider: 'google_ads', forceReload: true })
    pageNotice.value = copy.value.metaDisconnectSuccess
  } catch (error) {
    pageError.value = formatUnexpectedError(error)
  } finally {
    metaDisconnecting.value = false
  }
}

async function connectGoogle() {
  googleConnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    const payload = await apiRequest<{ authorization_url: string }>('/google-ads/oauth/start')
    window.location.href = payload.authorization_url
  } catch (error) {
    googleConnecting.value = false
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  }
}

async function disconnectGoogle() {
  if (googleDisconnecting.value || !window.confirm(copy.value.disconnectGoogleConfirm)) {
    return
  }

  googleDisconnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    await apiRequest('/google-ads/connections', { method: 'DELETE' })
    oauthStatus.value = null
    await loadGoogleAccounts()
    await loadAccounts()
    await syncSelectedAccount({ preferredProvider: 'meta', forceReload: true })
    pageNotice.value = copy.value.googleDisconnectSuccess
  } catch (error) {
    pageError.value = formatUnexpectedError(error)
  } finally {
    googleDisconnecting.value = false
  }
}

async function connectTikTok() {
  tiktokConnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    const payload = await apiRequest<{ authorization_url: string }>('/tiktok-ads/oauth/start')
    window.location.href = payload.authorization_url
  } catch (error) {
    tiktokConnecting.value = false
    pageError.value = error instanceof Error ? error.message : 'Unexpected error'
  }
}

async function disconnectTikTok() {
  if (tiktokDisconnecting.value || !window.confirm(copy.value.disconnectTikTokConfirm)) {
    return
  }

  tiktokDisconnecting.value = true
  pageError.value = ''
  pageNotice.value = ''

  try {
    await apiRequest('/tiktok-ads/connections', { method: 'DELETE' })
    oauthStatus.value = null
    await loadTikTokAccounts()
    await loadAccounts()
    await loadGoogleAccounts()
    await syncSelectedAccount({ preferredProvider: 'meta', forceReload: true })
    pageNotice.value = copy.value.tiktokDisconnectSuccess
  } catch (error) {
    pageError.value = formatUnexpectedError(error)
  } finally {
    tiktokDisconnecting.value = false
  }
}

async function loadReport(options: { forceRefresh?: boolean } = {}) {
  if (!selectedAccountId.value) {
    return
  }

  const nextContextKey = buildReportContextKey(selectedProvider.value, selectedAccountId.value, reportDays.value)
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
    const payload = await apiRequest<DashboardReport>(buildDashboardReportPath(selectedProvider.value, selectedAccountId.value, query.toString()))
    report.value = payload
    reportContextKey.value = nextContextKey
    selectedCampaignId.value = payload.campaigns.find((campaign) => campaign.id === selectedCampaignId.value)?.id ?? ''
    if (workspaceSection.value === 'campaign' && !selectedCampaignId.value) {
      navigateToWorkspace('overview', { replace: true })
    }
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

    const apiKey = useClientCredentials.value ? clientApiKey.value.trim() || null : null
    if (useClientCredentials.value && !apiKey && !canUseSavedProviderKey.value) {
      autoVerdict.value = copy.value.missingCustomKeyError
      autoVerdictExpanded.value = false
      return
    }

    verdictLoading.value = true
    autoVerdictExpanded.value = false
    const payload = await apiRequest<{ text: string }>(buildAutoVerdictPath(selectedProvider.value, selectedAccountId.value), {
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
      },
    })
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
    const payload = await apiRequest<{ text: string }>(buildChatPath(selectedProvider.value, selectedAccountId.value), {
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

function handleViewportResize() {
  viewportWidth.value = window.innerWidth
  if (viewportWidth.value < 1024) {
    sidebarCollapsed.value = false
  }
}

function openAiPanel() {
  aiPanelOpen.value = true
}

function closeAiPanel() {
  aiPanelOpen.value = false
}

function connectProvider(providerOption: OAuthProvider) {
  if (providerOption === 'google_ads') {
    void connectGoogle()
    return
  }
  if (providerOption === 'tiktok_ads') {
    void connectTikTok()
    return
  }
  void connectMeta()
}

function disconnectProvider(providerOption: OAuthProvider) {
  if (providerOption === 'google_ads') {
    void disconnectGoogle()
    return
  }
  if (providerOption === 'tiktok_ads') {
    void disconnectTikTok()
    return
  }
  void disconnectMeta()
}

function connectCurrentProvider() {
  openConnectModal(selectedProvider.value)
}

function disconnectCurrentProvider() {
  disconnectProvider(selectedProvider.value)
}

function startProviderConnection(providerOption: OAuthProvider) {
  openConnectModal(providerOption)
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function providerIsConnecting(providerOption: OAuthProvider) {
  if (providerOption === 'google_ads') {
    return googleConnecting.value
  }
  if (providerOption === 'tiktok_ads') {
    return tiktokConnecting.value
  }
  return metaConnecting.value || metaDisconnecting.value
}

function providerConnectLabel(providerOption: OAuthProvider) {
  if (providerIsConnecting(providerOption)) {
    return copy.value.loading
  }
  if (providerOption === 'google_ads') {
    return copy.value.connectGoogle
  }
  if (providerOption === 'tiktok_ads') {
    return copy.value.connectTikTok
  }
  return copy.value.connectMeta
}

function providerGlyph(providerOption: OAuthProvider) {
  if (providerOption === 'google_ads') {
    return 'G'
  }
  if (providerOption === 'tiktok_ads') {
    return 'T'
  }
  return 'M'
}

function openConnectModal(providerOption: OAuthProvider | null = null) {
  connectModalProvider.value = providerOption
  connectModalOpen.value = true
  accountSwitcherOpen.value = false
  platformMenuOpen.value = false
}

function closeConnectModal() {
  connectModalOpen.value = false
  connectModalProvider.value = null
}

function connectFromModal(providerOption: OAuthProvider) {
  closeConnectModal()
  connectProvider(providerOption)
}

function setWorkspaceProvider(provider: OAuthProvider) {
  platformMenuOpen.value = false
  const nextAccountId = firstProviderAccountId(provider)
  if (nextAccountId) {
    selectAccount(provider, nextAccountId)
    return
  }

  if (selectedProvider.value === provider && selectedAccountId.value === '') {
    return
  }

  selectedProvider.value = provider
  selectedAccountId.value = ''
  clearReportState()
}

function handleGlobalPointer(event: MouseEvent) {
  const target = event.target as Node
  if (accountSwitcherRef.value && !accountSwitcherRef.value.contains(target)) {
    accountSwitcherOpen.value = false
  }
  if (platformMenuRef.value && !platformMenuRef.value.contains(target)) {
    platformMenuOpen.value = false
  }
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') {
    return
  }
  accountSwitcherOpen.value = false
  platformMenuOpen.value = false
  connectModalOpen.value = false
  if (isAiOverlay.value) {
    aiPanelOpen.value = false
  }
}

function selectAccount(provider: OAuthProvider, accountId: string) {
  if (provider === 'google_ads') {
    const customer = googleAccounts.value.find((item) => item.external_customer_id === accountId)
    if (customer && !isGoogleReportableCustomer(customer)) {
      return
    }
  }
  if (selectedProvider.value === provider && selectedAccountId.value === accountId) {
    return
  }
  accountSwitcherOpen.value = false
  platformMenuOpen.value = false
  selectedProvider.value = provider
  selectedAccountId.value = accountId
  selectedCampaignId.value = ''
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
  navigateToWorkspace('campaign', { campaignId })
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
    maximumFractionDigits: key === 'results' ? 1 : 0,
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
  const parts = [accountKind, accessKind, formatGoogleCustomerId(customer.external_customer_id)]
  if (customer.is_manager) {
    parts.push(copy.value.googleManagerNoReports)
  }
  return parts.join(' · ')
}

function formatTikTokAdvertiserLabel(advertiser: TikTokAdsAdvertiser) {
  return [advertiser.status, advertiser.currency, advertiser.advertiser_id].filter(Boolean).join(' · ')
}

function accountCardInitials(value: string) {
  const parts = value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
  if (parts.length === 0) {
    return 'AD'
  }
  return parts
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
    .slice(0, 2)
}

function formatDelta(delta: number | null | undefined) {
  if (delta === null || delta === undefined) {
    return '—'
  }
  const prefix = delta > 0 ? '+' : ''
  return `${prefix}${delta.toFixed(1)}%`
}

function metricPerformanceTone(key: MetricKey, delta: number | null | undefined): SurfaceMetricCard['deltaTone'] {
  if (delta === null || delta === undefined || delta === 0) {
    return 'neutral'
  }
  const lowerIsBetter = key === 'cost_per_result' || key === 'cpc' || key === 'cpm'
  const isGood = lowerIsBetter ? delta < 0 : delta > 0
  return isGood ? 'good' : 'warning'
}

function metricSurfaceLabel(key: MetricKey, resultKind: string) {
  if (key === 'results') {
    return resultKindLabel(resultKind || 'result')
  }
  return copy.value.metricCopy[key][0]
}

function metricSurfaceHint(key: MetricKey, delta: number | null | undefined) {
  const tone = metricPerformanceTone(key, delta)
  if (tone === 'good') {
    return copy.value.metricTrendGood
  }
  if (tone === 'warning') {
    return copy.value.metricTrendWarning
  }
  return copy.value.metricTrendNeutral
}

function buildSurfaceMetricCards(metrics: MetricCollection, resultKind: string): SurfaceMetricCard[] {
  return overviewMetricKeys.map((key) => {
    const metric = metrics[key]
    return {
      key,
      label: metricSurfaceLabel(key, resultKind),
      value: formatMetricValue(key, metric.current),
      subtitle: copy.value.metricCopy[key][1],
      deltaLabel: formatDelta(metric.delta_pct),
      deltaTone: metricPerformanceTone(key, metric.delta_pct),
    }
  })
}

function formatTrendAxisCurrency(value: number) {
  const currency = report.value?.account.currency || selectedAccount.value?.currency || 'USD'
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency,
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value)
}

function formatTrendAxisResult(value: number) {
  return new Intl.NumberFormat(locale.value, {
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 100 ? 0 : value < 10 ? 1 : 0,
  }).format(value)
}

function formatTrendDateLabel(value: string) {
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(locale.value, {
    day: '2-digit',
    month: '2-digit',
  }).format(parsed)
}

function buildTrendLinePath(points: TrendChartPointView[], key: 'spendY' | 'resultsY') {
  if (points.length === 0) {
    return ''
  }
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point[key]}`).join(' ')
}

function buildTrendAreaPath(points: TrendChartPointView[], key: 'spendY' | 'resultsY') {
  if (points.length === 0) {
    return ''
  }
  const baseline = trendChartFrame.height - trendChartFrame.bottom
  const line = buildTrendLinePath(points, key)
  const lastPoint = points[points.length - 1]
  const firstPoint = points[0]
  return `${line} L ${lastPoint.x} ${baseline} L ${firstPoint.x} ${baseline} Z`
}

function buildTrendTicks(points: TrendChartPointView[]): TrendChartTick[] {
  if (points.length <= 6) {
    return points.map((point) => ({ x: point.x, label: point.label }))
  }
  const indexes = Array.from(
    new Set([0, Math.floor((points.length - 1) / 3), Math.floor(((points.length - 1) * 2) / 3), points.length - 1]),
  )
  return indexes.map((index) => ({
    x: points[index].x,
    label: points[index].label,
  }))
}

function buildTrendChartModel(points: TrendPoint[]): TrendChartModel {
  if (points.length === 0) {
    return {
      hasData: false,
      points: [],
      spendLine: '',
      spendArea: '',
      resultsLine: '',
      resultsArea: '',
      gridLines: [],
      ticks: [],
    }
  }

  const plotWidth = trendChartFrame.width - trendChartFrame.left - trendChartFrame.right
  const plotHeight = trendChartFrame.height - trendChartFrame.top - trendChartFrame.bottom
  const spendMax = Math.max(1, ...points.map((point) => point.spend || 0))
  const resultsMax = Math.max(1, ...points.map((point) => point.results || 0))
  const viewPoints = points.map<TrendChartPointView>((point, index) => {
    const x =
      points.length === 1
        ? trendChartFrame.left + plotWidth / 2
        : trendChartFrame.left + (plotWidth * index) / (points.length - 1)
    const spendY = trendChartFrame.top + plotHeight - ((point.spend || 0) / spendMax) * plotHeight
    const resultsY = trendChartFrame.top + plotHeight - ((point.results || 0) / resultsMax) * plotHeight
    return {
      ...point,
      x,
      spendY,
      resultsY,
      label: formatTrendDateLabel(point.date),
    }
  })
  const gridLines = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3
    const y = trendChartFrame.top + plotHeight * ratio
    return {
      y,
      spendLabel: formatTrendAxisCurrency(spendMax * (1 - ratio)),
      resultsLabel: formatTrendAxisResult(resultsMax * (1 - ratio)),
    }
  })

  return {
    hasData: true,
    points: viewPoints,
    spendLine: buildTrendLinePath(viewPoints, 'spendY'),
    spendArea: buildTrendAreaPath(viewPoints, 'spendY'),
    resultsLine: buildTrendLinePath(viewPoints, 'resultsY'),
    resultsArea: buildTrendAreaPath(viewPoints, 'resultsY'),
    gridLines,
    ticks: buildTrendTicks(viewPoints),
  }
}

function statusTone(status: string) {
  const normalized = status.toUpperCase()
  if (normalized.includes('ACTIVE') || normalized === 'ENABLED') {
    return 'active'
  }
  if (normalized.includes('PAUSED') || normalized === 'DISABLED') {
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
  () => [currentView.value, locale.value, isAuthenticated.value, workspaceScreenTitle.value],
  () => {
    updateDocumentTitle()
  },
  { immediate: true },
)

onMounted(() => {
  localStorage.removeItem(LEGACY_STORAGE_LOCALE_KEY)
  applyLocale(locale.value, { persist: false })
  applyProviderDefaultPreset()
  handleViewportResize()
  window.addEventListener('popstate', handlePopState)
  window.addEventListener('resize', handleViewportResize)
  window.addEventListener('mousedown', handleGlobalPointer)
  window.addEventListener('keydown', handleGlobalKeydown)
  void syncView(currentView.value)
})

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('resize', handleViewportResize)
  window.removeEventListener('mousedown', handleGlobalPointer)
  window.removeEventListener('keydown', handleGlobalKeydown)
})

watch(currentView, (view) => {
  void syncView(view)
})
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell-auth': !bootLoading && !isAuthenticated && !isLegalView }">
    <header v-if="!bootLoading && isLegalView" class="topbar">
      <template>
        <div class="topbar-brand">
          <div class="brand-lockup" aria-label="chatico ads">
            <span class="brand-mark" aria-hidden="true">
              <span class="brand-mark-bubble"></span>
            </span>
            <span class="brand-wordmark">
              <span class="brand-wordmark-main">chatico</span>
              <span class="brand-wordmark-sub">ads</span>
            </span>
          </div>
          <div class="topbar-copy">
            <p class="eyebrow">{{ copy.brand }}</p>
            <p class="topbar-subtitle">{{ topbarContextLine }}</p>
          </div>
        </div>

        <div class="topbar-title">
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

          <button
            type="button"
            class="ghost-button"
            :class="{ active: isTermsView }"
            :disabled="currentView === 'terms'"
            @click="openTermsOfService"
          >
            {{ copy.termsOfService }}
          </button>

          <button v-if="isLegalView" type="button" class="ghost-button" @click="openAppView">
            {{ copy.backToApp }}
          </button>

          <button v-if="isAuthenticated" type="button" class="ghost-button" @click="logout">
            {{ copy.logout }}
          </button>

          <div v-if="isAuthenticated && user" class="user-pill">
            <span class="user-avatar">{{ userInitial }}</span>
            <span class="user-email">{{ user.email }}</span>
          </div>
        </div>
      </template>
    </header>

    <main v-if="isLegalView" class="policy-stage">
      <section class="policy-surface">
        <div class="policy-hero">
          <p class="eyebrow">{{ legalEyebrow }}</p>
          <h2>{{ legalTitle }}</h2>
          <p class="auth-copy">{{ legalLead }}</p>

          <div class="policy-meta">
            <span class="policy-chip">{{ legalUpdatedLabel }}: {{ legalUpdatedOn }}</span>
            <template v-if="isPolicyView">
              <span class="policy-chip">{{ copy.privacyMetaScopeLabel }}: ads_read</span>
              <span class="policy-chip">{{ copy.privacyGoogleScopeLabel }}: adwords</span>
              <span class="policy-chip">{{ copy.privacyTikTokScopeLabel }}: read-only advertiser/reporting</span>
              <a class="ghost-link" :href="`mailto:${PRIVACY_CONTACT_EMAIL}`">{{ PRIVACY_CONTACT_EMAIL }}</a>
              <button type="button" class="ghost-button" @click="openDataDeletion">
                {{ copy.dataDeletionLabel }}
              </button>
              <button type="button" class="ghost-button" @click="openTermsOfService">
                {{ copy.termsOfService }}
              </button>
            </template>
            <template v-else>
              <button type="button" class="ghost-button" @click="openPrivacyPolicy">
                {{ copy.termsPrivacyLinkLabel }}
              </button>
            </template>
          </div>
        </div>

        <div class="policy-grid">
          <section
            v-for="section in legalSections"
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
      <section class="auth-shell">
        <div class="brand-lockup auth-shell-brand" aria-label="chatico ads">
          <span class="brand-mark" aria-hidden="true">
            <span class="brand-mark-bubble"></span>
          </span>
          <span class="brand-wordmark">
            <span class="brand-wordmark-main">chatico</span>
            <span class="brand-wordmark-sub">ads</span>
          </span>
        </div>

        <div class="auth-panel auth-shell-card">
          <p class="auth-shell-eyebrow">Meta · Google · TikTok</p>
          <p class="auth-shell-copy">{{ copy.authLead }}</p>

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

            <button type="submit" class="primary-button auth-submit" :disabled="authLoading">
              {{ authMode === 'register' ? copy.signUp : copy.signIn }}
            </button>
          </form>

          <p class="panel-hint auth-panel-hint">{{ copy.authHint }}</p>
          <p v-if="authError" class="message error">{{ authError }}</p>
          <p v-else-if="pageError" class="message error">{{ pageError }}</p>

          <div class="auth-shell-links">
            <button type="button" class="ghost-button compact-button" @click="openPrivacyPolicy">
              {{ copy.privacyPolicy }}
            </button>
            <button type="button" class="ghost-button compact-button" @click="openTermsOfService">
              {{ copy.termsOfService }}
            </button>
          </div>
        </div>
      </section>
    </main>

    <main
      v-else
      class="workspace"
      :class="{ 'workspace-ai-closed': !aiPanelOpen, 'workspace-ai-overlay': isAiOverlay }"
      :style="workspaceGridStyle"
    >
      <aside class="rail rail-left" :class="{ collapsed: sidebarCollapsed }">
        <button
          type="button"
          class="sidebar-toggle"
          aria-label="Toggle sidebar"
          :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="toggleSidebar"
        >
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div class="workspace-brand-panel" :class="{ collapsed: sidebarCollapsed }">
          <div class="brand-lockup" aria-label="chatico ads">
            <span class="brand-mark" aria-hidden="true">
              <span class="brand-mark-bubble"></span>
            </span>
            <span class="brand-wordmark">
              <span class="brand-wordmark-main">chatico</span>
              <span class="brand-wordmark-sub">ads</span>
            </span>
          </div>
          <p v-if="!sidebarCollapsed" class="workspace-brand-note">{{ currentProviderOption.subtitle }}</p>
        </div>

        <section ref="platformMenuRef" class="rail-section platform-section" :class="{ collapsed: sidebarCollapsed }">
          <p v-if="!sidebarCollapsed" class="section-kicker">{{ copy.platforms }}</p>
          <button
            type="button"
            class="platform-switcher"
            :class="{ collapsed: sidebarCollapsed }"
            @click="platformMenuOpen = !platformMenuOpen"
          >
            <span class="platform-badge" :class="selectedProvider">
              {{ providerGlyph(selectedProvider) }}
            </span>
            <div v-if="!sidebarCollapsed" class="platform-switcher-copy">
              <strong>{{ currentProviderOption.label }}</strong>
              <small>{{ currentProviderOption.subtitle }}</small>
            </div>
            <span v-if="!sidebarCollapsed" class="platform-switcher-meta">{{ currentProviderOption.count }}</span>
            <span v-else class="nav-tooltip">{{ currentProviderOption.label }}</span>
          </button>

          <div v-if="platformMenuOpen" class="platform-menu" :class="{ collapsed: sidebarCollapsed }">
            <button
              v-for="providerOption in providerOptions"
              :key="providerOption.key"
              type="button"
              class="platform-option"
              :class="{ active: selectedProvider === providerOption.key }"
              @click="setWorkspaceProvider(providerOption.key)"
            >
              <span class="platform-badge" :class="providerOption.key">
                {{ providerGlyph(providerOption.key) }}
              </span>
              <div class="platform-option-copy">
                <strong>{{ providerOption.label }}</strong>
                <small>{{ providerOption.subtitle }}</small>
              </div>
              <span class="platform-option-state">{{ providerOption.count }}</span>
            </button>
          </div>
        </section>

        <section class="rail-section rail-primary-nav">
          <button
            type="button"
            class="overview-nav"
            :class="{ active: workspaceMode === 'overview', 'icon-only': sidebarCollapsed }"
            @click="openOverview"
          >
            <svg class="overview-nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M3 12l8.25-8.25a1.06 1.06 0 011.5 0L21 12m-2.25-2.25V19.5a1.5 1.5 0 01-1.5 1.5h-3.75v-5.25h-3V21H6.75a1.5 1.5 0 01-1.5-1.5V9.75"
              />
            </svg>
            <span v-if="!sidebarCollapsed">{{ copy.sidebarOverview }}</span>
            <span v-else class="nav-tooltip">{{ copy.sidebarOverview }}</span>
          </button>

          <button
            type="button"
            class="overview-nav"
            :class="{ active: workspaceMode === 'accounts', 'icon-only': sidebarCollapsed }"
            @click="openAccountsPage"
          >
            <svg class="overview-nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <span v-if="!sidebarCollapsed">{{ copy.sidebarAccounts }}</span>
            <span v-else class="nav-tooltip">{{ copy.sidebarAccounts }}</span>
          </button>
        </section>

        <div class="rail-divider"></div>

        <section v-if="!sidebarCollapsed" class="rail-section rail-campaigns">
          <button type="button" class="section-head rail-section-toggle" @click="campaignsExpanded = !campaignsExpanded">
            <span>{{ copy.campaigns }}</span>
            <small>{{ report?.campaigns?.length ?? 0 }}</small>
            <svg class="section-toggle-icon" :class="{ open: campaignsExpanded }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <div v-if="campaignsExpanded && report?.campaigns?.length" class="campaign-tree">
            <button
              v-for="(campaign, index) in report.campaigns"
              :key="campaign.id"
              type="button"
              class="campaign-nav"
              :class="{ active: workspaceMode === 'campaign' && selectedCampaignId === campaign.id }"
              @click="selectCampaign(campaign.id)"
            >
              <span class="campaign-tree-line" :class="{ last: index === report.campaigns.length - 1 }"></span>
              <span class="campaign-tree-branch"></span>
              <span v-if="workspaceMode === 'campaign' && selectedCampaignId === campaign.id" class="campaign-tree-marker"></span>
              <strong>{{ campaign.name }}</strong>
              <small>{{ formatMetricValue('spend', campaign.metrics.spend.current) }}</small>
            </button>
          </div>
          <div v-else-if="campaignsExpanded" class="empty-note">{{ copy.emptyCampaigns }}</div>
        </section>

        <div class="rail-spacer"></div>

        <div class="rail-footer-links" :class="{ collapsed: sidebarCollapsed }">
          <button
            type="button"
            class="overview-nav rail-footer-nav"
            :class="{ active: workspaceMode === 'settings', 'icon-only': sidebarCollapsed }"
            @click="openSettingsPage"
          >
            <svg class="overview-nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M10.325 4.317a1.724 1.724 0 013.35 0l.178.924a1.724 1.724 0 002.573 1.066l.82-.47a1.724 1.724 0 012.354.63l.67 1.16a1.724 1.724 0 01-.63 2.354l-.82.47a1.724 1.724 0 000 2.984l.82.47a1.724 1.724 0 01.63 2.354l-.67 1.16a1.724 1.724 0 01-2.354.63l-.82-.47a1.724 1.724 0 00-2.573 1.066l-.178.924a1.724 1.724 0 01-3.35 0l-.178-.924a1.724 1.724 0 00-2.573-1.066l-.82.47a1.724 1.724 0 01-2.354-.63l-.67-1.16a1.724 1.724 0 01.63-2.354l.82-.47a1.724 1.724 0 000-2.984l-.82-.47a1.724 1.724 0 01-.63-2.354l.67-1.16a1.724 1.724 0 012.354-.63l.82.47a1.724 1.724 0 002.573-1.066l.178-.924z"
              />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span v-if="!sidebarCollapsed">{{ copy.sidebarSettings }}</span>
            <span v-else class="nav-tooltip">{{ copy.sidebarSettings }}</span>
          </button>

          <div v-if="!sidebarCollapsed" class="rail-meta-links">
            <button type="button" class="rail-footer-link" @click="openPrivacyPolicy">{{ copy.privacyPolicy }}</button>
            <button type="button" class="rail-footer-link" @click="openTermsOfService">{{ copy.termsOfService }}</button>
            <button type="button" class="rail-footer-link" @click="logout">{{ copy.logout }}</button>
          </div>
        </div>
      </aside>

      <section class="stage-center">
        <header class="topbar topbar-workspace workspace-stage-topbar">
          <div ref="accountSwitcherRef" class="account-switcher">
            <button type="button" class="account-switcher-trigger" @click="accountSwitcherOpen = !accountSwitcherOpen">
              <span class="account-switcher-avatar">
                {{ selectedAccount?.name?.trim().charAt(0).toUpperCase() || selectedProviderLabel.charAt(0) }}
              </span>
              <div class="account-switcher-copy">
                <span>{{ copy.accountSwitcherLabel }}</span>
                <strong>{{ accountSwitcherLabel }}</strong>
                <small>{{ accountSwitcherSubtitle }}</small>
              </div>
              <svg
                class="account-switcher-chevron"
                :class="{ open: accountSwitcherOpen }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div v-if="accountSwitcherOpen" class="account-switcher-menu">
              <p class="account-switcher-eyebrow">{{ copy.yourAccounts }}</p>
              <div v-if="currentProviderAccounts.length === 0" class="empty-note">
                {{ currentProviderEmptyMessage }}
              </div>
              <button
                v-for="item in currentProviderAccounts"
                :key="`${item.provider}:${item.id}`"
                type="button"
                class="account-switcher-option"
                :class="{ active: selectedProvider === item.provider && selectedAccountId === item.id }"
                @click="selectAccount(item.provider, item.id)"
              >
                <span class="account-switcher-option-avatar">{{ item.name.charAt(0).toUpperCase() }}</span>
                <div class="account-switcher-option-copy">
                  <strong>{{ item.name }}</strong>
                  <small>{{ item.subtitle }}</small>
                </div>
                <svg
                  v-if="selectedProvider === item.provider && selectedAccountId === item.id"
                  class="account-switcher-check"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2.5"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </button>

              <div class="account-switcher-divider"></div>

              <button type="button" class="menu-action" @click="connectCurrentProvider">
                {{
                  selectedProvider === 'google_ads'
                    ? copy.connectGoogle
                    : selectedProvider === 'tiktok_ads'
                      ? copy.connectTikTok
                      : copy.connectMeta
                }}
              </button>
              <button v-if="currentProviderHasAccounts" type="button" class="menu-action muted" @click="disconnectCurrentProvider">
                {{
                  selectedProvider === 'google_ads'
                    ? copy.disconnectGoogle
                    : selectedProvider === 'tiktok_ads'
                      ? copy.disconnectTikTok
                      : copy.disconnectMeta
                }}
              </button>
              <button type="button" class="menu-action muted" @click="openAccountsPage">
                {{ copy.sidebarAccounts }}
              </button>
            </div>
          </div>

          <div class="toolbar workspace-toolbar">
            <button v-if="!aiPanelOpen" type="button" class="ghost-button ai-reopen-button" @click="openAiPanel">
              <svg class="ai-reopen-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
              </svg>
              {{ copy.askAi }}
            </button>
            <div v-if="!aiPanelOpen" class="workspace-toolbar-divider" aria-hidden="true"></div>
            <div v-if="user" class="workspace-user">
              <span class="user-avatar">{{ userInitial }}</span>
              <span class="user-email">{{ user.email }}</span>
            </div>
          </div>
        </header>

        <div v-if="workspaceNotice" class="message" :class="workspaceNoticeTone">
          {{ workspaceNotice }}
        </div>
        <div v-if="pageError" class="message error">{{ pageError }}</div>

        <template v-if="workspaceMode === 'settings'">
          <section class="hero-strip dashboard-hero">
            <div>
              <p class="eyebrow">{{ copy.sidebarSettings }}</p>
              <h2>{{ copy.settingsPageTitle }}</h2>
              <p class="muted">{{ copy.settingsPageLead }}</p>
            </div>
          </section>

          <section class="settings-grid">
            <article class="settings-card">
              <div class="section-head">
                <div>
                  <span>{{ copy.settingsProfileTitle }}</span>
                  <p class="surface-note">{{ copy.settingsProfileLead }}</p>
                </div>
              </div>
              <div class="profile-stack">
                <div class="profile-row">
                  <span class="user-avatar large">{{ userInitial }}</span>
                  <div>
                    <strong>{{ user?.email || copy.brand }}</strong>
                    <small>{{ currentProviderOption.label }} · {{ currentProviderOption.subtitle }}</small>
                  </div>
                </div>
                <button type="button" class="ghost-button compact-button" @click="logout">
                  {{ copy.logout }}
                </button>
              </div>
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <span>{{ copy.settingsLanguageTitle }}</span>
                  <p class="surface-note">{{ copy.settingsLanguageLead }}</p>
                </div>
              </div>
              <div class="lang-switch settings-lang-switch" role="tablist" :aria-label="copy.locale">
                <button
                  v-for="lang in ['ru', 'kz', 'en']"
                  :key="`settings-${lang}`"
                  type="button"
                  class="lang-pill"
                  :class="{ active: locale === lang }"
                  @click="void syncLocale(lang as Locale)"
                >
                  {{ lang.toUpperCase() }}
                </button>
              </div>
            </article>

            <article class="settings-card settings-card-wide">
              <div class="section-head">
                <div>
                  <span>{{ copy.settingsAiTitle }}</span>
                  <p class="surface-note">{{ copy.settingsAiLead }}</p>
                </div>
              </div>

              <div class="settings-pill-row">
                <span class="settings-badge">{{ activeProviderConfig?.label || provider }}</span>
                <span class="settings-badge">{{ resolvedModel || activeProviderConfig?.default_model }}</span>
                <span class="settings-badge" :class="{ muted: !hasSavedProviderKey }">
                  {{ hasSavedProviderKey ? copy.settingsSavedKey : copy.settingsNoSavedKey }}
                </span>
              </div>

              <div class="chat-advanced-toggle settings-toggle-row">
                <button
                  type="button"
                  class="ghost-button compact-button"
                  @click="useClientCredentials = !useClientCredentials"
                >
                  {{ useClientCredentials ? copy.hideOwnApiKey : copy.useOwnApiKey }}
                </button>
              </div>

              <div class="chat-advanced settings-advanced">
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
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <span>{{ copy.settingsLegalTitle }}</span>
                  <p class="surface-note">{{ copy.settingsLegalLead }}</p>
                </div>
              </div>
              <div class="settings-links">
                <button type="button" class="ghost-button compact-button" @click="openPrivacyPolicy">
                  {{ copy.privacyPolicy }}
                </button>
                <button type="button" class="ghost-button compact-button" @click="openTermsOfService">
                  {{ copy.termsOfService }}
                </button>
              </div>
            </article>
          </section>
        </template>

        <template v-else-if="workspaceMode === 'accounts'">
          <section class="hero-strip dashboard-hero">
            <div>
              <p class="eyebrow">{{ copy.sidebarAccounts }}</p>
              <h2>{{ copy.accountsPageTitle }}</h2>
              <p class="muted">
                {{ copy.accountsPageLead }}
                <span> · {{ copy.accountsPageConnected }}: {{ connectedAccountCount }}</span>
              </p>
            </div>
            <div class="hero-actions-stack">
              <button type="button" class="primary-button compact" @click="openConnectModal()">
                {{ copy.manageConnections }}
              </button>
            </div>
          </section>

          <section v-if="connectedAccountCount === 0" class="empty-surface">
            <p class="eyebrow">{{ copy.accounts }}</p>
            <h2>{{ copy.accountsPageEmptyTitle }}</h2>
            <p>{{ copy.accountsPageEmptyBody }}</p>
            <div class="empty-surface-actions">
              <button type="button" class="primary-button" @click="openConnectModal()">
                {{ copy.manageConnections }}
              </button>
            </div>
          </section>

          <section v-else class="account-page-grid">
            <article v-for="group in connectedAccountGroups" :key="group.provider" class="account-page-section">
              <div class="account-provider-head">
                <div>
                  <p class="eyebrow">{{ group.label }}</p>
                  <h3>{{ group.subtitle }}</h3>
                </div>
                <div class="section-actions">
                  <button
                    type="button"
                    class="ghost-button compact-button"
                    @click="startProviderConnection(group.provider)"
                  >
                    {{
                      group.provider === 'google_ads'
                        ? copy.connectGoogle
                        : group.provider === 'tiktok_ads'
                          ? copy.connectTikTok
                          : copy.connectMeta
                    }}
                  </button>
                  <button
                    v-if="group.connected"
                    type="button"
                    class="ghost-button compact-button"
                    @click="disconnectProvider(group.provider)"
                  >
                    {{
                      group.provider === 'google_ads'
                        ? copy.disconnectGoogle
                        : group.provider === 'tiktok_ads'
                          ? copy.disconnectTikTok
                          : copy.disconnectMeta
                    }}
                  </button>
                </div>
              </div>

              <div v-if="group.cards.length === 0" class="empty-note">
                {{
                  group.provider === 'google_ads'
                    ? copy.googleAccountsEmpty
                    : group.provider === 'tiktok_ads'
                      ? copy.tiktokAccountsEmpty
                      : copy.noAccountsBody
                }}
              </div>

              <div v-else class="account-card-grid">
                <article
                  v-for="card in group.cards"
                  :key="`${group.provider}:${card.id}`"
                  class="account-card"
                  :class="[
                    card.accent,
                    { active: selectedProvider === group.provider && selectedAccountId === card.id },
                  ]"
                >
                  <div class="account-card-head">
                    <div class="account-card-profile">
                      <div class="account-card-avatar">{{ accountCardInitials(card.name) }}</div>
                      <div class="account-card-copy">
                        <div class="account-card-title-row">
                          <strong>{{ card.name }}</strong>
                          <span class="account-card-platform">{{ group.label }}</span>
                        </div>
                        <small>{{ card.subtitle }}</small>
                        <span class="account-card-status">
                          <i class="status-dot active"></i>
                          {{ copy.accountCardConnected }}
                        </span>
                      </div>
                    </div>
                    <span v-if="selectedProvider === group.provider && selectedAccountId === card.id" class="account-card-badge">
                      {{ copy.accountsPageSelected }}
                    </span>
                  </div>

                  <div class="account-card-stats">
                    <div class="account-card-stat">
                      <span>{{ copy.accountCardId }}</span>
                      <strong>{{ card.subtitle }}</strong>
                    </div>
                    <div class="account-card-stat">
                      <span>{{ copy.accountCardCurrency }}</span>
                      <strong>{{ card.currency }}</strong>
                    </div>
                    <div class="account-card-stat">
                      <span>{{ copy.accountCardTimezone }}</span>
                      <strong>{{ card.timezone }}</strong>
                    </div>
                  </div>

                  <button
                    type="button"
                    class="primary-button compact account-card-action"
                    :disabled="selectedProvider === group.provider && selectedAccountId === card.id"
                    @click="selectAccount(group.provider, card.id)"
                  >
                    {{
                      selectedProvider === group.provider && selectedAccountId === card.id
                        ? copy.accountsPageSelected
                        : copy.accountsPageSelect
                    }}
                  </button>
                </article>
              </div>
            </article>
          </section>
        </template>

        <section v-else-if="!hasAnyConnectedAccounts" class="empty-surface">
          <p class="eyebrow">{{ copy.accounts }}</p>
          <h2>{{ copy.noAccountsTitle }}</h2>
          <p>{{ copy.noAccountsBody }}</p>
          <div class="empty-surface-actions">
            <button type="button" class="primary-button" @click="openConnectModal()">
              {{ copy.manageConnections }}
            </button>
          </div>
        </section>

        <section v-else-if="!currentProviderHasAccounts" class="empty-surface">
          <p class="eyebrow">{{ currentProviderOption.label }}</p>
          <h2>{{ copy.accountSwitcherEmpty }}</h2>
          <p>{{ currentProviderEmptyMessage }}</p>
          <div class="empty-surface-actions">
            <button type="button" class="primary-button" @click="connectCurrentProvider">
              {{
                selectedProvider === 'google_ads'
                  ? copy.connectGoogle
                  : selectedProvider === 'tiktok_ads'
                    ? copy.connectTikTok
                    : copy.connectMeta
              }}
            </button>
          </div>
        </section>

        <section v-else-if="reportLoading && !report" class="empty-surface">
          <p class="eyebrow">{{ currentProviderOption.label }}</p>
          <h2>{{ copy.loadingReport }}</h2>
        </section>

        <template v-else-if="report">
          <template v-if="workspaceMode === 'overview'">
            <section class="hero-strip dashboard-hero reference-hero">
              <div class="reference-heading">
                <div class="reference-kicker">
                  <span class="reference-kicker-bar"></span>
                  <p class="eyebrow">{{ currentProviderOption.label }} · {{ currentProviderOption.subtitle }}</p>
                </div>
                <h2>{{ copy.overviewAccount }}</h2>
                <p class="muted">
                  {{ copy.overviewLead }}
                  <span>
                    · {{ report.periods.current.since }} - {{ report.periods.current.until }}
                  </span>
                  <span v-if="report.account.timezone_name"> · {{ report.account.timezone_name }}</span>
                </p>
              </div>

              <div class="hero-actions hero-actions-stack reference-hero-actions">
                <div class="range-grid range-grid-inline">
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
                <button type="button" class="ghost-button" :disabled="reportLoading" @click="loadReport({ forceRefresh: true })">
                  {{ copy.refreshData }}
                </button>
              </div>
            </section>

            <section class="ai-surface verdict-surface reference-surface reference-verdict-surface">
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
                <article
                  v-for="(block, index) in visibleAutoVerdictBlocks"
                  :key="`overview-verdict-${index}`"
                  class="verdict-message"
                >
                  <div class="verdict-text markdown-body" v-html="renderMarkdown(block)"></div>
                </article>
                <article v-if="visibleAutoVerdictBlocks.length === 0" class="verdict-message verdict-message-empty">
                  <div class="verdict-text markdown-body">—</div>
                </article>
                <button
                  v-if="hasCollapsedAutoVerdict"
                  type="button"
                  class="ghost-button compact-button verdict-toggle"
                  @click="autoVerdictExpanded = !autoVerdictExpanded"
                >
                  {{ autoVerdictExpanded ? copy.hideVerdictDetails : copy.showVerdictDetails }}
                </button>
              </div>
            </section>

            <section class="metric-grid reference-metric-grid">
              <article v-for="item in overviewMetrics" :key="item.key" class="metric-tile surface-metric-card">
                <div class="surface-metric-head">
                  <p>{{ item.label }}</p>
                  <small class="surface-delta-pill" :class="item.deltaTone">{{ item.deltaLabel }}</small>
                </div>
                <strong>{{ item.value }}</strong>
                <div class="surface-metric-foot">
                  <span>{{ metricSurfaceHint(item.key, report.summary.metrics[item.key].delta_pct) }}</span>
                  <small>{{ item.subtitle }}</small>
                </div>
              </article>
            </section>

            <section class="reference-surface trend-surface">
              <div class="trend-surface-head">
                <div>
                  <h3>{{ copy.trendTitle }}</h3>
                  <p>{{ copy.trendLead }}</p>
                </div>
                <div class="trend-legend">
                  <span>
                    <i class="trend-legend-swatch spend"></i>
                    {{ copy.metricCopy.spend[0] }}
                  </span>
                  <span>
                    <i class="trend-legend-swatch results"></i>
                    {{ overviewTrendResultLabel }}
                  </span>
                </div>
              </div>

              <div v-if="overviewTrendChart.hasData" class="trend-chart-shell">
                <svg class="trend-chart" viewBox="0 0 760 320" preserveAspectRatio="none" aria-hidden="true">
                  <g v-for="(line, index) in overviewTrendChart.gridLines" :key="`trend-grid-${index}`">
                    <line x1="52" :x2="760 - 52" :y1="line.y" :y2="line.y" class="trend-grid-line" />
                    <text x="10" :y="line.y + 4" class="trend-axis-label">{{ line.spendLabel }}</text>
                    <text x="750" :y="line.y + 4" text-anchor="end" class="trend-axis-label">{{ line.resultsLabel }}</text>
                  </g>

                  <path :d="overviewTrendChart.spendArea" class="trend-area trend-area-spend"></path>
                  <path :d="overviewTrendChart.resultsArea" class="trend-area trend-area-results"></path>
                  <path :d="overviewTrendChart.spendLine" class="trend-line trend-line-spend"></path>
                  <path :d="overviewTrendChart.resultsLine" class="trend-line trend-line-results"></path>

                  <g v-for="point in overviewTrendChart.points" :key="`trend-point-${point.date}`">
                    <circle :cx="point.x" :cy="point.spendY" r="4" class="trend-point trend-point-spend"></circle>
                    <circle :cx="point.x" :cy="point.resultsY" r="4" class="trend-point trend-point-results"></circle>
                  </g>

                  <g v-for="tick in overviewTrendChart.ticks" :key="`trend-tick-${tick.x}`">
                    <text :x="tick.x" y="306" text-anchor="middle" class="trend-tick-label">{{ tick.label }}</text>
                  </g>
                </svg>
              </div>
              <p v-else class="empty-note">{{ copy.trendEmpty }}</p>
            </section>

            <section class="summary-band reference-summary-band">
              <div class="summary-chip">
                <span>{{ copy.activeCampaigns }}</span>
                <strong>{{ report.summary.active_campaigns ?? 0 }}</strong>
              </div>
              <div class="summary-chip">
                <span>{{ copy.totalCampaigns }}</span>
                <strong>{{ report.summary.total_campaigns ?? 0 }}</strong>
              </div>
              <div class="summary-chip">
                <span>{{ resultKindLabel(report.summary.primary_result_kind || 'result') }}</span>
                <strong>{{ formatCompactNumber(report.summary.metrics.results.current) }}</strong>
              </div>
            </section>

            <section class="compare-strip reference-compare-strip">
              <p class="eyebrow">{{ copy.periodCompare }}</p>
              <p>
                {{ report.periods.previous.since }} - {{ report.periods.previous.until }}
                <span>vs</span>
                {{ report.periods.current.since }} - {{ report.periods.current.until }}
              </p>
            </section>

            <section class="list-surface reference-surface campaign-list-surface">
              <div class="focus-head">
                <div>
                  <p class="eyebrow">{{ copy.campaigns }}</p>
                  <h3>{{ report.account.name }}</h3>
                </div>
              </div>

              <div v-if="report.campaigns.length === 0" class="empty-note">
                {{ copy.emptyCampaigns }}
              </div>
              <div v-else class="campaign-list">
                <button
                  v-for="campaign in report.campaigns"
                  :key="campaign.id"
                  type="button"
                  class="campaign-row"
                  @click="selectCampaign(campaign.id)"
                >
                  <div class="campaign-row-main">
                    <i class="status-dot" :class="statusTone(campaign.status)"></i>
                    <div>
                      <strong>{{ campaign.name }}</strong>
                      <small>{{ resultKindLabel(campaign.primary_result_kind || 'result') }}</small>
                    </div>
                  </div>
                  <div class="campaign-row-metrics">
                    <span>{{ formatMetricValue('spend', campaign.metrics.spend.current) }}</span>
                    <span>{{ formatMetricValue('ctr', campaign.metrics.ctr.current) }}</span>
                    <span>{{ formatMetricValue('results', campaign.metrics.results.current) }}</span>
                  </div>
                </button>
              </div>
            </section>
          </template>

          <template v-else-if="selectedCampaign">
            <button type="button" class="back-link" @click="openOverview">
              <svg class="back-link-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              {{ copy.overviewAccount }}
            </button>

            <section class="hero-strip campaign-hero reference-hero">
              <div class="reference-heading">
                <div class="reference-kicker">
                  <span class="reference-kicker-bar"></span>
                  <p class="eyebrow">{{ copy.campaigns }} · {{ resultKindLabel(selectedCampaign.primary_result_kind || 'result') }}</p>
                </div>
                <div class="campaign-hero-row">
                  <h2>{{ selectedCampaign.name }}</h2>
                  <div class="status-badge" :class="statusTone(selectedCampaign.status)">
                    <i class="status-dot" :class="statusTone(selectedCampaign.status)"></i>
                    {{ statusLabel(selectedCampaign.status) }}
                  </div>
                </div>
                <p class="muted">
                  {{ report.account.name }}
                  <span> · {{ report.periods.current.since }} - {{ report.periods.current.until }}</span>
                  <span> · {{ copy.creativeFocus }}: {{ selectedCampaign.creatives.length }}</span>
                </p>
              </div>
            </section>

            <section class="ai-surface verdict-surface reference-surface reference-verdict-surface">
              <div class="section-head">
                <div class="verdict-title">
                  <span>{{ copy.aiVerdict }}</span>
                  <div class="info-tooltip">
                    <button
                      type="button"
                      class="info-tooltip-trigger"
                      :aria-label="copy.aiVerdictInfoLabel"
                      aria-describedby="campaign-ai-verdict-tooltip"
                    >
                      i
                    </button>
                    <span id="campaign-ai-verdict-tooltip" class="info-tooltip-panel" role="tooltip">{{ copy.aiVerdictHint }}</span>
                  </div>
                </div>
              </div>
              <p v-if="verdictLoading" class="empty-note">{{ copy.loadingVerdict }}</p>
              <div v-else class="verdict-body">
                <article
                  v-for="(block, index) in visibleAutoVerdictBlocks"
                  :key="`campaign-verdict-${index}`"
                  class="verdict-message"
                >
                  <div class="verdict-text markdown-body" v-html="renderMarkdown(block)"></div>
                </article>
                <article v-if="visibleAutoVerdictBlocks.length === 0" class="verdict-message verdict-message-empty">
                  <div class="verdict-text markdown-body">—</div>
                </article>
                <button
                  v-if="hasCollapsedAutoVerdict"
                  type="button"
                  class="ghost-button compact-button verdict-toggle"
                  @click="autoVerdictExpanded = !autoVerdictExpanded"
                >
                  {{ autoVerdictExpanded ? copy.hideVerdictDetails : copy.showVerdictDetails }}
                </button>
              </div>
            </section>

            <section class="campaign-summary-stack">
              <div class="focus-head reference-section-head">
                <div class="reference-kicker">
                  <span class="reference-kicker-bar"></span>
                  <p class="eyebrow">{{ copy.campaignMetricsTitle }}</p>
                </div>
              </div>

              <div class="metric-grid reference-metric-grid">
                <article v-for="item in campaignSummaryMetrics" :key="item.key" class="metric-tile surface-metric-card">
                  <div class="surface-metric-head">
                    <p>{{ item.label }}</p>
                    <small class="surface-delta-pill" :class="item.deltaTone">{{ item.deltaLabel }}</small>
                  </div>
                  <strong>{{ item.value }}</strong>
                  <div class="surface-metric-foot">
                    <span>{{ metricSurfaceHint(item.key, selectedCampaign.metrics[item.key].delta_pct) }}</span>
                    <small>{{ item.subtitle }}</small>
                  </div>
                </article>
              </div>
            </section>

            <section class="focus-surface reference-surface campaign-creatives-surface">
              <div class="section-head">
                <div class="reference-kicker">
                  <span class="reference-kicker-bar"></span>
                  <p class="eyebrow">{{ copy.campaignCreativesTitle }}</p>
                </div>
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
            </section>
          </template>

          <section v-else class="empty-surface">
            <p class="eyebrow">{{ currentProviderOption.label }}</p>
            <h2>{{ copy.overviewAccount }}</h2>
            <p>{{ copy.emptyCampaigns }}</p>
            <div class="empty-surface-actions">
              <button type="button" class="ghost-button" @click="openOverview">
                {{ copy.sidebarOverview }}
              </button>
            </div>
          </section>
        </template>

        <section v-else class="empty-surface">
          <p class="eyebrow">{{ currentProviderOption.label }}</p>
          <h2>{{ copy.loadingReport }}</h2>
        </section>
      </section>

      <div v-if="aiPanelOpen && isAiOverlay" class="ai-overlay" @click="closeAiPanel"></div>

      <button v-if="!aiPanelOpen" type="button" class="ai-fab" :aria-label="copy.askAi" @click="openAiPanel">
        <svg class="ai-fab-icon" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
        </svg>
      </button>

      <div v-if="connectModalOpen" class="connect-modal-root">
        <div class="connect-modal-backdrop" @click="closeConnectModal"></div>
        <section class="connect-modal" role="dialog" :aria-label="copy.accountsPageTitle">
          <div class="connect-modal-head">
            <div>
              <p class="eyebrow">{{ copy.sidebarAccounts }}</p>
              <h3>{{ copy.manageConnections }}</h3>
            </div>
            <button type="button" class="ghost-button compact-button" @click="closeConnectModal">
              {{ copy.backToApp }}
            </button>
          </div>

          <p class="surface-note connect-modal-note">{{ copy.accountsPageLead }}</p>

          <div class="connect-modal-grid">
            <article
              v-for="providerOption in connectModalProviders"
              :key="providerOption.key"
              class="connect-provider-card"
              :class="providerOption.key"
            >
              <div class="connect-provider-head">
                <span class="platform-badge" :class="providerOption.key">
                  {{ providerGlyph(providerOption.key) }}
                </span>
                <div class="connect-provider-copy">
                  <strong>{{ providerOption.label }}</strong>
                  <small>{{ providerOption.subtitle }}</small>
                </div>
                <span class="settings-badge">{{ providerOption.count }}</span>
              </div>

              <p class="surface-note">
                {{
                  providerOption.key === 'google_ads'
                    ? copy.googleAccountsEmpty
                    : providerOption.key === 'tiktok_ads'
                      ? copy.tiktokAccountsEmpty
                      : copy.noAccountsBody
                }}
              </p>

              <button
                type="button"
                class="primary-button compact connect-provider-action"
                :disabled="providerIsConnecting(providerOption.key)"
                @click="connectFromModal(providerOption.key)"
              >
                {{ providerConnectLabel(providerOption.key) }}
              </button>
            </article>
          </div>
        </section>
      </div>

      <aside v-if="aiPanelOpen" class="rail rail-right ai-panel" :class="{ overlay: isAiOverlay }">
        <header class="ai-panel-header">
          <div class="ai-panel-title">
            <span class="ai-panel-icon-wrap">
              <svg class="ai-panel-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
              </svg>
            </span>
            <div>
              <strong>{{ copy.aiConsultant }}</strong>
              <small>{{ copy.aiConsultantOnline }}</small>
            </div>
          </div>
          <button type="button" class="ai-panel-close" :aria-label="copy.askAi" @click="closeAiPanel">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </header>

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
