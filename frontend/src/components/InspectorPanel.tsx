'use client';

import { useMemo } from 'react';
import { CaptionPosition, CaptionPreset, TrackType, useTimelineStore } from '@/store/timelineStore';

const CAPTION_POSITIONS: CaptionPosition[] = ['top', 'middle', 'bottom'];
const CAPTION_PRESETS: CaptionPreset[] = ['cinematic', 'tiktok', 'hormozi', 'minimal', 'neon'];

export function InspectorPanel() {
  const { tracks, selectedBlockId, updateBlock } = useTimelineStore();

  const selected = useMemo(() => {
    for (const track of Object.keys(tracks) as TrackType[]) {
      const hit = tracks[track].find((block) => block.id === selectedBlockId);
      if (hit) return { track, block: hit };
    }
    return null;
  }, [tracks, selectedBlockId]);

  if (!selected) return <div className="rounded-[2rem] border border-white/12 bg-white/[0.05] p-6">Selecione um bloco.</div>;

  return (
    <div className="rounded-[2.1rem] border border-white/15 bg-[#101a2e]/72 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.12),0_35px_90px_rgba(0,0,0,.5)] backdrop-blur-3xl">
      <h3 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-slate-200">Inspector</h3>
      <div className="space-y-4 rounded-2xl border border-white/10 bg-[#0b1224]/80 p-4">
        <label className="block text-xs uppercase tracking-[0.12em] text-slate-400">Texto</label>
        <textarea
          value={selected.block.text ?? ''}
          onChange={(e) => updateBlock(selected.track, selected.block.id, { text: e.target.value })}
          className="min-h-28 w-full rounded-xl border border-white/12 bg-[#070d1b] p-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50 focus:shadow-[0_0_0_3px_rgba(34,211,238,.16)]"
        />
      </div>
      {selected.track === 'subtitles' && (
        <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-[#0b1224]/80 p-4">
          <label className="block text-xs uppercase tracking-[0.12em] text-slate-400">Caption Position</label>
          <div className="grid grid-cols-3 gap-2">
            {CAPTION_POSITIONS.map((position) => (
              <button
                key={position}
                onClick={() => updateBlock(selected.track, selected.block.id, { style: { ...selected.block.style, captionPosition: position } })}
                className={`rounded-lg border px-2 py-2 text-xs font-semibold uppercase tracking-[0.08em] ${selected.block.style?.captionPosition === position ? 'border-cyan-300 bg-cyan-400/20 text-cyan-200' : 'border-white/10 bg-[#070d1b] text-slate-300'}`}
              >
                {position}
              </button>
            ))}
          </div>
          <label className="block text-xs uppercase tracking-[0.12em] text-slate-400">Preset</label>
          <select
            value={selected.block.style?.captionPreset ?? 'cinematic'}
            onChange={(e) => updateBlock(selected.track, selected.block.id, { style: { ...selected.block.style, captionPreset: e.target.value as CaptionPreset } })}
            className="w-full rounded-xl border border-white/12 bg-[#070d1b] p-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50"
          >
            {CAPTION_PRESETS.map((preset) => (
              <option key={preset} value={preset}>{preset}</option>
            ))}
          </select>
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-2xl border border-white/10 bg-[#0b1224]/80 p-4">
        <input type="number" step="0.1" value={selected.block.start} onChange={(e) => updateBlock(selected.track, selected.block.id, { start: Number(e.target.value) })} className="rounded-xl border border-white/12 bg-[#070d1b] p-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50" />
        <input type="number" step="0.1" value={selected.block.end} onChange={(e) => updateBlock(selected.track, selected.block.id, { end: Number(e.target.value) })} className="rounded-xl border border-white/12 bg-[#070d1b] p-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50" />
      </div>
    </div>
  );
}
