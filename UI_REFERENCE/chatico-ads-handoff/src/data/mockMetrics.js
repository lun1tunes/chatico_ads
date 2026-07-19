/**
 * Mock-данные для дашборда Chatico ADS (M11)
 * Поддерживает периоды: 7, 14, 30, 60, 90 дней
 */

export const MOCK_METRICS_BY_PERIOD = {
  7: {
    spent: { value: '145 200 ₸', trend: { value: '12%', isPositive: false }, subtitle: 'Потрачено за 7 дней' },
    leads: { value: '382 контакта', trend: { value: '18%', isPositive: true }, subtitle: 'Начали диалог в WhatsApp' },
    cpl: { value: '380 ₸', trend: { value: '5%', isPositive: true }, subtitle: 'Стоимость одного контакта' },
    impressions: { value: '45 800 раз', trend: { value: '3%', isPositive: true }, subtitle: 'Показы объявлений' },
    verdict: {
      status: 'good',
      text: 'Реклама работает отлично! За последнюю неделю мы получили на 18% больше контактов, при этом стоимость привлечения одного клиента снизилась на 5%. Наиболее эффективна кампания на Алматы — рекомендуем перераспределить часть бюджета туда.',
    },
    chartData: [
      { date: '18.06', spent: 18000, leads: 48 },
      { date: '19.06', spent: 21000, leads: 52 },
      { date: '20.06', spent: 19500, leads: 50 },
      { date: '21.06', spent: 22000, leads: 58 },
      { date: '22.06', spent: 20000, leads: 55 },
      { date: '23.06', spent: 23200, leads: 61 },
      { date: '24.06', spent: 21500, leads: 58 },
    ],
  },
  14: {
    spent: { value: '310 500 ₸', trend: { value: '8%', isPositive: true }, subtitle: 'Потрачено за 14 дней' },
    leads: { value: '740 контактов', trend: { value: '14%', isPositive: true }, subtitle: 'Начали диалог в WhatsApp' },
    cpl: { value: '419 ₸', trend: { value: '6%', isPositive: true }, subtitle: 'Стоимость одного контакта' },
    impressions: { value: '98 200 раз', trend: { value: '10%', isPositive: true }, subtitle: 'Показы объявлений' },
    verdict: {
      status: 'warning',
      text: 'В целом показатели стабильные, но кампания на женскую аудиторию стала обходиться дороже на 12% за последние дни. Рекомендуем обновить рекламные баннеры, так как старые примелькались пользователям и начали терять эффективность.',
    },
    chartData: [
      { date: '11.06', spent: 19000, leads: 45 },
      { date: '12.06', spent: 20000, leads: 47 },
      { date: '13.06', spent: 22000, leads: 51 },
      { date: '14.06', spent: 21000, leads: 49 },
      { date: '15.06', spent: 23000, leads: 53 },
      { date: '16.06', spent: 22500, leads: 52 },
      { date: '17.06', spent: 24000, leads: 56 },
      { date: '18.06', spent: 21000, leads: 50 },
      { date: '19.06', spent: 23000, leads: 54 },
      { date: '20.06', spent: 22000, leads: 51 },
      { date: '21.06', spent: 24500, leads: 59 },
      { date: '22.06', spent: 21000, leads: 52 },
      { date: '23.06', spent: 24000, leads: 60 },
      { date: '24.06', spent: 23500, leads: 57 },
    ],
  },
  30: {
    spent: { value: '680 000 ₸', trend: { value: '15%', isPositive: true }, subtitle: 'Потрачено за 30 дней' },
    leads: { value: '1 520 контактов', trend: { value: '22%', isPositive: true }, subtitle: 'Начали диалог в WhatsApp' },
    cpl: { value: '447 ₸', trend: { value: '8%', isPositive: true }, subtitle: 'Стоимость одного контакта' },
    impressions: { value: '215 000 раз', trend: { value: '12%', isPositive: true }, subtitle: 'Показы объявлений' },
    verdict: {
      status: 'good',
      text: 'Отличный месяц! Мы привлекли 1520 потенциальных клиентов. Средняя стоимость контакта удерживается на комфортном уровне в 447 ₸. Основной драйвер роста — кампания с акцией «Скидка 20%». Советуем продлить её действие на следующий месяц.',
    },
    chartData: Array.from({ length: 30 }, (_, i) => {
      const day = i + 1;
      return {
        date: `${day}.06`,
        spent: Math.round(20000 + Math.sin(day) * 3000 + Math.random() * 2000),
        leads: Math.round(45 + Math.sin(day) * 8 + Math.random() * 6),
      };
    }),
  },
};
