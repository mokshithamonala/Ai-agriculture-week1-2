'use client';

import React, { useRef, useEffect } from 'react';
import { translations } from '../utils/translations';

interface VoiceInputProps {
  language: 'en' | 'hi' | 'kn';
  isListening: boolean;
  startListening: () => void;
  stopListening: () => void;
  sendMessage: (text: string) => void;
  inputText: string;
  setInputText: (text: string) => void;
}

export default function VoiceInput({
  language,
  isListening,
  startListening,
  stopListening,
  sendMessage,
  inputText,
  setInputText,
}: VoiceInputProps) {
  const t = translations[language];
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendMessage(inputText.trim());
    setInputText('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
    }
  };

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // Auto-grow textarea height on text change
  useEffect(() => {
    if (textareaRef.current) {
      // Set to minimal height first to recalculate scrollHeight properly
      textareaRef.current.style.height = '48px';
      if (inputText.trim()) {
        const scrollHeight = textareaRef.current.scrollHeight;
        // Cap the max height of the growing area at 140px
        textareaRef.current.style.height = `${Math.min(scrollHeight, 140)}px`;
      }
    }
  }, [inputText]);

  // Handle enter key to send message (Shift+Enter for new line)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim()) {
        sendMessage(inputText.trim());
        setInputText('');
        if (textareaRef.current) {
          textareaRef.current.style.height = '48px';
        }
      }
    }
  };

  return (
    <div className="border-t border-border bg-card p-4 shadow-inner text-card-foreground">
      <div className="mx-auto max-w-md flex flex-col items-center space-y-4">
        
        {/* Helper Prompt Text */}
        <p className={`text-sm font-semibold tracking-wide transition-all ${
          isListening 
            ? 'text-red-500 animate-pulse font-bold' 
            : 'text-muted-foreground'
        }`}>
          {isListening ? t.listening : t.tapMic}
        </p>

        {/* Massive Microphone Button */}
        <button
          type="button"
          onClick={handleMicClick}
          className={`flex h-24 w-24 items-center justify-center rounded-full border-4 border-background shadow-lg transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-primary/50 active:scale-90 ${
            isListening
              ? 'bg-red-500 text-white pulse-button'
              : 'bg-primary text-primary-foreground hover:opacity-90'
          }`}
          aria-label={isListening ? 'Stop Listening' : 'Start Listening'}
        >
          {isListening ? (
            // Stop Icon / Mic Recording
            <svg className="h-10 w-10 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
          ) : (
            // Microphone Icon
            <svg className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          )}
        </button>

        {/* Text Input Fallback (for typing) */}
        <form onSubmit={handleSend} className="w-full flex items-end space-x-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t.placeholder}
            className="flex-1 min-h-[48px] max-h-[140px] resize-none rounded-2xl border border-border bg-background px-4 py-3 text-base text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all duration-100"
            style={{ height: '48px' }}
          />
          <button
            type="submit"
            disabled={!inputText.trim()}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md transition-all hover:opacity-90 active:scale-95 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none mb-0.5 flex-shrink-0"
            aria-label="Send Message"
          >
            {/* Send Paperplane Icon */}
            <svg className="h-5 w-5 rotate-45 transform -translate-x-0.5 translate-y-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
