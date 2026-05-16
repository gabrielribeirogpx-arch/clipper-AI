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

const splitCinematic = (text: string): string[] => {
  const words = safeSplit(text);
  if (words.length <= 4) return [words.join(' ')];
  const middle = Math.ceil(words.length / 2);
  return [words.slice(0, middle).join(' '), words.slice(middle).join(' ')];
};

const baseTokens = (line: string, heroWord: string, uppercase = false): CaptionWordToken[] => {
  const hero = heroWord.toLowerCase();
  return line.split(' ').filter(Boolean).map((word) => ({
    text: uppercase ? word.toUpperCase() : word,
    isHighlighted: hero.length > 0 && word.toLowerCase().includes(hero)
  }));
};

export const CAPTION_THEMES: Record<CaptionPreset, CaptionTheme> = {
  minimal: {
    preset: 'minimal',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-3 z-30 md:inset-x-6',
      innerClassName: 'mx-auto rounded-xl px-2 py-1 md:px-4 md:py-2',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[9%]', middle: 'top-[46%] -translate-y-1/2', bottom: 'bottom-[12%]' },
      maxWidth: 'min(88vw, 860px)'
    },
    typography: { fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 500, fontSize: 'clamp(20px, 2.4vw, 34px)', letterSpacing: '0.012em', lineHeight: 1.24 },
    style: { baseColor: '#FFFFFF', highlightedColor: '#EAF2FF', stroke: '0.9px rgba(0,0,0,0.7)', textShadow: '0 3px 10px rgba(0,0,0,0.45)', glowFilter: 'drop-shadow(0 0 6px rgba(255,255,255,.15))' },
    animation: { lineInitial: { opacity: 0, y: 8 }, lineAnimate: { opacity: 1, y: 0 }, lineTransition: { duration: 0.24, ease: 'easeOut' }, wordActiveScale: 1.03 },
    splitText: (text) => splitBalanced(text, 4, 2),
    wordTokens: (line, heroWord) => baseTokens(line, heroWord)
  },
  tiktok: {
    preset: 'tiktok',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-2 z-30 md:inset-x-5',
      innerClassName: 'mx-auto rounded-2xl px-2 py-1 md:px-4 md:py-2',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[8%]', middle: 'top-[46%] -translate-y-1/2', bottom: 'bottom-[11%]' },
      maxWidth: 'min(94vw, 940px)'
    },
    typography: { fontFamily: 'Montserrat, Arial Black, sans-serif', fontWeight: 800, fontSize: 'clamp(28px, 3.9vw, 62px)', letterSpacing: '0.02em', lineHeight: 1.03, textTransform: 'uppercase' },
    style: { baseColor: '#FFFFFF', highlightedColor: '#FFD60A', stroke: '2.8px rgba(0,0,0,0.98)', textShadow: '0 6px 0 rgba(0,0,0,0.95), 0 14px 26px rgba(0,0,0,0.7)', glowFilter: 'drop-shadow(0 0 16px rgba(255,214,10,.34))', backgroundBox: 'rgba(0,0,0,0.44)', activeBackgroundBox: 'rgba(255,214,10,0.18)' },
    animation: { lineInitial: { opacity: 0, scale: 0.86, y: 12 }, lineAnimate: { opacity: 1, scale: 1, y: 0 }, lineTransition: { duration: 0.16, ease: 'easeOut' }, wordActiveScale: 1.18 },
    splitText: (text) => splitBalanced(text, 2, 2),
    wordTokens: (line, heroWord) => baseTokens(line, heroWord, true)
  },
  cinematic: {
    preset: 'cinematic',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-4 z-30 md:inset-x-8',
      innerClassName: 'mx-auto rounded-xl px-3 py-2 md:px-5 md:py-3',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[10%]', middle: 'top-[47%] -translate-y-1/2', bottom: 'bottom-[14%]' },
      maxWidth: 'min(86vw, 900px)'
    },
    typography: { fontFamily: 'Inter, Helvetica Neue, Arial, sans-serif', fontWeight: 600, fontSize: 'clamp(24px, 3.1vw, 48px)', letterSpacing: '0.042em', lineHeight: 1.32 },
    style: { baseColor: '#F8FBFF', highlightedColor: '#FFFFFF', stroke: '1.5px rgba(0,0,0,0.78)', textShadow: '0 5px 18px rgba(0,0,0,0.58)', glowFilter: 'drop-shadow(0 0 12px rgba(177,208,255,.22))' },
    animation: { lineInitial: { opacity: 0, y: 10 }, lineAnimate: { opacity: 1, y: 0 }, lineTransition: { duration: 0.42, ease: 'easeInOut' }, wordActiveScale: 1.04 },
    splitText: splitCinematic,
    wordTokens: (line, heroWord) => baseTokens(line, heroWord)
  },
  hormozi: null as unknown as CaptionTheme,
  neon: null as unknown as CaptionTheme,
};

CAPTION_THEMES.hormozi = CAPTION_THEMES.tiktok;
CAPTION_THEMES.neon = CAPTION_THEMES.cinematic;

export const resolveTheme = (preset: CaptionPreset): CaptionTheme => CAPTION_THEMES[preset] ?? CAPTION_THEMES.cinematic;
