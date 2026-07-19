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

export default function ChatMessage({ role, text, typing }) {
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
        {typing ? <TypingDots /> : text}
      </div>
    </div>
  );
}
