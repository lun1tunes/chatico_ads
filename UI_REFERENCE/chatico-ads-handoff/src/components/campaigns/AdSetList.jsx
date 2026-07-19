import AdSetRow from './AdSetRow';

/** Список групп объявлений кампании с секционным заголовком. */
export default function AdSetList({ adSets, resultLabel }) {
  if (!adSets || adSets.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
        <p className="text-sm text-gray-400">В этой кампании пока нет групп объявлений.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">
          Группы объявлений · {adSets.length}
        </h2>
      </div>

      {adSets.map((adSet) => (
        <AdSetRow key={adSet.id} adSet={adSet} resultLabel={resultLabel} />
      ))}
    </div>
  );
}
