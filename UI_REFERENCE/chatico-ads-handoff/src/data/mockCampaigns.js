/** Mock-кампании Meta Ads (до подключения API, M11) */
export const MOCK_CAMPAIGNS = [
  {
    id: 'camp_001',
    name: 'Лиды · WhatsApp · Алматы · Март 2026',
    status: 'active',
  },
  {
    id: 'camp_002',
    name: 'Продажи · Instagram Reels · женская аудитория 25–45',
    status: 'active',
  },
  {
    id: 'camp_003',
    name: 'Трафик на сайт · Facebook Feed · ретаргетинг посетителей',
    status: 'active',
  },
  {
    id: 'camp_004',
    name: 'Сообщения · Messenger · акция «Скидка 20%» до конца месяца',
    status: 'paused',
  },
  {
    id: 'camp_005',
    name: 'Охват · Stories · новый продукт · тест креативов A/B/C',
    status: 'active',
  },
  {
    id: 'camp_006',
    name: 'Лиды · Lead Form · B2B · директора и собственники бизнеса',
    status: 'active',
  },
  {
    id: 'camp_007',
    name: 'Конверсии · Catalog Sales · интернет-магазин · все города KZ',
    status: 'paused',
  },
];

export function getCampaignById(id) {
  return MOCK_CAMPAIGNS.find((c) => c.id === id);
}

/** Короткий helper для метрики в формате карточки обзора */
const metric = (value, pct, isPositive, subtitle) => ({
  value,
  trend: { value: pct, isPositive },
  subtitle,
});

/**
 * Детальные mock-данные по кампаниям (M5/M6).
 * Структура: метрики (как в обзоре) → вердикт → группы объявлений → объявления.
 * Цель кампании определяет, как называется главный результат (диалоги/заявки/продажи/...).
 */
const CAMPAIGN_DETAILS = {
  camp_001: {
    objective: 'Сообщения',
    resultLabel: 'Диалоги',
    metrics: {
      spent: metric('92 400 ₸', '9%', false, 'Потрачено за период'),
      leads: metric('243 диалога', '15%', true, 'Начали диалог в WhatsApp'),
      cpl: metric('380 ₸', '6%', true, 'Цена за диалог'),
      impressions: metric('18 900 раз', '4%', true, 'Показы объявлений'),
    },
    verdict: {
      status: 'good',
      text: 'Кампания на Алматы — ваш лидер. Цена за диалог снизилась на 6%, а объём обращений вырос на 15%. Группа «Тёплая аудитория» работает заметно дешевле остальных — на неё стоит добавить бюджет.',
    },
    adSets: [
      {
        id: 'as_001',
        name: 'Тёплая аудитория · похожие на клиентов',
        targeting: { gender: 'Все', age: '25–45', city: 'Алматы' },
        ads: [
          { id: 'ad_0011', name: 'Видео-отзыв клиента · 15 сек', spent: 24000, leads: 78, cpl: 308 },
          { id: 'ad_0012', name: 'Карусель «До / После»', spent: 18000, leads: 49, cpl: 367 },
          { id: 'ad_0013', name: 'Статичный баннер · оффер дня', spent: 15000, leads: 36, cpl: 417 },
          { id: 'ad_0014', name: 'Фото товара · крупный план', spent: 12000, leads: 22, cpl: 545 },
        ],
      },
      {
        id: 'as_002',
        name: 'Широкая аудитория · интересы',
        targeting: { gender: 'Все', age: '18–35', city: 'Алматы · Астана' },
        ads: [
          { id: 'ad_0021', name: 'Reels · динамика распаковки', spent: 23400, leads: 58, cpl: 403 },
        ],
      },
    ],
  },
  camp_002: {
    objective: 'Продажи',
    resultLabel: 'Продажи',
    metrics: {
      spent: metric('118 700 ₸', '12%', true, 'Потрачено за период'),
      leads: metric('164 продажи', '20%', true, 'Оформили заказ'),
      cpl: metric('724 ₸', '4%', false, 'Цена за продажу'),
      impressions: metric('51 200 раз', '9%', true, 'Показы объявлений'),
    },
    verdict: {
      status: 'warning',
      text: 'Продаж стало больше на 20%, но цена за продажу подросла на 4%. Креативы в Reels начинают примелькаться аудитории — рекомендуем обновить видео, чтобы удержать стоимость.',
    },
    adSets: [
      {
        id: 'as_021',
        name: 'Reels · женщины 25–45',
        targeting: { gender: 'Женщины', age: '25–45', city: 'Вся РК' },
        ads: [
          { id: 'ad_0211', name: 'Reels · образ «весна»', spent: 41000, leads: 64, cpl: 641 },
          { id: 'ad_0212', name: 'Reels · отзыв + промокод', spent: 38000, leads: 52, cpl: 731 },
          { id: 'ad_0213', name: 'Карусель · новая коллекция', spent: 39700, leads: 48, cpl: 827 },
        ],
      },
      {
        id: 'as_022',
        name: 'Ретаргетинг · смотрели товар',
        targeting: { gender: 'Женщины', age: '25–45', city: 'Алматы' },
        ads: [
          { id: 'ad_0221', name: 'Напоминание · брошенная корзина', spent: 0, leads: 0, cpl: 0 },
        ],
      },
    ],
  },
  camp_003: {
    objective: 'Трафик',
    resultLabel: 'Переходы',
    metrics: {
      spent: metric('43 800 ₸', '3%', true, 'Потрачено за период'),
      leads: metric('1 240 переходов', '11%', true, 'Перешли на сайт'),
      cpl: metric('35 ₸', '7%', true, 'Цена за переход'),
      impressions: metric('72 400 раз', '6%', true, 'Показы объявлений'),
    },
    verdict: {
      status: 'good',
      text: 'Ретаргетинг приводит дешёвый трафик: переход стоит всего 35 ₸ и подешевел на 7%. Аудитория «посетители сайта» реагирует лучше всего — связка работает стабильно.',
    },
    adSets: [
      {
        id: 'as_031',
        name: 'Ретаргетинг · посетители за 30 дней',
        targeting: { gender: 'Все', age: '18–55', city: 'Вся РК' },
        ads: [
          { id: 'ad_0311', name: 'Баннер · «Вернись за скидкой»', spent: 16000, leads: 520, cpl: 31 },
          { id: 'ad_0312', name: 'Карусель · популярные товары', spent: 15800, leads: 430, cpl: 37 },
          { id: 'ad_0313', name: 'Видео · обзор каталога', spent: 12000, leads: 290, cpl: 41 },
        ],
      },
    ],
  },
  camp_004: {
    objective: 'Сообщения',
    resultLabel: 'Диалоги',
    metrics: {
      spent: metric('61 500 ₸', '5%', false, 'Потрачено за период'),
      leads: metric('128 диалогов', '8%', false, 'Написали в Messenger'),
      cpl: metric('480 ₸', '10%', false, 'Цена за диалог'),
      impressions: metric('27 300 раз', '12%', false, 'Показы объявлений'),
    },
    verdict: {
      status: 'warning',
      text: 'Кампания на паузе, поэтому показатели снижаются. Перед перезапуском обновите оффер: акция «Скидка 20%» заканчивается, и старое сообщение уже не цепляет аудиторию.',
    },
    adSets: [
      {
        id: 'as_041',
        name: 'Акция · широкая аудитория',
        targeting: { gender: 'Все', age: '20–50', city: 'Алматы · Астана · Шымкент' },
        ads: [
          { id: 'ad_0411', name: 'Баннер · «Скидка 20%»', spent: 22000, leads: 52, cpl: 423 },
          { id: 'ad_0412', name: 'Видео · условия акции', spent: 19500, leads: 41, cpl: 476 },
        ],
      },
      {
        id: 'as_042',
        name: 'Lookalike · похожие на писавших',
        targeting: { gender: 'Все', age: '25–45', city: 'Алматы' },
        ads: [
          { id: 'ad_0421', name: 'Карусель · хиты со скидкой', spent: 20000, leads: 35, cpl: 571 },
        ],
      },
    ],
  },
  camp_005: {
    objective: 'Охват',
    resultLabel: 'Охват',
    metrics: {
      spent: metric('38 200 ₸', '2%', true, 'Потрачено за период'),
      leads: metric('96 400 человек', '18%', true, 'Уникальный охват'),
      cpl: metric('0,40 ₸', '5%', true, 'Цена за охват 1 чел.'),
      impressions: metric('142 000 раз', '15%', true, 'Показы объявлений'),
    },
    verdict: {
      status: 'good',
      text: 'Тест креативов A/B/C идёт успешно: вариант A даёт самый широкий охват при минимальной цене. Рекомендуем оставить вариант A и отключить отстающий вариант C.',
    },
    adSets: [
      {
        id: 'as_051',
        name: 'A/B/C тест · новый продукт',
        targeting: { gender: 'Все', age: '18–40', city: 'Вся РК' },
        ads: [
          { id: 'ad_0511', name: 'Вариант A · Stories вертикаль', spent: 14000, leads: 42000, cpl: 0.33 },
          { id: 'ad_0512', name: 'Вариант B · статика', spent: 13000, leads: 34000, cpl: 0.38 },
          { id: 'ad_0513', name: 'Вариант C · текст-оверлей', spent: 11200, leads: 20400, cpl: 0.55 },
        ],
      },
    ],
  },
  camp_006: {
    objective: 'Лиды',
    resultLabel: 'Заявки',
    metrics: {
      spent: metric('134 000 ₸', '14%', true, 'Потрачено за период'),
      leads: metric('208 заявок', '9%', true, 'Оставили заявку (Lead Form)'),
      cpl: metric('644 ₸', '3%', false, 'Цена за заявку'),
      impressions: metric('39 800 раз', '7%', true, 'Показы объявлений'),
    },
    verdict: {
      status: 'warning',
      text: 'B2B-аудитория приносит качественные заявки, но они дороже на 3%. Группа «Собственники бизнеса» окупается лучше — стоит сместить бюджет в её пользу и протестировать новый лид-магнит.',
    },
    adSets: [
      {
        id: 'as_061',
        name: 'Директора · крупный бизнес',
        targeting: { gender: 'Все', age: '30–55', city: 'Алматы · Астана' },
        ads: [
          { id: 'ad_0611', name: 'Лид-форма · бесплатный аудит', spent: 36000, leads: 58, cpl: 621 },
          { id: 'ad_0612', name: 'Кейс · рост продаж клиента', spent: 31000, leads: 44, cpl: 705 },
        ],
      },
      {
        id: 'as_062',
        name: 'Собственники бизнеса · интересы',
        targeting: { gender: 'Мужчины', age: '28–50', city: 'Вся РК' },
        ads: [
          { id: 'ad_0621', name: 'Лид-форма · чек-лист для бизнеса', spent: 20000, leads: 41, cpl: 488 },
          { id: 'ad_0622', name: 'Видео · приглашение на вебинар', spent: 18000, leads: 28, cpl: 643 },
          { id: 'ad_0623', name: 'Карусель · тарифы и выгода', spent: 16000, leads: 22, cpl: 727 },
          { id: 'ad_0624', name: 'Статика · оффер «первый месяц»', spent: 13000, leads: 15, cpl: 867 },
        ],
      },
    ],
  },
  camp_007: {
    objective: 'Конверсии',
    resultLabel: 'Продажи',
    metrics: {
      spent: metric('57 900 ₸', '6%', false, 'Потрачено за период'),
      leads: metric('89 продаж', '11%', false, 'Покупки из каталога'),
      cpl: metric('650 ₸', '7%', false, 'Цена за продажу'),
      impressions: metric('33 100 раз', '9%', false, 'Показы объявлений'),
    },
    verdict: {
      status: 'warning',
      text: 'Кампания на паузе. Динамический каталог показывал хорошую цену продажи — перед перезапуском проверьте актуальность товарного фида и обновите обложки популярных позиций.',
    },
    adSets: [
      {
        id: 'as_071',
        name: 'Динамический каталог · вся РК',
        targeting: { gender: 'Все', age: '20–50', city: 'Вся РК' },
        ads: [
          { id: 'ad_0711', name: 'Catalog Sales · авто-карусель', spent: 57900, leads: 89, cpl: 650 },
        ],
      },
    ],
  },
};

/** Возвращает кампанию из списка, обогащённую детальными mock-данными. */
export function getCampaignDetail(id) {
  const base = getCampaignById(id);
  if (!base) return null;
  const details = CAMPAIGN_DETAILS[id];
  return details ? { ...base, ...details } : base;
}
