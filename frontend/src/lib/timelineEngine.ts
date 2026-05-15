import { ClipBlock } from '@/store/timelineStore';

export const secondsToPixels = (seconds: number, pxPerSecond: number) => seconds * pxPerSecond;
export const pixelsToSeconds = (pixels: number, pxPerSecond: number) => pixels / pxPerSecond;
export const blockDuration = (block: ClipBlock) => block.end - block.start;
