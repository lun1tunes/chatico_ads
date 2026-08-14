/** Утилиты форматирования чисел для дашборда (RU-локаль). */

/** Денежная сумма в тенге: 24000 → «24 000 ₸». Дробные ≥0 и <10 — с двумя знаками. */
export function formatTenge(value) {
  return formatMoney(value, 'KZT');
}

/** Денежная сумма с учётом валюты кампании. */
export function formatMoney(value, currency = 'KZT') {
  if (value == null) return '—';

  if (currency === 'USD') {
    return `$${value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  const fractionDigits = value > 0 && value < 10 ? 2 : 0;
  return `${value.toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })} ₸`;
}

/** Целое число с разделителями разрядов: 42000 → «42 000». */
export function formatNumber(value) {
  if (value == null) return '—';
  return value.toLocaleString('ru-RU');
}

/** «1 объявление», «4 объявления», «5 объявлений». */
export function formatAdsCountLabel(count) {
  const n = Math.abs(Number(count) || 0);
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} объявление`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${n} объявления`;
  return `${n} объявлений`;
}
