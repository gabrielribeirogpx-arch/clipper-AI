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
  wordTokens: (line: string, activeWordIndex?: number) => CaptionWordToken[];
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

const splitSemanticChunks = (text: string, maxWordsPerChunk = 2): string[] => {
  const normalized = text.trim().replace(/\s+/g, ' ');
  if (!normalized) return [];

  const phraseParts = normalized
    .split(/([,;:.!?])/)
    .reduce<string[]>((acc, part, index, arr) => {
      if (!part.trim()) return acc;
      if (/^[,;:.!?]$/.test(part) && acc.length > 0) {
        acc[acc.length - 1] = `${acc[acc.length - 1]}${part}`;
        return acc;
      }
      const next = arr[index + 1];
      if (next && /^[,;:.!?]$/.test(next)) {
        acc.push(`${part.trim()}${next}`);
        return acc;
      }
      acc.push(part.trim());
      return acc;
    }, []);

  const chunks: string[] = [];
  for (const phrase of phraseParts) {
    const words = safeSplit(phrase);
    if (words.length <= maxWordsPerChunk) {
      chunks.push(words.join(' '));
      continue;
    }
    for (let i = 0; i < words.length; i += maxWordsPerChunk) {
      chunks.push(words.slice(i, i + maxWordsPerChunk).join(' '));
    }
  }
  return chunks;
};

const splitCinematic = (text: string): string[] => {
  const words = safeSplit(text);
  if (words.length <= 4) return [words.join(' ')];
  const middle = Math.ceil(words.length / 2);
  return [words.slice(0, middle).join(' '), words.slice(middle).join(' ')];
};

const baseTokens = (line: string, activeWordIndex = 0, uppercase = false): CaptionWordToken[] => {
  const words = line.split(' ').filter(Boolean);
  const activeIndex = Math.max(0, Math.min(activeWordIndex, Math.max(words.length - 1, 0)));

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
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(18px, 1.9vw, 26px)', letterSpacing: '0.008em', lineHeight: 1.02 },
    style: { baseColor: '#F6F8FC', highlightedColor: '#FFD028', stroke: '1px rgba(0,0,0,0.58)', textShadow: '0 2px 6px rgba(0,0,0,0.36)', glowFilter: 'drop-shadow(0 0 1px rgba(255,208,40,.08))' },
    animation: { lineInitial: { opacity: 0, y: 3, scale: 0.99 }, lineAnimate: { opacity: 1, y: 0, scale: 1 }, lineTransition: { duration: 0.08, ease: 'easeOut' }, wordActiveScale: 1.06 },
    splitText: (text) => splitSemanticChunks(text, 2),
    wordTokens: (line, activeWordIndex) => baseTokens(line, activeWordIndex)
  },
  tiktok: {
    preset: 'tiktok',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-2 z-30 md:inset-x-5',
      innerClassName: 'mx-auto rounded-xl px-1.5 py-1 md:px-3 md:py-1.5',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[10%]', middle: 'top-[45%] -translate-y-1/2', bottom: 'bottom-[13%]' },
      maxWidth: '70%'
    },
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(22px, 2.8vw, 38px)', letterSpacing: '0.014em', lineHeight: 0.95, textTransform: 'uppercase' },
    style: { baseColor: '#FFFFFF', highlightedColor: '#FFD028', stroke: '1.2px rgba(0,0,0,0.9)', textShadow: '0 2px 7px rgba(0,0,0,0.48)', glowFilter: 'drop-shadow(0 0 1px rgba(255,208,40,.12))' },
    animation: { lineInitial: { opacity: 0, scale: 0.97, y: 4 }, lineAnimate: { opacity: 1, scale: 1, y: 0 }, lineTransition: { duration: 0.08, ease: 'easeOut' }, wordActiveScale: 1.09 },
    splitText: (text) => splitSemanticChunks(text, 2),
    wordTokens: (line, activeWordIndex) => baseTokens(line, activeWordIndex, true)
  },
  cinematic: {
    preset: 'cinematic',
    layout: {
      containerClassName: 'pointer-events-none absolute inset-x-4 z-30 md:inset-x-8',
      innerClassName: 'mx-auto rounded-lg px-2 py-1.5 md:px-4 md:py-2',
      lineClassName: 'text-center',
      positionClass: { top: 'top-[11%]', middle: 'top-[46%] -translate-y-1/2', bottom: 'bottom-[15%]' },
      maxWidth: '70%'
    },
    typography: { fontFamily: 'Montserrat, Anton, Arial Black, sans-serif', fontWeight: 900, fontSize: 'clamp(20px, 2.3vw, 32px)', letterSpacing: '0.016em', lineHeight: 1.02 },
    style: { baseColor: '#F2F5FA', highlightedColor: '#FFD028', stroke: '1.1px rgba(0,0,0,0.7)', textShadow: '0 2px 8px rgba(0,0,0,0.42)', glowFilter: 'drop-shadow(0 0 1px rgba(255,208,40,.1))' },
    animation: { lineInitial: { opacity: 0, y: 4, scale: 0.98 }, lineAnimate: { opacity: 1, y: 0, scale: 1 }, lineTransition: { duration: 0.1, ease: 'easeOut' }, wordActiveScale: 1.07 },
    splitText: (text) => splitSemanticChunks(text, 2),
    wordTokens: (line, activeWordIndex) => baseTokens(line, activeWordIndex)
  },
  hormozi: null as unknown as CaptionTheme,
  neon: null as unknown as CaptionTheme,
};

CAPTION_THEMES.hormozi = CAPTION_THEMES.tiktok;
CAPTION_THEMES.neon = CAPTION_THEMES.cinematic;

export const resolveTheme = (preset: CaptionPreset): CaptionTheme => CAPTION_THEMES[preset] ?? CAPTION_THEMES.cinematic;
