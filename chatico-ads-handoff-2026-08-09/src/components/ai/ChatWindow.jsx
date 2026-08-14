import { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import SuggestedChips from './SuggestedChips';
import ChatInput from './ChatInput';
import { AI_WELCOME, SUGGESTED_QUESTIONS, getAiResponse } from '../../data/mockAiResponses';
import { useAppStore } from '../../store/useAppStore';

let messageCounter = 0;
const nextId = () => `msg_${++messageCounter}`;

/** Строит первое (авто) сообщение чата с учётом контекста экрана. */
function buildIntroMessage(aiContext) {
  if (aiContext?.intro) {
    return {
      id: nextId(),
      role: 'assistant',
      text: aiContext.intro,
      verdict: aiContext.verdict ? { status: aiContext.verdict.status } : undefined,
    };
  }
  return { id: nextId(), role: 'assistant', text: AI_WELCOME };
}

export default function ChatWindow() {
  const aiContext = useAppStore((s) => s.aiContext);
  const contextKey = aiContext?.key ?? 'default';
  const questions = aiContext?.questions ?? SUGGESTED_QUESTIONS;

  const [messages, setMessages] = useState(() => [buildIntroMessage(aiContext)]);
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef(null);
  const timerRef = useRef(null);
  const prevKeyRef = useRef(contextKey);

  const hasUserMessage = messages.some((m) => m.role === 'user');

  // Смена контекста (открыли другую кампанию / вернулись в обзор) → новый первый ответ
  useEffect(() => {
    if (prevKeyRef.current !== contextKey) {
      prevKeyRef.current = contextKey;
      clearTimeout(timerRef.current);
      setTyping(false);
      setMessages([buildIntroMessage(aiContext)]);
    }
  }, [contextKey, aiContext]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, typing]);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  const handleSend = (text) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text }]);
    setTyping(true);
    timerRef.current = setTimeout(() => {
      setTyping(false);
      setMessages((prev) => [...prev, { id: nextId(), role: 'assistant', text: getAiResponse(text) }]);
    }, 900);
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.map((m) => (
          <ChatMessage key={m.id} role={m.role} text={m.text} verdict={m.verdict} />
        ))}
        {typing && <ChatMessage role="assistant" typing />}

        {!hasUserMessage && !typing && (
          <div className="pt-2">
            <SuggestedChips questions={questions} onPick={handleSend} />
          </div>
        )}
      </div>

      <div className="border-t border-outline bg-white p-3">
        <ChatInput onSend={handleSend} disabled={typing} />
        <p className="mt-2 text-center text-[10px] text-gray-400">
          Демо-режим · ответы на основе тестовых данных
        </p>
      </div>
    </div>
  );
}
