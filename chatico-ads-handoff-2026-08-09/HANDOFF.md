# Chatico ADS — передача разработчику

> Снимок: 9 августа 2026

## Запуск

```bash
npm install
npm run dev
```

Открыть: `http://localhost:5173`

## Что изменилось с прошлой версии

### Навигация
- Главная (`/`) — приветствие, выбор кампании в sidebar
- Клик по кампании → `/campaigns/:id` (страница кампании или группы через `?adSet=`)
- Все объявления кампании → `/campaigns/:id/ads` (отдельный маршрут)
- Sidebar: плоский список кампаний, без «Главное» и без сворачивания списка

### Экраны
- **Кампания** — метрики, карточка «Все объявления», список групп
- **Группа** (`?adSet=`) — таргетинг с человекочитаемым описанием аудитории, метрики, объявления
- **Все объявления** (`/ads`) — фильтр по группе слева, период справа, список с превью

### Данные и UI
- Mock с реальными объявлениями (кампания `camp_001`): 3 объявления, USD, превью в `public/creatives/`
- `src/utils/audienceSummary.js` — свёртка FB-таргетинга в 2–3 строки простым языком
- `CreativePreview` — поддержка `thumbnailUrl` (реальное фото) + заглушки по типу
- `formatMoney()` — KZT и USD
- ИИ-вердикт контекстный: кампания / группа / все объявления

### Документы
- `docs/ARCHITECTURE.md` — глоссарий метрик (что не показывать клиенту)
- `MEDIA_RENDERING_RULES.md` — правила отображения медиа в карточках объявлений

## Ключевые файлы

| Файл | Назначение |
|---|---|
| `src/App.jsx` | Роуты |
| `src/pages/CampaignDetailPage.jsx` | Кампания + группа |
| `src/pages/CampaignAdsPage.jsx` | Все объявления |
| `src/components/campaigns/CampaignExplorer.jsx` | Контент кампании/группы |
| `src/components/campaigns/AdPreviewCard.jsx` | Карточка объявления |
| `src/components/ads/CreativePreview.jsx` | Превью креатива |
| `src/data/mockCampaigns.js` | Mock-данные |
| `src/utils/audienceSummary.js` | Описание аудитории |
| `src/utils/aiContext.js` | Контекст для ИИ-панели |

## Не включено в архив

- `node_modules/` — установить через `npm install`
- `.env` — скопировать из `.env.example`
- Git-история

## Следующие шаги для бэкенда

- Подключить Meta Marketing API → заменить mock в `mockCampaigns.js`
- Прокидывать `fbDetails` (interests, behaviors, jobTitles) для `summarizeAudience()`
- Прокидывать `thumbnailUrl` / URL видео для `CreativePreview`
- Реализовать `MEDIA_RENDERING_RULES.md` при финальной вёрстке карточек
