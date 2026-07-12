'use client';

import React, { useEffect, useRef } from 'react';
import { translations } from '../utils/translations';
import Markdown from './Markdown';

export interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  intent?: string;
  entities?: {
    crops?: string[];
    pests?: string[];
    fertilizers?: string[];
    soilTypes?: string[];
    weather?: string[];
    schemes?: string[];
  };
}

interface ChatAreaProps {
  messages: Message[];
  language: 'en' | 'hi' | 'kn';
  speakText: (text: string) => void;
  stopSpeaking: () => void;
  isSpeaking: boolean;
  speakingMessageId: string | null;
  setSpeakingMessageId: (id: string | null) => void;
}

export default function ChatArea({
  messages,
  language,
  speakText,
  stopSpeaking,
  isSpeaking,
  speakingMessageId,
  setSpeakingMessageId,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const t = translations[language];

  // Auto-scroll to bottom of chat
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSpeakClick = (messageId: string, text: string) => {
    if (isSpeaking && speakingMessageId === messageId) {
      stopSpeaking();
      setSpeakingMessageId(null);
    } else {
      setSpeakingMessageId(messageId);
      speakText(text);
    }
  };

  useEffect(() => {
    if (!isSpeaking) {
      setSpeakingMessageId(null);
    }
  }, [isSpeaking, setSpeakingMessageId]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((message) => {
        const isUser = message.sender === 'user';
        const isCurrentlySpeaking = isSpeaking && speakingMessageId === message.id;

        // Compile non-empty entities for visual tag display
        const entityList: string[] = [];
        if (message.entities) {
          Object.entries(message.entities).forEach(([key, list]) => {
            if (list && list.length > 0) {
              list.forEach((val) => entityList.push(`${key}: ${val}`));
            }
          });
        }

        return (
          <div
            key={message.id}
            className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-full`}
          >
            {/* Bubble */}
            <div
              className={`relative max-w-[85%] rounded-2xl px-4 py-3 shadow-sm transition-all ${
                isUser
                  ? 'bg-primary text-primary-foreground rounded-tr-none'
                  : 'bg-card text-card-foreground border border-border rounded-tl-none'
              }`}
            >
              {/* Message text with markdown formatting support */}
              <Markdown text={message.text} />

              {/* Visual NLP Tags (Only for Assistant messages to show classification & NER) */}
              {!isUser && (message.intent || entityList.length > 0) && (
                <div className="mt-2 border-t border-border pt-2 text-[10px] space-y-1 font-semibold text-muted-foreground">
                  {message.intent && (
                    <div className="flex items-center space-x-1">
                      <span className="bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 rounded px-1.5 py-0.5">
                        Intent: {message.intent}
                      </span>
                    </div>
                  )}
                  {entityList.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {entityList.map((tag, idx) => (
                        <span key={idx} className="bg-primary-light text-primary rounded px-1.5 py-0.5">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Read Aloud Button (Only for Assistant messages) */}
              {!isUser && (
                <div className="mt-2 flex items-center justify-end border-t border-border pt-1.5">
                  <button
                    onClick={() => handleSpeakClick(message.id, message.text)}
                    className={`inline-flex items-center space-x-1 rounded-full px-3 py-1 text-xs font-bold transition-all focus:outline-none focus:ring-2 focus:ring-primary ${
                      isCurrentlySpeaking
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        : 'bg-primary-light text-primary hover:bg-opacity-80'
                    }`}
                  >
                    {isCurrentlySpeaking ? (
                      <>
                        <svg className="h-3.5 w-3.5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
                        </svg>
                        <span>{t.stopReading}</span>
                      </>
                    ) : (
                      <>
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
                        </svg>
                        <span>{t.readAloud}</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Time Stamp */}
            <span className="mt-1 px-2 text-[10px] font-semibold text-muted-foreground">
              {message.timestamp}
            </span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
