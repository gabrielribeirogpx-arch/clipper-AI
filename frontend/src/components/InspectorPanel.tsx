'use client';

import { useMemo } from 'react';
import { TrackType, useTimelineStore } from '@/store/timelineStore';

export function InspectorPanel() {
  const { tracks, selectedBlockId, updateBlock } = useTimelineStore();

  const selected = useMemo(() => {
    for (const track of Object.keys(tracks) as TrackType[]) {
      const hit = tracks[track].find((block) => block.id === selectedBlockId);
      if (hit) return { track, block: hit };
    }
    return null;
  }, [tracks, selectedBlockId]);

  if (!selected) return <div className="rounded-2xl border border-white/10 bg-white/5 p-4">Selecione um bloco.</div>;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur-xl">
      <h3 className="mb-4 text-sm font-semibold">Inspector Profissional</h3>
      <label className="mb-2 block text-xs text-slate-400">Texto</label>
      <textarea
        value={selected.block.text ?? ''}
        onChange={(e) => updateBlock(selected.track, selected.block.id, { text: e.target.value })}
        className="mb-4 min-h-24 w-full rounded bg-slate-900 p-2 text-sm"
      />
      <div className="grid grid-cols-2 gap-2">
        <input type="number" step="0.1" value={selected.block.start} onChange={(e) => updateBlock(selected.track, selected.block.id, { start: Number(e.target.value) })} className="rounded bg-slate-900 p-2 text-sm" />
        <input type="number" step="0.1" value={selected.block.end} onChange={(e) => updateBlock(selected.track, selected.block.id, { end: Number(e.target.value) })} className="rounded bg-slate-900 p-2 text-sm" />
      </div>
    </div>
  );
}
