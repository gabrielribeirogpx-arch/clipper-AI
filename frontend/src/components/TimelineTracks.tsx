'use client';

import { memo, useMemo, useRef } from 'react';
import { useMounted } from '@/hooks/useMounted';
import { motion } from 'framer-motion';
import { TimelineBlock, TrackType, useTimelineStore } from '@/store/timelineStore';
import { pixelsToSeconds, secondsToPixels } from '@/lib/timelineEngine';

const trackStyles: Record<TrackType, string> = {
  subtitles:
    'from-cyan-500/88 via-sky-400/82 to-cyan-300/72 border-cyan-200/55 shadow-[0_12px_30px_rgba(14,165,233,.34)]',
  broll:
    'from-violet-500/88 via-purple-400/82 to-fuchsia-300/74 border-violet-200/55 shadow-[0_12px_30px_rgba(168,85,247,.34)]',
  hooks:
    'from-rose-500/94 via-orange-400/90 to-amber-300/84 border-rose-100/65 shadow-[0_14px_38px_rgba(251,113,133,.46)]',
  cuts:
    'from-amber-500/90 via-yellow-400/86 to-yellow-300/74 border-amber-100/65 shadow-[0_12px_32px_rgba(250,204,21,.38)]',
  effects:
    'from-fuchsia-500/88 via-purple-400/84 to-fuchsia-300/72 border-fuchsia-100/55 shadow-[0_12px_30px_rgba(217,70,239,.34)]'
};

const TRACK_HEIGHT = 88;
const SUBTITLE_MIN_SECONDS = 1.2;

const formatTime = (seconds: number) => {
  const total = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const getRulerStep = (zoom: number) => {
  if (zoom >= 2.4) return 0.5;
  if (zoom >= 1.6) return 1;
  if (zoom >= 1) return 2;
  if (zoom >= 0.7) return 4;
  return 8;
};

const layoutSubtitleLanes = (blocks: TimelineBlock[]) => {
  const lanes: number[] = [];
  const mapped = blocks
    .slice(0, 300)
    .sort((a, b) => a.start - b.start)
    .map((block) => {
      let lane = lanes.findIndex((end) => block.start >= end + 0.12);
      if (lane === -1) {
        lanes.push(block.end);
        lane = lanes.length - 1;
      } else {
        lanes[lane] = block.end;
      }
      return { block, lane };
    });

  return { mapped, laneCount: Math.max(1, lanes.length) };
};

export const TimelineTracks = memo(function TimelineTracks() {
  const { duration, currentTime, tracks, setCurrentTime, moveBlock, selectBlock, zoom, setZoom } = useTimelineStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const mounted = useMounted();
  const pxPerSecond = useMemo(() => 72 * zoom, [zoom]);
  const cursorLeft = secondsToPixels(currentTime, pxPerSecond);

  const rulerStep = useMemo(() => getRulerStep(zoom), [zoom]);
  const markers = useMemo(() => {
    const count = Math.ceil(duration / rulerStep) + 1;
    return Array.from({ length: count }, (_, idx) => {
      const time = idx * rulerStep;
      return {
        time,
        major: idx % 2 === 0,
        left: secondsToPixels(time, pxPerSecond)
      };
    });
  }, [duration, pxPerSecond, rulerStep]);

  const subtitleLayout = useMemo(() => layoutSubtitleLanes(tracks.subtitles), [tracks.subtitles]);

  if (!mounted) return <div className="h-[460px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <section className="rounded-[2.25rem] border border-white/10 bg-[#0b1120]/88 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.11),0_34px_96px_rgba(0,0,0,.65)] backdrop-blur-2xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.26em] text-slate-200">Cinematic Timeline</p>
        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#0a1122]/88 px-4 py-2">
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-slate-300">Zoom {zoom.toFixed(1)}x</span>
          <input type="range" min={0.5} max={3} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} className="timeline-zoom-slider w-56" />
        </div>
      </div>

      <div
        ref={containerRef}
        className="timeline-scrollbar relative overflow-x-auto overflow-y-hidden rounded-2xl border border-white/10 bg-[#050912] p-4 shadow-[inset_0_2px_22px_rgba(0,0,0,.55)]"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const timelineX = e.clientX - rect.left + e.currentTarget.scrollLeft;
          setCurrentTime(pixelsToSeconds(timelineX, pxPerSecond));
        }}
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setCurrentTime(pixelsToSeconds(e.clientX - rect.left + e.currentTarget.scrollLeft, pxPerSecond));
        }}
      >
        <div style={{ width: Math.max(secondsToPixels(duration, pxPerSecond), 1000) }} className="relative min-w-full">
          <div className="relative mb-4 h-14 overflow-hidden rounded-xl border border-white/10 bg-[#0b1324]">
            <div className="absolute inset-0 opacity-50 [background-image:linear-gradient(to_right,rgba(148,163,184,.2)_1px,transparent_1px)]" style={{ backgroundSize: `${pxPerSecond / 2}px 100%` }} />
            {markers.map((marker) => (
              <div key={marker.time} className="pointer-events-none absolute inset-y-0" style={{ left: marker.left }}>
                <div className={`w-px ${marker.major ? 'h-8 bg-slate-200/65' : 'h-5 bg-slate-300/40'}`} />
                {marker.major && <span className="absolute left-2 top-1 text-[10px] font-semibold tracking-[0.12em] text-slate-300">{formatTime(marker.time)}</span>}
              </div>
            ))}
          </div>

          <div className="pointer-events-none absolute inset-y-0 z-30" style={{ left: cursorLeft }}>
            <div className="-ml-[7px] h-4 w-4 rounded-full border border-rose-100/85 bg-rose-400 shadow-[0_0_18px_rgba(251,113,133,.95)]" />
            <div className="ml-0.5 h-[calc(100%-0.75rem)] w-[3px] rounded-full bg-rose-400 shadow-[0_0_20px_rgba(251,113,133,.95),0_0_56px_rgba(251,113,133,.6)]" />
          </div>

          <div className="grid gap-3">
            {(Object.keys(tracks) as TrackType[]).map((name) => {
              const subtitleMode = name === 'subtitles';
              const laneHeight = subtitleMode ? Math.max(1, subtitleLayout.laneCount) * 30 : TRACK_HEIGHT;
              const rowHeight = Math.max(TRACK_HEIGHT, laneHeight + 16);

              return (
                <div key={name} className="grid grid-cols-[160px_1fr] gap-3">
                  <div className="flex items-center rounded-xl border border-white/10 bg-white/[0.03] px-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-300">
                    {name}
                  </div>
                  <div className="relative overflow-hidden rounded-xl border border-white/10 bg-[#0b1324]/95" style={{ height: rowHeight }}>
                    <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,.035),transparent_30%,transparent_70%,rgba(255,255,255,.06))]" />
                    <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(to_right,rgba(148,163,184,.16)_1px,transparent_1px)]" style={{ backgroundSize: `${pxPerSecond / 4}px 100%` }} />
                    {subtitleMode
                      ? subtitleLayout.mapped.map(({ block, lane }) => {
                          const width = Math.max(secondsToPixels(block.end - block.start, pxPerSecond), secondsToPixels(SUBTITLE_MIN_SECONDS, pxPerSecond));
                          return (
                            <motion.div
                              key={block.id}
                              drag="x"
                              dragMomentum={false}
                              whileHover={{ y: -2, scale: 1.01 }}
                              onClick={() => {
                                setCurrentTime(block.start);
                                selectBlock(block.id);
                              }}
                              onDragEnd={(_, info) => {
                                const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                                moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                              }}
                              className={`absolute flex h-7 items-center rounded-lg border bg-gradient-to-r px-3 text-xs font-semibold text-white ${trackStyles[name]}`}
                              style={{ left: secondsToPixels(block.start, pxPerSecond), top: 8 + lane * 30, width }}
                            >
                              <span className="truncate">{block.label}</span>
                            </motion.div>
                          );
                        })
                      : tracks[name].slice(0, 300).map((block) => (
                          <motion.div
                            key={block.id}
                            drag="x"
                            dragMomentum={false}
                            whileHover={{ scale: 1.015, y: -2 }}
                            onClick={() => {
                              setCurrentTime(block.start);
                              selectBlock(block.id);
                            }}
                            onDragEnd={(_, info) => {
                              const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                              moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                            }}
                            className={`absolute top-2.5 flex h-[72px] items-center rounded-xl border bg-gradient-to-r px-4 text-sm font-semibold text-white ${trackStyles[name]} ${
                              name === 'hooks' ? 'ring-1 ring-rose-200/70' : ''
                            }`}
                            style={{ left: secondsToPixels(block.start, pxPerSecond), width: secondsToPixels(block.end - block.start, pxPerSecond) }}
                          >
                            <span className="truncate">{block.label}</span>
                            {name === 'hooks' && (
                              <span className="ml-2 rounded-full border border-rose-100/40 bg-black/35 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-rose-100">VIRAL</span>
                            )}
                            <span className="ml-auto mr-[-4px] h-8 w-1.5 rounded-full bg-white/35" />
                          </motion.div>
                        ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
});
