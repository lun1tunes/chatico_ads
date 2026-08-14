export default function Skeleton({ className = '' }) {
  return (
    <div
      className={`animate-pulse rounded bg-surface-variant ${className}`}
      style={{ animationDuration: '1.5s' }}
    />
  );
}
