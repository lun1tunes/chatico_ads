import { summarizeAudience, summarizeAudiencePlain } from '../../utils/audienceSummary';

/** Краткое описание аудитории для карточки группы. */
export function formatAudienceBrief(targeting) {
  if (!targeting) return '';
  const summary = summarizeAudiencePlain(targeting);
  if (summary) return summary;

  const parts = [];
  if (targeting.audienceType) parts.push(targeting.audienceType);
  else if (targeting.interests) parts.push(targeting.interests);
  if (targeting.city) parts.push(targeting.city);
  if (targeting.gender && targeting.age) {
    parts.push(`${targeting.gender.toLowerCase()}, ${targeting.age}`);
  }
  return parts.join(' · ');
}

/**
 * Компактная строка таргетинга под названием группы объявлений.
 */
export default function TargetingLine({ targeting }) {
  const brief = formatAudienceBrief(targeting);
  if (!brief) return null;

  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400">
      <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <span className="truncate">{brief}</span>
    </div>
  );
}

function TargetingField({ label, value }) {
  if (!value) return null;
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-on-surface">{value}</p>
    </div>
  );
}

/** Развёрнутый блок таргетинга на странице группы объявлений. */
export function TargetingDetails({ targeting }) {
  if (!targeting) return null;

  const audience =
    targeting.audienceType ?? targeting.interests ?? null;
  const summaryLines = summarizeAudience(targeting);

  return (
    <div className="rounded-xl border border-outline bg-white p-4 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <TargetingField label="География" value={targeting.city} />
        <TargetingField label="Возраст" value={targeting.age} />
        <TargetingField label="Пол" value={targeting.gender} />
        <TargetingField label="Аудитория" value={audience} />
      </div>

      {summaryLines.length > 0 && (
        <div className="mt-4 border-t border-outline/60 pt-4">
          {summaryLines.map((line) => (
            <p
              key={line}
              className="text-sm leading-relaxed text-gray-600 first:font-medium first:text-on-surface"
            >
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
