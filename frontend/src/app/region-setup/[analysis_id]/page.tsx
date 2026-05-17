'use client';
import { useRouter } from 'next/navigation';
import { useTimelineStore } from '@/store/timelineStore';

export default function RegionSetupPage() {
  const router = useRouter();
  const { videoUrl, dualRegions, setDualRegions, generatedClips } = useTimelineStore();
  const presets = {
    podcast: { regionA: { x: 120, y: 80, width: 700, height: 700 }, regionB: { x: 1100, y: 80, width: 700, height: 700 } },
    gameplay: { regionA: { x: 80, y: 120, width: 600, height: 600 }, regionB: { x: 700, y: 60, width: 1180, height: 900 } },
    debate: { regionA: { x: 80, y: 180, width: 760, height: 760 }, regionB: { x: 1080, y: 180, width: 760, height: 760 } },
    reaction: { regionA: { x: 100, y: 80, width: 800, height: 800 }, regionB: { x: 1020, y: 140, width: 820, height: 820 } },
  } as const;

  return <main className='p-6 text-white bg-black min-h-screen'>
    <h1 className='text-2xl font-bold mb-2'>Region Setup (16:9 Source)</h1>
    <p className='text-sm text-slate-300 mb-4'>[DUAL REGION SETUP OPENED]</p>
    <div className='aspect-video max-w-5xl relative border border-white/20'>
      {videoUrl ? <video src={videoUrl} className='w-full h-full' controls /> : <div className='p-8'>No source</div>}
      {(['regionA','regionB'] as const).map((k)=>{const r=dualRegions[k];return <div key={k} className='absolute border-2 border-cyan-300 bg-cyan-300/20' style={{left:`${(r.x/1920)*100}%`,top:`${(r.y/1080)*100}%`,width:`${(r.width/1920)*100}%`,height:`${(r.height/1080)*100}%`}} />})}
    </div>
    <div className='mt-4 flex gap-2'>{Object.entries(presets).map(([k,v])=><button key={k} className='px-3 py-2 bg-slate-800 rounded' onClick={()=>setDualRegions(v)}>{k}</button>)}</div>
    <div className='mt-4 p-3 border border-white/20 max-w-sm'>
      <div className='aspect-[9/16] bg-slate-900 relative'>
        <div className='h-1/2 border-b border-white/30 grid place-items-center'>Região A</div>
        <div className='h-1/2 grid place-items-center'>Região B</div>
      </div>
    </div>
    <button className='mt-6 px-4 py-2 bg-cyan-400 text-black rounded' onClick={()=>{console.log('[DUAL REGION CONFIG SAVED]'); console.log('[DUAL REGION GLOBAL FRAMING]', dualRegions); if(generatedClips.length>0) router.push('/editor')}}>Confirm Regions</button>
  </main>
}
