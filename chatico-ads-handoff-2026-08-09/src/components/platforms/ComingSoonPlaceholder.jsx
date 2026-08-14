import { PLATFORMS, useAppStore } from '../../store/useAppStore';

const PLATFORM_LABELS = {
  [PLATFORMS.GOOGLE]: 'Google Ads',
  [PLATFORMS.TIKTOK]: 'TikTok Ads',
};

export default function ComingSoonPlaceholder() {
  const platform = useAppStore((s) => s.selectedPlatform);
  const label = PLATFORM_LABELS[platform] ?? 'Платформа';

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-card bg-surface p-12 text-center shadow-card">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-secondary-container text-2xl">
        🚧
      </div>
      <h2 className="text-xl font-bold text-on-surface">{label}</h2>
      <p className="mt-2 max-w-md text-sm text-on-surface-variant">
        Эта платформа появится после MVP на Meta. Структура экранов будет такой же:
        обзор → кампании → AI-консультант.
      </p>
      <p className="mt-6 text-xs text-on-surface-variant">Модуль M9 · Platforms</p>
    </div>
  );
}
