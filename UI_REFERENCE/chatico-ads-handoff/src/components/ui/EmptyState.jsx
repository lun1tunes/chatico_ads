export default function EmptyState({ title, description, action }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-card bg-surface p-8 text-center shadow-card">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-container text-primary">
        🔍
      </div>
      <h3 className="text-lg font-bold text-on-surface">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-on-surface-variant">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
