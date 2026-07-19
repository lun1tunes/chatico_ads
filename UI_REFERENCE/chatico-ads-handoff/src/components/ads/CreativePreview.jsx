/**
 * Превью креатива объявления (заглушка до реальных картинок из Meta API).
 *
 * Чтобы баннер был узнаваем визуально, а не только по названию:
 * - уникальный градиент, детерминированный по id объявления;
 * - оформление под тип креатива (видео/Reels/карусель/баннер/лид-форма);
 * - бейдж с названием формата.
 */
const GRADIENTS = [
  'from-[#5E44EB] to-[#9B87F5]',
  'from-[#2AABEE] to-[#5E44EB]',
  'from-[#EC4899] to-[#8B5CF6]',
  'from-[#F59E0B] to-[#EF4444]',
  'from-[#14B8A6] to-[#22D3EE]',
  'from-[#6366F1] to-[#A855F7]',
  'from-[#10B981] to-[#84CC16]',
];

const FORMAT_META = {
  video: { label: 'Видео', play: true },
  reels: { label: 'Reels', play: true, vertical: true },
  stories: { label: 'Stories', play: true, vertical: true },
  carousel: { label: 'Карусель', carousel: true },
  leadform: { label: 'Лид-форма', form: true },
  image: { label: 'Баннер' },
};

function hashString(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h;
}

/** Определяем тип креатива по названию объявления. */
export function inferFormat(name = '') {
  const n = name.toLowerCase();
  if (/reels/.test(n)) return 'reels';
  if (/stories|сторис/.test(n)) return 'stories';
  if (/видео|video|вебинар/.test(n)) return 'video';
  if (/карусель|carousel/.test(n)) return 'carousel';
  if (/лид-форма|lead|форма|чек-лист|аудит/.test(n)) return 'leadform';
  return 'image';
}

export default function CreativePreview({ id, name, format }) {
  const resolved = format ?? inferFormat(name);
  const meta = FORMAT_META[resolved] ?? FORMAT_META.image;
  const gradient = GRADIENTS[hashString(id ?? name ?? '') % GRADIENTS.length];

  return (
    <div
      className={`relative aspect-video w-full shrink-0 overflow-hidden rounded-xl bg-gradient-to-br ${gradient} sm:aspect-[4/3] sm:w-40`}
    >
      {/* Декоративные пятна — имитация графики креатива */}
      <div className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-white/15" />
      <div className="pointer-events-none absolute -bottom-10 -left-6 h-24 w-24 rounded-full bg-black/10" />

      {/* Центральный элемент по типу формата */}
      <div className="absolute inset-0 flex items-center justify-center">
        {meta.play && (
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/90 shadow-md">
            <svg className="ml-0.5 h-5 w-5 text-[#1C1B1F]" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        )}
        {meta.carousel && (
          <div className="flex items-center gap-1.5">
            <div className="h-12 w-9 rounded-md bg-white/30" />
            <div className="h-14 w-11 rounded-md bg-white/80 shadow-md" />
            <div className="h-12 w-9 rounded-md bg-white/30" />
          </div>
        )}
        {meta.form && (
          <div className="w-20 rounded-md bg-white/90 p-2 shadow-md">
            <div className="h-1.5 w-12 rounded-full bg-gray-300" />
            <div className="mt-1.5 h-1.5 w-16 rounded-full bg-gray-200" />
            <div className="mt-1.5 h-1.5 w-10 rounded-full bg-gray-200" />
            <div className="mt-2 h-3 w-full rounded bg-[#5E44EB]" />
          </div>
        )}
        {!meta.play && !meta.carousel && !meta.form && (
          <svg className="h-10 w-10 text-white/80" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M9.5 9.5a1.2 1.2 0 11-2.4 0 1.2 1.2 0 012.4 0z" />
          </svg>
        )}
      </div>

      {/* Вертикальная рамка-подсказка для Reels/Stories */}
      {meta.vertical && (
        <div className="pointer-events-none absolute inset-y-2 left-1/2 w-10 -translate-x-1/2 rounded-md border-2 border-white/50" />
      )}

      {/* Бейдж формата */}
      <span className="absolute bottom-2 left-2 rounded-md bg-white/90 px-1.5 py-0.5 text-[10px] font-bold text-gray-800">
        {meta.label}
      </span>
    </div>
  );
}
