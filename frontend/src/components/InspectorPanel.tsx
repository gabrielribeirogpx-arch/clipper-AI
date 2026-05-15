'use client';

import { useTimelineStore } from '@/store/timelineStore';

export function InspectorPanel() {
  const { subtitles, broll, updateBlock } = useTimelineStore();
  const selectedSubtitle = subtitles[0];
  const selectedBroll = broll[0];

  return (
    <div className="rounded-2xl border border-slate-700 bg-panel p-4">
      <h3 className="mb-4 text-sm font-semibold">Editor</h3>
      <label className="mb-2 block text-xs text-slate-400">Texto subtitle</label>
      <textarea
        value={selectedSubtitle.text}
        onChange={(e) => updateBlock('subtitles', selectedSubtitle.id, { text: e.target.value })}
        className="mb-4 min-h-24 w-full rounded bg-slate-900 p-2 text-sm"
      />
      <label className="mb-2 block text-xs text-slate-400">Timing B-roll (start)</label>
      <input
        type="number"
        step="0.1"
        value={selectedBroll.start}
        onChange={(e) => updateBlock('broll', selectedBroll.id, { start: Number(e.target.value) })}
        className="w-full rounded bg-slate-900 p-2 text-sm"
      />
    </div>
  );
}
