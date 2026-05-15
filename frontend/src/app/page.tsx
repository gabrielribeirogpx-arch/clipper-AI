import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-black p-6">
      <h1 className="mb-6 text-2xl font-bold">Clipper AI Timeline Editor</h1>
      <div className="grid gap-6 lg:grid-cols-[360px_1fr_340px]">
        <VideoPreview />
        <TimelineTracks />
        <InspectorPanel />
      </div>
    </main>
  );
}
