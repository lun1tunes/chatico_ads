import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';

export default function WelcomePage() {
  const clearAiContext = useAppStore((s) => s.clearAiContext);

  useEffect(() => {
    clearAiContext();
    return () => clearAiContext();
  }, [clearAiContext]);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="max-w-lg pt-4">
        <h1 className="text-3xl font-bold tracking-tight text-on-surface">
          Добро пожаловать
        </h1>
        <p className="mt-4 text-base leading-relaxed text-gray-600">
          Здесь — вся ваша реклама. Слева выберите кампанию, справа спросите у ИИ-ассистента
          что угодно про результаты.
        </p>
        <p className="mt-6 text-sm font-semibold text-[#5E44EB]">
          Начните с выбора кампании в меню слева.
        </p>
      </div>
    </div>
  );
}
