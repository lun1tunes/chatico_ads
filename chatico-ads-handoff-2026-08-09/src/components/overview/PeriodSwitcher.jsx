/**
 * Переключатель периода в стиле shadcn/ui Tabs/ToggleGroup:
 * трек bg-muted, активная вкладка bg-background со слабой тенью.
 */
export default function PeriodSwitcher({ selectedPeriod, onPeriodChange }) {
  const periods = [
    { value: 7, label: '7 дней' },
    { value: 14, label: '14 дней' },
    { value: 30, label: '30 дней' },
  ];

  return (
    <div className="inline-flex h-9 items-center rounded-lg bg-muted p-1 text-muted-foreground">
      {periods.map((period) => {
        const isSelected = selectedPeriod === period.value;
        return (
          <button
            key={period.value}
            type="button"
            onClick={() => onPeriodChange(period.value)}
            className={`inline-flex h-7 items-center rounded-md px-3 text-xs font-medium transition-all duration-150 ${
              isSelected
                ? 'bg-white text-on-surface shadow-sm'
                : 'hover:text-on-surface'
            }`}
          >
            {period.label}
          </button>
        );
      })}
    </div>
  );
}
