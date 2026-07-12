'use client';

import React, { useEffect, useState } from 'react';
import { translations } from '../utils/translations';

interface NavbarProps {
  language: 'en' | 'hi' | 'kn';
  setLanguage: (lang: 'en' | 'hi' | 'kn') => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

export default function Navbar({ language, setLanguage, theme, toggleTheme }: NavbarProps) {
  const [isOnline, setIsOnline] = useState(true);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isInstallable, setIsInstallable] = useState(false);

  const t = translations[language];

  useEffect(() => {
    if (typeof window === 'undefined') return;

    setIsOnline(navigator.onLine);

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // PWA Install Prompt handler
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setIsInstallable(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      console.log('User accepted the PWA install prompt');
    }
    setDeferredPrompt(null);
    setIsInstallable(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card text-card-foreground shadow-md transition-colors duration-200">
      <div className="mx-auto flex h-16 max-w-md items-center justify-between px-4">
        {/* App Title & Icon */}
        <div className="flex items-center space-x-2">
          <svg className="h-8 w-8 text-primary" viewBox="0 0 512 512" fill="currentColor">
            <circle cx="256" cy="256" r="240" fill="currentColor" opacity="0.15" />
            <path d="M256 120 C180 120 140 200 140 280 C140 360 200 380 256 380 C312 380 372 360 372 280 C372 200 332 120 256 120 Z" className="text-primary" />
            <path d="M256 380 V 200" stroke="#ffffff" strokeWidth="16" strokeLinecap="round" />
            <path d="M256 270 Q 190 230 170 180 Q 220 180 256 240" fill="#ffffff" />
            <path d="M256 230 Q 322 190 342 140 Q 292 140 256 200" fill="#ffffff" />
          </svg>
          <div>
            <h1 className="text-lg font-bold leading-tight tracking-tight text-primary">
              {t.title}
            </h1>
            <p className="text-xs font-medium text-muted-foreground">
              {t.subtitle}
            </p>
          </div>
        </div>

        {/* Right Action Bar */}
        <div className="flex items-center space-x-2">
          {/* Online/Offline Status Indicator */}
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
              isOnline
                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
            }`}
          >
            <span
              className={`mr-1 h-1.5 w-1.5 rounded-full ${
                isOnline ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
            {isOnline ? t.online : t.offline}
          </span>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Toggle Theme"
          >
            {theme === 'light' ? (
              // Moon Icon
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            ) : (
              // Sun Icon
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            )}
          </button>

          {/* Language Selector */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as 'en' | 'hi' | 'kn')}
            className="h-9 rounded-lg border border-border bg-background px-2 py-1 text-sm font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="en">EN</option>
            <option value="hi">हिंदी</option>
            <option value="kn">ಕನ್ನಡ</option>
          </select>
        </div>
      </div>

      {/* Banner for PWA Install Prompt */}
      {isInstallable && (
        <div className="bg-primary-light border-t border-border px-4 py-2 text-center transition-all">
          <button
            onClick={handleInstallClick}
            className="inline-flex items-center justify-center rounded-full bg-primary px-4 py-1 text-xs font-bold text-primary-foreground shadow-sm hover:opacity-90 active:scale-95"
          >
            <svg className="mr-1 h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {t.install}
          </button>
        </div>
      )}
    </header>
  );
}
