import PeriodControl from './PeriodControl';

/**
 * Шапка экрана с глобальным выбором периода (сквозной PeriodControl).
 */
export default function PageHeader({ eyebrow, title, subtitle, back, trailing }) {
  return (
    <div className="space-y-4">
      {back}
      <div
        className={`flex min-w-0 flex-1 flex-col gap-4 xl:flex-row xl:justify-between ${
          trailing ? 'xl:items-end' : 'xl:items-start'
        }`}
      >
        <div className="min-w-0 flex-1">
          {eyebrow && (
            <div className="flex items-center gap-2">
              <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{eyebrow}</p>
            </div>
          )}
          {typeof title === 'string' ? (
            <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-on-surface">{title}</h1>
          ) : (
            <div className="mt-1.5">{title}</div>
          )}
          {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-start gap-3 self-start xl:pt-6">
          {trailing}
          <PeriodControl />
        </div>
      </div>
    </div>
  );
}
