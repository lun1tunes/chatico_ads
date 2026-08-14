const SMB_MARKERS = [
  'малый бизнес',
  'small business',
  'средний бизнес',
  'medium business',
  'предприним',
  'entrepreneur',
  ' smb',
  'индивидуальный предприниматель',
  'individual entrepreneur',
  'владельцы малых',
  'small business owner',
];

const LEADER_MARKERS = [
  'owner',
  'founder',
  'ceo',
  'director',
  'manager',
  'владелец',
  'основатель',
  'учредитель',
  'директор',
  'ген.директор',
  'генеральный',
  'управляющ',
];

const LIFESTYLE_MARKERS = [
  'lifestyle',
  'shopping',
  'шопинг',
  'мода',
  'fashion',
  'beauty',
  'красот',
];

function normalize(text = '') {
  return String(text).toLowerCase().trim();
}

function includesAny(text, markers) {
  const value = normalize(text);
  return markers.some((marker) => value.includes(marker));
}

function collectSignals(fbDetails = {}) {
  const items = [
    ...(fbDetails.interests ?? []),
    ...(fbDetails.behaviors ?? []),
    ...(fbDetails.jobTitles ?? []),
    ...(fbDetails.customAudiences ?? []),
  ];

  return {
    smb: items.some((item) => includesAny(item, SMB_MARKERS)),
    leaders: items.some((item) => includesAny(item, LEADER_MARKERS)),
    lifestyle: items.some((item) => includesAny(item, LIFESTYLE_MARKERS)),
  };
}

function formatCityPhrase(city = '') {
  const cities = city
    .split('·')
    .map((part) => part.trim())
    .filter(Boolean);

  if (!cities.length) return '';
  if (cities.some((part) => /вся\s*рк/i.test(part))) return 'по всей РК';
  if (cities.length === 1) return `из ${cities[0]}`;
  if (cities.length === 2) return `из ${cities[0]} и ${cities[1]}`;
  return `из ${cities.slice(0, -1).join(', ')} и ${cities[cities.length - 1]}`;
}

function formatGenderPhrase(gender) {
  if (!gender || gender === 'Все') return '';
  return gender.toLowerCase();
}

function describeMechanism(targeting = {}) {
  const audienceType = normalize(targeting.audienceType);
  const interests = targeting.interests ?? '';
  const fbDetails = targeting.fbDetails ?? {};

  if (fbDetails.lookalike || audienceType.includes('похож')) {
    return 'похожие по поведению на ваших текущих клиентов';
  }

  if (
    fbDetails.retargeting ||
    audienceType.includes('ретаргет') ||
    (fbDetails.customAudiences ?? []).some((item) => includesAny(item, ['сайт', 'корзин', 'посетител', 'смотрел']))
  ) {
    return 'те, кто уже взаимодействовали с вашим бизнесом';
  }

  if (interests) {
    const topic = interests.replace(/^интересы\s*·\s*/i, '').trim();
    if (topic) return `отобраны по интересам: ${topic.toLowerCase()}`;
  }

  if (audienceType) return audienceType.toLowerCase();

  return '';
}

function describeProfile(signals) {
  if (signals.smb && signals.leaders) {
    return 'Чаще всего это владельцы и руководители малого и среднего бизнеса.';
  }
  if (signals.smb) {
    return 'Обычно это люди, связанные с малым и средним бизнесом.';
  }
  if (signals.leaders) {
    return 'Чаще всего это руководители и люди, принимающие решения в компании.';
  }
  if (signals.lifestyle) {
    return 'Интересуются покупками, lifestyle-контентом и новинками.';
  }
  return '';
}

/**
 * Переводит сырые данные Facebook в 1–2 короткие фразы простым языком.
 * Возвращает массив строк: первая — с «→», вторая — уточнение профиля (если есть).
 */
export function summarizeAudience(targeting) {
  if (!targeting) return [];

  const cityPhrase = formatCityPhrase(targeting.city);
  const genderPhrase = formatGenderPhrase(targeting.gender);
  const mechanism = describeMechanism(targeting);

  let intro = '→ Это люди';
  if (cityPhrase) intro += ` ${cityPhrase}`;
  if (targeting.age) intro += ` ${targeting.age} лет`;
  if (genderPhrase) intro += ` — ${genderPhrase}`;
  if (mechanism) intro += ` — ${mechanism}`;

  const lines = [intro.replace(/\s+/g, ' ').trim()];

  const profile = describeProfile(collectSignals(targeting.fbDetails));
  if (profile) lines.push(profile);

  return lines;
}

/** Одна строка для карточек и ИИ-контекста. */
export function summarizeAudiencePlain(targeting) {
  return summarizeAudience(targeting).join(' ').replace(/^→\s*/, '');
}
