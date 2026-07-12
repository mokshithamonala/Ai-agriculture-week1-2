'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from '../components/Navbar';
import ChatArea, { Message } from '../components/ChatArea';
import VoiceInput from '../components/VoiceInput';
import { useSpeech } from '../hooks/useSpeech';
import { translations } from '../utils/translations';

export default function Home() {
  const [language, setLanguage] = useState<'en' | 'hi' | 'kn'>('en');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);

  const sessionIdRef = useRef<string>('');

  // Generate session ID on initial mount
  useEffect(() => {
    sessionIdRef.current = `session-${Math.random().toString(36).substring(2, 9)}`;
  }, []);

  // Initialize theme from state
  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  // Register PWA service worker
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => console.log('Service Worker Registered Successfully', reg.scope))
        .catch((err) => console.error('Service Worker Registration Failed', err));
    }
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  // Get current translation
  const t = translations[language];

  // Set initial welcome message
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: translations[language].welcome,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  }, [language]);

  // Trigger error message banner
  const handleError = useCallback((msg: string) => {
    setErrorMessage(msg);
    setTimeout(() => {
      setErrorMessage(null);
    }, 4500);
  }, []);

  // Handle incoming completed transcription from microphone
  const handleTranscriptComplete = useCallback((text: string) => {
    setInputText(text);
    if (text.trim()) {
      handleSendMessage(text.trim(), true);
    }
  }, [language]);

  // Initialize Speech Pipeline Hook
  const {
    isListening,
    isSpeaking,
    isProcessing: isSpeechProcessing,
    startListening,
    stopListening,
    speakText,
    stopSpeaking,
  } = useSpeech({
    language,
    onTranscriptComplete: handleTranscriptComplete,
    onError: handleError,
  });

  const handleSendMessage = async (text: string, wasVoice: boolean = false) => {
    if (!text.trim() || chatLoading) return;

    // Stop currently active speak readback
    stopSpeaking();

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Add user message
    const userMsgId = Date.now().toString();
    const newUserMessage: Message = {
      id: userMsgId,
      sender: 'user',
      text,
      timestamp,
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInputText('');
    setChatLoading(true);

    try {
      // Build clean history array excluding the initial welcome message
      const historyPayload = messages
        .filter((msg) => msg.id !== 'welcome')
        .map((msg) => ({
          sender: msg.sender,
          text: msg.text,
          intent: msg.intent,
          entities: msg.entities,
        }));

      // Call API chat route
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: historyPayload,
          language,
          sessionId: sessionIdRef.current,
          mode: wasVoice ? 'voice' : 'text',
        }),
      });

      if (!response.ok) {
        throw new Error('Advisory request failed');
      }

      const data = await response.json();
      const assistantMsgId = Date.now().toString();
      const newAssistantMessage: Message = {
        id: assistantMsgId,
        sender: 'assistant',
        text: data.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        intent: data.intent,
        entities: data.entities,
      };

      setMessages((prev) => [...prev, newAssistantMessage]);

      // Automatically speak the response aloud if triggered via voice input
      if (wasVoice) {
        setSpeakingMessageId(assistantMsgId);
        speakText(data.response);
      }
    } catch (err) {
      console.error(err);
      handleError('Could not process query. Please check your network connection.');
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="flex h-full w-full flex-col bg-background font-sans transition-colors duration-200">
      <div className="mx-auto flex h-full w-full max-w-md flex-col border-x border-border bg-background shadow-2xl relative">
        
        {/* Floating Error/Warning Alert */}
        {errorMessage && (
          <div className="absolute top-20 left-4 right-4 z-50 rounded-xl bg-red-100 border border-red-200 p-3 shadow-md text-red-800 text-sm font-semibold flex items-center justify-between animate-fade-in-down">
            <div className="flex items-center space-x-2">
              <svg className="h-5 w-5 text-red-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-red-500 hover:text-red-700">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Top Navbar */}
        <Navbar
          language={language}
          setLanguage={setLanguage}
          theme={theme}
          toggleTheme={toggleTheme}
        />

        {/* Scrollable Chat Area */}
        <ChatArea
          messages={messages}
          language={language}
          speakText={speakText}
          stopSpeaking={stopSpeaking}
          isSpeaking={isSpeaking}
          speakingMessageId={speakingMessageId}
          setSpeakingMessageId={setSpeakingMessageId}
        />

        {/* Audio Transcribing or Chat Loading Indicator */}
        {(isSpeechProcessing || chatLoading) && (
          <div className="px-4 py-2 bg-primary-light border-y border-border text-center text-sm font-semibold text-primary flex items-center justify-center space-x-2">
            <svg className="animate-spin h-4 w-4 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>{isSpeechProcessing ? 'Processing your voice...' : 'Generating advisor answer...'}</span>
          </div>
        )}

        {/* Bottom Panel */}
        <VoiceInput
          language={language}
          isListening={isListening}
          startListening={startListening}
          stopListening={stopListening}
          sendMessage={(text) => handleSendMessage(text, false)}
          inputText={inputText}
          setInputText={setInputText}
        />
      </div>
    </div>
  );
}
