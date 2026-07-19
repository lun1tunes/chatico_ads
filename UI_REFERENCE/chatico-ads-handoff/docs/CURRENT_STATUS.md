# CURRENT_STATUS.md — Chatico ADS

> Обновлено: 24 июня 2026 · Редизайн блоков дашборда в стиле shadcn/ui (v0.8.0)

## Общий статус

**Стадия:** разработка фронтенда — модульная проработка  
**Хранение:** локально на компьютере (`~/Projects/chatico-ads/`)  
**Git / GitHub:** не подключены  
**Текущий модуль:** M13 — i18n (языки RU/KAZ/ENG) / M3 — Auth (следующие)

---

## Прогресс модулей

| ID | Модуль | Статус | Комментарий |
|---|---|---|---|
| M0 | Foundation | ✅ Готово | Vite, Tailwind, tokens, Zustand, React Query |
| M1 | Layout | ✅ Готово | Сворачиваемый Sidebar, выпадающий селектор Платформ (Инструмент) |
| M2 | UI Primitives | ✅ Готово | MetricCard, TrendBadge, Skeleton, EmptyState |
| M3 | Auth | ⬜ | LoginForm, RegisterForm (демо-вход есть) |
| M4 | Overview | ✅ Готово | DashboardPage — редизайн в стиле меню: индиго-вердикт, карточки с иконками, график, период |
| M5 | Campaigns | ✅ Готово | Страница кампании: шапка+статус, вердикт, сводка, группы объявлений |
| M6 | Ads | 🟡 Частично | AdCard, AdList с условным рендером (1/2-3/4+), бейдж лидера |
| M7 | AI Panel | ✅ Готово | Закреплённый чат-консультант (3 колонки) + overlay на узких, подсказки, mock-ответы |
| M8 | Accounts | ✅ Готово | Переключатель в топбаре, страница кабинетов, подключение (mock Facebook) |
| M9 | Platforms | ✅ Готово | Интеграция с селектором, ComingSoonPlaceholder для Google/TikTok |
| M10 | Settings | ⬜ | Страница-заглушка создана |
| M11 | API + Mocks | 🟡 Частично | `mockCampaigns.js`, `mockMetrics.js`, `mockAccounts.js`, `mockAiResponses.js`; `src/api/*` — позже |
| M12 | Polish | ⬜ | Адаптив, деплой |
| M13 | i18n | ⬜ Запланирован | Переключатель RU/KAZ/ENG + react-i18next, перевод UI-надписей |

Подробности — `docs/MODULES.md`.

---

## Что уже сделано

| Область | Статус | Комментарий |
|---|---|---|
| Описание продукта | ✅ Готово | `docs/PROJECT_OVERVIEW.md` |
| Архитектура фронтенда | ✅ Готово | `docs/ARCHITECTURE.md` |
| Разбивка на модули | ✅ Готово | `docs/MODULES.md` |
| Технологический стек | ✅ Зафиксирован | `docs/TECH_STACK.md` |
| Дизайн-система | ✅ Готово | `docs/DESIGN_SYSTEM.md` |
| История изменений | ✅ Готово | `docs/CHANGELOG.md` — фиксация версий проекта |
| Логотип проекта | ✅ Готово | `public/logo-chatico-ads.png`, компонент `Logo.jsx` |
| Каркас React (M0) | ✅ Готово | `package.json`, Tailwind, Zustand |
| Layout (M1) | ✅ Готово | Sidebar (свернутый/развернутый, селектор платформ, фирменный индиго-стиль), Topbar, роуты, платформы |
| Лендинг (лид-форма) | 🟡 В тесте | HTML в `~/Downloads/` |
| Прототипы UI | 🟡 Есть черновики | `chatico_src/` в Downloads |
| Бэкенд / API | ⬜ Отдельная команда | `API_CONTRACT.md` — в планах |
| AI-правила языка | ⬜ Не создано | `AI_LANGUAGE_RULES.md` — в планах |

---

## Структура проекта (актуальная)

```
chatico-ads/
├── docs/           ← документация (6 файлов + MODULES.md)
├── public/         ← статические ресурсы (логотип)
├── src/
│   ├── components/
│   │   ├── layout/     ✅ M1 (Sidebar, Topbar, ProtectedRoute)
│   │   ├── overview/   ✅ M4 (PeriodSwitcher, KeyMetricsRow, VerdictCard, TrendChart)
│   │   ├── campaigns/  ✅ M5 (CampaignSummary, AdSetList, AdSetRow, TargetingLine)
│   │   ├── ads/        🟡 M6 (AdCard, AdList, CreativePreview)
│   │   ├── ai/         ✅ M7 (AIPanel, ChatWindow, ChatMessage, SuggestedChips, ChatInput)
│   │   ├── accounts/   ✅ M8 (AccountSwitcher, ConnectAccountModal, AccountAvatar)
│   │   ├── platforms/  🟡 M9 (ComingSoonPlaceholder)
│   │   └── ui/         ✅ M2 (Logo, MetricCard, TrendBadge, Skeleton, EmptyState)
│   ├── data/           ✅ M11 (mockCampaigns, mockMetrics, mockAccounts, mockAiResponses)
│   ├── utils/          ✅ format.js (₸ и числа, RU-локаль)
│   ├── pages/          🟡 (LoginPage, DashboardPage ✅, CampaignDetailPage ✅, AccountsPage, SettingsPage)
│   ├── store/          ✅ M0 (useAppStore)
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── README.md
```

---

## Запуск (локально)

```bash
cd ~/Projects/chatico-ads
npm install
npm run dev
```

---

## MVP — прогресс

| Функция MVP | Статус |
|---|---|
| Подключение Meta Ads | ⬜ Не начато (бэкенд) |
| Отчёт по метрикам (RU/KZ) | ✅ Готово | Интерфейс полностью готов на mock-данных (M4) |
| AI-чат по данным рекламы | ⬜ M7 |
| Лендинг для теста спроса | 🟡 Запущен в тест |

---

## Следующие шаги

1. **M13** — i18n: переключатель языков RU/KAZ/ENG + перевод UI-надписей
2. **M3** — Auth: полноценные формы входа/регистрации
3. **M10** — Settings: страница настроек
4. **M12** — Polish: адаптив под мобильные, доводка, деплой
5. **M6** (доработка) — реальные креативы объявлений после подключения API
6. Перенести лендинги и прототипы из Downloads

---

## Открытые вопросы

- Формат API-ответа по метрикам (ждём бэкенд-команду).
- Какие цели кампаний Meta реально используют клиенты сейчас.
- Сроки и состав бэкенд-команды.
