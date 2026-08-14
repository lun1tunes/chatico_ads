/** Presets глобального периода (Этап 1 — до подключения API). */
export const PERIOD_PRESETS = {
  '7d': { label: '7 дней', days: 7 },
  '14d': { label: '14 дней', days: 14 },
  '30d': { label: '30 дней', days: 30 },
  thisMonth: { label: 'Этот месяц' },
  lastMonth: { label: 'Прошлый месяц' },
  custom: { label: 'Выбрать период' },
};

const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

function pad(n) {
  return String(n).padStart(2, '0');
}

/** ISO YYYY-MM-DD из Date (локальная дата). */
export function toISODate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseISODate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

/** Даты для preset относительно «сегодня» (демо: фиксированная база 24.06.2026 для стабильных mock). */
const DEMO_TODAY = new Date(2026, 5, 24);

export function getDemoToday() {
  return DEMO_TODAY;
}

/** Вычисляет from/to для preset. */
export function resolvePresetDates(preset, refDate = getDemoToday()) {
  switch (preset) {
    case '7d':
      return { from: toISODate(addDays(refDate, -6)), to: toISODate(refDate) };
    case '14d':
      return { from: toISODate(addDays(refDate, -13)), to: toISODate(refDate) };
    case '30d':
      return { from: toISODate(addDays(refDate, -29)), to: toISODate(refDate) };
    case 'thisMonth':
      return {
        from: toISODate(startOfMonth(refDate)),
        to: toISODate(refDate),
      };
    case 'lastMonth': {
      const prev = new Date(refDate.getFullYear(), refDate.getMonth() - 1, 1);
      return {
        from: toISODate(startOfMonth(prev)),
        to: toISODate(endOfMonth(prev)),
      };
    }
    default:
      return resolvePresetDates('14d', refDate);
  }
}

/** Период по умолчанию: последние 14 дней. */
export function createDefaultDateRange() {
  const { from, to } = resolvePresetDates('14d');
  return { preset: '14d', from, to };
}

export function getPeriodDayCount(from, to) {
  const a = parseISODate(from);
  const b = parseISODate(to);
  return Math.round((b - a) / (1000 * 60 * 60 * 24)) + 1;
}

/** Предыдущий период той же длины, сразу перед текущим. */
export function getPreviousPeriod(from, to) {
  const days = getPeriodDayCount(from, to);
  const end = addDays(parseISODate(from), -1);
  const start = addDays(end, -(days - 1));
  return { from: toISODate(start), to: toISODate(end) };
}

function formatDayMonth(date) {
  return `${date.getDate()} ${MONTHS_RU[date.getMonth()]}`;
}

/** «Период: 11–24 июня 2026» */
export function formatPeriodLabel(from, to) {
  const a = parseISODate(from);
  const b = parseISODate(to);
  if (a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear()) {
    return `${a.getDate()}–${b.getDate()} ${MONTHS_RU[b.getMonth()]} ${b.getFullYear()}`;
  }
  if (a.getFullYear() === b.getFullYear()) {
    return `${formatDayMonth(a)} – ${formatDayMonth(b)} ${b.getFullYear()}`;
  }
  return `${formatDayMonth(a)} ${a.getFullYear()} – ${formatDayMonth(b)} ${b.getFullYear()}`;
}

/**
 * Ключ mock-набора для overview/campaign list.
 * Custom-период мапится на ближайший preset по длине (явно mock, не API).
 */
export function resolveMockPeriodKey(dateRange) {
  if (dateRange.preset && dateRange.preset !== 'custom') {
    return dateRange.preset;
  }
  const days = getPeriodDayCount(dateRange.from, dateRange.to);
  if (days <= 7) return '7d';
  if (days <= 14) return '14d';
  if (days <= 30) return '30d';
  return '30d';
}
