'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseSpeechProps {
  language: 'en' | 'hi' | 'kn';
  onTranscriptComplete?: (text: string) => void;
  onListeningChange?: (listening: boolean) => void;
  onError?: (errorMessage: string) => void;
}

export function useSpeech({
  language,
  onTranscriptComplete,
  onListeningChange,
  onError,
}: UseSpeechProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [useBrowserSTTOnly, setUseBrowserSTTOnly] = useState(false);
  const [useBrowserTTSOnly, setUseBrowserTTSOnly] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<any>(null); // For browser fallback
  const isFallbackActiveRef = useRef(false);

  // Map app languages to BCP-47 speech tags
  const getLanguageTag = useCallback((lang: 'en' | 'hi' | 'kn') => {
    switch (lang) {
      case 'hi':
        return 'hi-IN';
      case 'kn':
        return 'kn-IN';
      default:
        return 'en-US';
    }
  }, []);

  // Fetch API key config status from server to optimize fallbacks on load
  useEffect(() => {
    async function checkConfig() {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          // If neither Sarvam nor OpenAI keys are configured for voice, default to browser
          if (!data.has_stt) {
            console.log('Voice: No server-side STT API keys detected. Defaulting directly to browser SpeechRecognition.');
            setUseBrowserSTTOnly(true);
          }
          if (!data.has_tts) {
            console.log('Voice: No server-side TTS API keys detected. Defaulting directly to browser SpeechSynthesis.');
            setUseBrowserTTSOnly(true);
          }
        }
      } catch (err) {
        console.warn('Could not fetch server voice config, will fall back dynamically:', err);
      }
    }
    checkConfig();
  }, []);

  // Web Speech API browser fallback initialization
  const initBrowserSpeechRecognition = useCallback(() => {
    if (typeof window === 'undefined') return null;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = getLanguageTag(language);

    recognition.onstart = () => {
      setIsListening(true);
      if (onListeningChange) onListeningChange(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      if (onTranscriptComplete) {
        onTranscriptComplete(transcript);
      }
    };

    recognition.onerror = (event: any) => {
      console.warn('Browser Speech recognition error:', event.error);
      if (event.error === 'not-allowed') {
        if (onError) onError('Microphone access denied. Please check browser permissions.');
      } else {
        if (onError) onError(`Speech recognition error: ${event.error}`);
      }
      setIsListening(false);
      if (onListeningChange) onListeningChange(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      if (onListeningChange) onListeningChange(false);
    };

    return recognition;
  }, [language, getLanguageTag, onTranscriptComplete, onListeningChange, onError]);

  // Clean up recording structures
  const cleanupRecording = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (audioContextRef.current) {
      if (audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(console.error);
      }
      audioContextRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    mediaRecorderRef.current = null;
  }, []);

  // Browser-based Text-to-Speech (TTS) Fallback
  const speakTextBrowser = useCallback((text: string) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = getLanguageTag(language);

    const voices = window.speechSynthesis.getVoices();
    const targetLang = getLanguageTag(language);
    // Find matching voice or closest match
    const voice = voices.find((v) => v.lang === targetLang || v.lang.startsWith(language));
    if (voice) utterance.voice = voice;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, [language, getLanguageTag]);

  // Server Text-to-Speech (TTS) with Browser Fallback
  const speakText = useCallback(async (text: string) => {
    if (typeof window === 'undefined') return;

    // Stop currently speaking audio
    window.speechSynthesis?.cancel();

    if (useBrowserTTSOnly) {
      speakTextBrowser(text);
      return;
    }

    try {
      setIsSpeaking(true);
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
      });

      if (!response.ok) {
        throw new Error('TTS API failed, falling back');
      }

      const data = await response.json();
      if (!data.audio) {
        throw new Error('No audio returned, falling back');
      }

      // Play synthesized base64 WAV audio
      const audioUrl = `data:audio/wav;base64,${data.audio}`;
      const audio = new Audio(audioUrl);

      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = (e) => {
        console.error('Audio playback error, using browser TTS:', e);
        speakTextBrowser(text);
      };

      await audio.play();
    } catch (err) {
      console.warn('Premium TTS unavailable, falling back to browser:', err);
      setUseBrowserTTSOnly(true);
      speakTextBrowser(text);
    }
  }, [language, useBrowserTTSOnly, speakTextBrowser]);

  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.speechSynthesis?.cancel();
      setIsSpeaking(false);
    }
  }, []);

  // Process completed audio recording via API
  const processAudio = useCallback(async (audioBlob: Blob) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', audioBlob);
      formData.append('language', language);

      const response = await fetch('/api/stt', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Server STT API returned error status');
      }

      const data = await response.json();
      if (data.transcript && data.transcript.trim()) {
        if (onTranscriptComplete) {
          onTranscriptComplete(data.transcript);
        }
      } else {
        console.warn('Server transcribed empty text');
      }
    } catch (err) {
      console.warn('STT API failed. Switching to browser voice recognition fallback:', err);
      setUseBrowserSTTOnly(true);
      if (onError) {
        onError('Voice server offline. Switched to local browser voice typing. Tap mic to try again.');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [language, onTranscriptComplete, onError]);

  // Silence Detection / Voice Activity Detection (VAD) loop
  const startSilenceDetection = useCallback(() => {
    if (!analyserRef.current || !audioContextRef.current) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.fftSize;
    const dataArray = new Float32Array(bufferLength);

    let lastActiveTime = Date.now();
    const SILENCE_TIMEOUT = 1800; // 1.8 seconds of continuous silence to stop
    const VOLUME_THRESHOLD = 0.012; // Noise gate threshold

    const checkVolume = () => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return;

      analyser.getFloatTimeDomainData(dataArray);

      // Calculate Root Mean Square (RMS) volume
      let sumSquares = 0;
      for (let i = 0; i < bufferLength; i++) {
        sumSquares += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sumSquares / bufferLength);

      const now = Date.now();
      if (rms > VOLUME_THRESHOLD) {
        lastActiveTime = now;
      } else if (now - lastActiveTime > SILENCE_TIMEOUT) {
        console.log('VAD: Silence detected. Automatically stopping recording.');
        stopListening();
        return;
      }

      requestAnimationFrame(checkVolume);
    };

    requestAnimationFrame(checkVolume);
  }, []);

  // Stop Speech Recognition
  const stopListening = useCallback(() => {
    if (isFallbackActiveRef.current || useBrowserSTTOnly) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          console.error(e);
        }
      }
      isFallbackActiveRef.current = false;
      setIsListening(false);
      if (onListeningChange) onListeningChange(false);
      return;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop();
      } catch (err) {
        console.error('Error stopping MediaRecorder:', err);
      }
    }

    cleanupRecording();
    setIsListening(false);
    if (onListeningChange) onListeningChange(false);
  }, [cleanupRecording, useBrowserSTTOnly, onListeningChange]);

  // Start Speech Recognition
  const startListening = useCallback(async () => {
    // Stop any ongoing speech playback
    stopSpeaking();
    cleanupRecording();

    if (typeof window === 'undefined') return;

    // Direct Browser SpeechRecognition Fallback
    if (useBrowserSTTOnly) {
      const recognition = initBrowserSpeechRecognition();
      if (recognition) {
        recognitionRef.current = recognition;
        isFallbackActiveRef.current = true;
        try {
          recognition.start();
        } catch (e) {
          console.error('Failed to start browser Web Speech recognition:', e);
          if (onError) onError('Could not initialize browser microphone.');
        }
      } else {
        if (onError) onError('Voice input is not supported in this browser. Please type.');
      }
      return;
    }

    // Server-side recording pipeline
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      // Initialize VAD Silence Detection
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioContextClass();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      audioChunksRef.current = [];
      const options = { mimeType: 'audio/webm' };
      const mediaRecorder = new MediaRecorder(stream, options);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (audioBlob.size > 1000) {
          processAudio(audioBlob);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250); // Get chunks every 250ms

      setIsListening(true);
      if (onListeningChange) onListeningChange(true);

      startSilenceDetection();
    } catch (err: any) {
      console.warn('Server MediaRecorder failed to initialize, switching to browser API:', err);
      setUseBrowserSTTOnly(true);
      
      const recognition = initBrowserSpeechRecognition();
      if (recognition) {
        recognitionRef.current = recognition;
        isFallbackActiveRef.current = true;
        try {
          recognition.start();
        } catch (e) {
          console.error('Failed to start browser Web Speech recognition:', e);
          if (onError) onError('Could not initialize microphone. Please check settings.');
        }
      } else {
        if (onError) onError('Microphone access is denied or not supported on this browser.');
      }
    }
  }, [
    cleanupRecording,
    initBrowserSpeechRecognition,
    processAudio,
    startSilenceDetection,
    onListeningChange,
    onError,
    stopSpeaking,
    useBrowserSTTOnly,
  ]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      cleanupRecording();
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [cleanupRecording]);

  return {
    isListening,
    isSpeaking,
    isProcessing,
    startListening,
    stopListening,
    speakText,
    stopSpeaking,
    hasSupport: typeof window !== 'undefined' && (!!navigator.mediaDevices || !!(window as any).webkitSpeechRecognition),
  };
}
