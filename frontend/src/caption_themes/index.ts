import { CSSProperties } from 'react';
import { CaptionPosition, CaptionPreset } from '@/store/timelineStore';

export type CaptionWordToken = { text: string; isHighlighted: boolean };

export type ThemeLayout = {
  containerClassName: string;
  innerClassName: string;
  lineClassName: string;
  positionClass: Record<CaptionPosition, string>;
  maxWidth: string;
};

export type ThemeTypography = {
  textTransform?: CSSProperties['textTransform'];
  fontFamily: string;
  fontWeight: number;
  fontSize: string;
  letterSpacing: string;
  lineHeight: number;
};

export type ThemeStyle = {
  baseColor: string;
  highlightedColor: string;
  stroke: string;
  textShadow: string;
  glowFilter: string;
  backgroundBox?: string;
  activeBackgroundBox?: string;
};

export type ThemeAnimation = {
  lineInitial: { opacity: number; y?: number; scale?: number };
  lineAnimate: { opacity: number; y?: number; scale?: number };
  lineTransition: { duration: number; ease: 'easeOut' | 'easeInOut' };
  wordActiveScale: number;
};

export type CaptionTheme = {
  preset: CaptionPreset;
  layout: ThemeLayout;
  typography: ThemeTypography;
  style: ThemeStyle;
  animation: ThemeAnimation;
  splitText: (text: string) => string[];
  wordTokens: (line: string, heroWord: string) => CaptionWordToken[];
};

const safeSplit = (text: string): string[] => text.trim().split(/\s+/).filter(Boolean);

const splitBalanced = (text: string, wordsPerLine = 3, maxLines = 2): string[] => {
  const words = safeSplit(text);
  if (words.length <= wordsPerLine) return [words.join(' ')];

  const lines: string[] = [];
  for (let i = 0; i < words.length; i += wordsPerLine) {
    if (lines.length >= maxLines) break;
    lines.push(words.slice(i, i + wordsPerLine).join(' '));
  }
  return lines;
};

const splitMicroChunks = (text: string, chunkSizes: number[] = [2, 3]): string[] => {
  const words = safeSplit(text);
  if (words.length === 0) return [];

  const chunks: string[] = [];
  let cursor = 0;
  let step = 0;

  while (cursor < words.length) {
    const requestedSize = chunkSizes[step % chunkSizes.length] ?? 2;
    const remaining = words.length - cursor;
    const size = Math.max(1, Math.min(requestedSize, remaining));
    chunks.push(words.slice(cursor, cursor + size).join(' '));
    cursor += size;
    step += 1;
  }

  return chunks;
};

const splitCinematic = (text: string): string[] => {
  const words = safeSplit(text);
  if (words.length <= 4) return [words.join(' ')];
  const middle = Math.ceil(words.length / 2);
  return [words.slice(0, middle).join(' '), words.slice(middle).join(' ')];
};

const baseTokens = (line: string, heroWord: string, uppercase = false): CaptionWordToken[] => {
  const words = line.split(' ').filter(Boolean);
  const hero = heroWord.toLowerCase();
  const heroIndex = words.findIndex((word) => hero.length > 0 && word.toLowerCase().includes(hero));
  const fallbackIndex = words.length > 1 ? 1 : 0;
  const activeIndex = heroIndex >= 0 ? heroIndex : fallbackIndex;

  return words.map((word, index) => ({
    text: uppercase ? word.toUpperCase() : word,
    isHighlighted: index === activeIndex
  }));
};

export const CAPTION_THEMES: Record<CaptionPreset, CaptionTheme> = {
  minimal: {
    preset: 'minimal',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-3 z-30 md:inset-x-6',
      innerClassName: 'mx-auto rounded-lg px-2 py-1 md:px-3 md:py-1.5',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[10%]', middle: 'top-[44%] -translate-y-1/2', bottom: 'bottom-[14%]' },
      maxWidth: 'min(58vw, 460px)'
    },
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(22px, 2.3vw, 32px)', letterSpacing: '0.01em', lineHeight: 1.14 },
    style: { baseColor: '#F6F8FC', highlightedColor: '#FFD028', stroke: '1.1px rgba(0,0,0,0.65)', textShadow: '0 3px 8px rgba(0,0,0,0.42)', glowFilter: 'drop-shadow(0 0 3px rgba(255,208,40,.16))' },
    animation: { lineInitial: { opacity: 0, y: 6, scale: 0.97 }, lineAnimate: { opacity: 1, y: 0, scale: 1 }, lineTransition: { duration: 0.14, ease: 'easeOut' }, wordActiveScale: 1.09 },
    splitText: (text) => splitMicroChunks(text, [2]),
    wordTokens: (line, heroWord) => baseTokens(line, heroWord)
  },
  tiktok: {
    preset: 'tiktok',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-2 z-30 md:inset-x-5',
      innerClassName: 'mx-auto rounded-xl px-1.5 py-1 md:px-3 md:py-1.5',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[10%]', middle: 'top-[45%] -translate-y-1/2', bottom: 'bottom-[13%]' },
      maxWidth: 'min(64vw, 520px)'
    },
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(30px, 4vw, 60px)', letterSpacing: '0.018em', lineHeight: 1.02, textTransform: 'uppercase' },
    style: { baseColor: '#FFFFFF', highlightedColor: '#FFD028', stroke: '1.8px rgba(0,0,0,0.94)', textShadow: '0 4px 10px rgba(0,0,0,0.62)', glowFilter: 'drop-shadow(0 0 4px rgba(255,208,40,.2))' },
    animation: { lineInitial: { opacity: 0, scale: 0.9, y: 8 }, lineAnimate: { opacity: 1, scale: 1, y: 0 }, lineTransition: { duration: 0.12, ease: 'easeOut' }, wordActiveScale: 1.2 },
    splitText: (text) => splitMicroChunks(text, [2, 3]),
    wordTokens: (line, heroWord) => baseTokens(line, heroWord, true)
  },
  cinematic: {
    preset: 'cinematic',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-4 z-30 md:inset-x-8',
      innerClassName: 'mx-auto rounded-lg px-2 py-1.5 md:px-4 md:py-2',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[11%]', middle: 'top-[46%] -translate-y-1/2', bottom: 'bottom-[15%]' },
      maxWidth: 'min(60vw, 500px)'
    },
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(24px, 2.9vw, 44px)', letterSpacing: '0.02em', lineHeight: 1.2 },
    style: { baseColor: '#F2F5FA', highlightedColor: '#FFD028', stroke: '1.3px rgba(0,0,0,0.76)', textShadow: '0 4px 12px rgba(0,0,0,0.5)', glowFilter: 'drop-shadow(0 0 3px rgba(255,208,40,.14))' },
    animation: { lineInitial: { opacity: 0, y: 8, scale: 0.96 }, lineAnimate: { opacity: 1, y: 0, scale: 1 }, lineTransition: { duration: 0.24, ease: 'easeInOut' }, wordActiveScale: 1.1 },
    splitText: (text) => splitMicroChunks(text, [3]),
    wordTokens: (line, heroWord) => baseTokens(line, heroWord)
  },
  hormozi: null as unknown as CaptionTheme,
  neon: null as unknown as CaptionTheme,
};

CAPTION_THEMES.hormozi = CAPTION_THEMES.tiktok;
CAPTION_THEMES.neon = CAPTION_THEMES.cinematic;

export const resolveTheme = (preset: CaptionPreset): CaptionTheme => CAPTION_THEMES[preset] ?? CAPTION_THEMES.cinematic;
