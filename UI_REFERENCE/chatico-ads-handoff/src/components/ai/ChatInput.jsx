import { useState } from 'react';

/** Поле ввода сообщения с отправкой по Enter и кнопкой. */
export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-outline bg-white p-2 shadow-sm focus-within:border-[#5E44EB]/50 focus-within:ring-2 focus-within:ring-[#5E44EB]/10">
      <textarea
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Спросите про вашу рекламу…"
        className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-on-surface placeholder:text-gray-400 focus:outline-none"
      />
      <button
        type="button"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Отправить"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#5E44EB] text-white transition-all duration-150 hover:brightness-110 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </button>
    </div>
  );
}
