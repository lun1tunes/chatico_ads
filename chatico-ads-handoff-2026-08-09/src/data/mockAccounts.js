/**
 * Mock рекламных кабинетов (M8).
 * Один пользователь Chatico может вести несколько кабинетов Meta
 * (агентство с разными клиентами, бизнес с несколькими брендами и т.п.).
 */
export const ALL_ACCOUNTS = [
  {
    id: 'acc_001',
    name: 'Мой бизнес',
    handle: '@my.business',
    platform: 'meta',
    currency: 'KZT',
    status: 'active',
    spentMonth: '680 000 ₸',
    leadsMonth: '1 520',
    campaigns: 7,
    accent: '#5E44EB',
  },
  {
    id: 'acc_002',
    name: 'Бутик «Aru»',
    handle: '@aru.store',
    platform: 'meta',
    currency: 'KZT',
    status: 'active',
    spentMonth: '214 500 ₸',
    leadsMonth: '430',
    campaigns: 3,
    accent: '#EC4899',
  },
  {
    id: 'acc_003',
    name: 'Кофейня «Dala»',
    handle: '@dala.coffee',
    platform: 'meta',
    currency: 'KZT',
    status: 'paused',
    spentMonth: '0 ₸',
    leadsMonth: '0',
    campaigns: 2,
    accent: '#F59E0B',
  },
  {
    id: 'acc_004',
    name: 'Автосервис «Турбо»',
    handle: '@turbo.auto',
    platform: 'meta',
    currency: 'KZT',
    status: 'active',
    spentMonth: '95 200 ₸',
    leadsMonth: '88',
    campaigns: 1,
    accent: '#14B8A6',
  },
  {
    id: 'acc_005',
    name: 'Студия маникюра «Lacquer»',
    handle: '@lacquer.nails',
    platform: 'meta',
    currency: 'KZT',
    status: 'active',
    spentMonth: '47 800 ₸',
    leadsMonth: '120',
    campaigns: 2,
    accent: '#6366F1',
  },
];

/** Изначально подключённые кабинеты. */
export const DEFAULT_CONNECTED_IDS = ['acc_001', 'acc_002', 'acc_003'];

export function getAccountById(id) {
  return ALL_ACCOUNTS.find((a) => a.id === id) ?? null;
}

/** Короткие инициалы для аватара кабинета. */
export function accountInitials(name = '') {
  const cleaned = name.replace(/[«»"']/g, '').trim();
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
