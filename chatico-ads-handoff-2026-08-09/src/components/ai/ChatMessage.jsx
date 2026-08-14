/** Аватар ИИ-консультанта — фирменный мотив: чат-облако индиго на лаймовой подложке. */
function AiAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#c2f913]">
      <svg className="h-4 w-4 text-[#5E44EB]" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
      </svg>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

/** Шапка вердикта внутри сообщения чата: иконка-искра + бейдж статуса. */
function VerdictHeader({ status }) {
  const isGood = status === 'good';
  return (
    <div className="mb-2 flex items-center justify-between gap-2 border-b border-outline pb-2">
      <div className="flex items-center gap-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-[#5E44EB]/10 text-[#5E44EB]">
          <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.4 6.6L22 12l-6.6 2.4L13 21l-2.4-6.6L4 12l6.6-2.4L13 3z" />
          </svg>
        </span>
        <span className="text-xs font-bold text-on-surface">ИИ-Вердикт</span>
      </div>
      <span
        className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${
          isGood ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'
        }`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${isGood ? 'bg-emerald-500' : 'bg-amber-500'}`} />
        {isGood ? 'Всё отлично' : 'Есть нюанс'}
      </span>
    </div>
  );
}

export default function ChatMessage({ role, text, typing, verdict }) {
  const isUser = role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-[#5E44EB] px-3.5 py-2.5 text-sm font-medium leading-relaxed text-white shadow-sm">
          {text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <AiAvatar />
      <div className="max-w-[82%] rounded-2xl rounded-tl-md border border-outline bg-white px-3.5 py-2.5 text-sm leading-relaxed text-on-surface shadow-sm">
        {typing ? (
          <TypingDots />
        ) : (
          <>
            {verdict && <VerdictHeader status={verdict.status} />}
            {text}
          </>
        )}
      </div>
    </div>
  );
}
