# MODULES.md — Модули интерфейса Chatico ADS

> Разбивка по `ARCHITECTURE.md`. Каждый модуль — отдельный шаг разработки.  
> Статус обновляется в `CURRENT_STATUS.md`.

---

## Карта модулей

| ID | Модуль | Компоненты / файлы | Зависит от | Статус |
|---|---|---|---|---|
| **M0** | Foundation | Vite, Tailwind, design tokens, Zustand, React Query, структура `src/` | — | ✅ Готово |
| **M1** | Layout | `Sidebar`, `Topbar`, `ProtectedRoute`, роутинг, shell | M0 | ✅ Готово |
| **M2** | UI Primitives | `MetricCard`, `TrendBadge`, `Skeleton`, `EmptyState` | M0 | ✅ Готово |
| **M3** | Auth | `LoginPage`, `LoginForm`, `RegisterForm` | M1, M2 | ⬜ |
| **M4** | Overview | `DashboardPage`, `PeriodSwitcher`, `KeyMetricsRow`, `VerdictCard`, `TrendChart` | M1, M2 | ✅ Готово |
| **M5** | Campaigns | `CampaignDetailPage`, `CampaignSummary`, `AdSetList`, `AdSetRow`, `TargetingLine` | M1, M2, M4 | ✅ Готово |
| **M6** | Ads | `AdCard`, `AdList` (условный рендер + «показать ещё») | M5 | 🟡 Частично |
| **M7** | AI Panel | `AIPanel`, `ChatWindow`, `ChatMessage`, `SuggestedChips`, `ChatInput` | M1, M2 | ✅ Готово |
| **M8** | Accounts | `AccountsPage`, `AccountSwitcher`, `ConnectAccountModal`, `AccountAvatar` | M1, M2 | ✅ Готово |
| **M9** | Platforms | `ComingSoonPlaceholder` (Google, TikTok) | M1 | 🟡 Частично |
| **M10** | Settings | `SettingsPage` | M1, M2 | ⬜ |
| **M11** | API + Mocks | `api/*`, mock-данные для UI | M0 | ⬜ |
| **M12** | Polish | Адаптив, финальная полировка, деплой | все | ⬜ |

---

## M0 — Foundation

**Цель:** каркас приложения, дизайн-токены из `DESIGN_SYSTEM.md`, глобальный стейт.

**Файлы:**
- `package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`
- `index.html` — Montserrat из Google Fonts
- `src/main.jsx`, `src/App.jsx`
- `src/index.css` — CSS-переменные бренда
- `src/store/useAppStore.js` — platform, account, user, token
- `.env.example`

**Критерий готовности:** `npm install && npm run dev` поднимает пустое приложение с брендовыми цветами.

---

## M1 — Layout

**Цель:** оболочка дашборда — навигация, платформы, защищённые маршруты.

**Файлы:**
- `src/components/layout/Sidebar.jsx` — Meta / Google / TikTok
- `src/components/layout/Topbar.jsx` — лого `chatico` + `ads`, аккаунт
- `src/components/layout/ProtectedRoute.jsx`
- `src/components/layout/AppLayout.jsx`
- `src/components/platforms/ComingSoonPlaceholder.jsx`
- Роуты: `/`, `/campaigns/:id`, `/accounts`, `/settings`, `/login`

**Критерий готовности:** переключение платформ в Sidebar; Meta — дашборд, Google/TikTok — заглушка.

---

## M2 — UI Primitives

**Цель:** переиспользуемые атомарные компоненты.

**Файлы:** `src/components/ui/*`

**Критерий готовности:** Storybook не нужен; компоненты используются в M4+.

---

## M3 — Auth

**Цель:** вход и регистрация (UI; API — mock до бэкенда).

---

## M4 — Overview

**Цель:** главный экран дашборда по аккаунту Meta.

**Иерархия:** PeriodSwitcher → VerdictCard → KeyMetricsRow → TrendChart → CampaignList → AIPanel (заглушка до M7).

---

## M5 — Campaigns

**Цель:** список кампаний и страница детализации.

**Маршрут:** `/campaigns/:id`

---

## M6 — Ads

**Цель:** объявления внутри группы — условный рендер (1 / 2–3 / 4+).

---

## M7 — AI Panel

**Цель:** VerdictCard (текст) + чат с SuggestedChips и правилом `hasInteracted`.

---

## M8 — Accounts

**Цель:** подключение и переключение рекламных аккаунтов.

---

## M9 — Platforms

**Цель:** заглушки Google Ads и TikTok Ads в Sidebar.

---

## M10 — Settings

**Цель:** страница настроек пользователя.

---

## M11 — API + Mocks

**Цель:** слой `src/api/*` и mock-данные для разработки без бэкенда.

---

## M12 — Polish

**Цель:** адаптивность, accessibility, деплой.

---

## Порядок работы

```
M0 → M1 → M2 → M11 (mocks параллельно M4)
         ↓
    M3, M4, M8, M9, M10 (можно параллельно после M2)
         ↓
    M5 → M6
         ↓
    M7 → M12
```

**Текущий шаг:** M2 — UI Primitives.
