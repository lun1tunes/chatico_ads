/** Утилиты форматирования чисел для дашборда (RU-локаль). */

/** Денежная сумма в тенге: 24000 → «24 000 ₸». Дробные ≥0 и <10 — с двумя знаками. */
export function formatTenge(value) {
  if (value == null) return '—';
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
