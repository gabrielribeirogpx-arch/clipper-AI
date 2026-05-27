'use client';

type DesktopAPI = {
  selectFolder?: () => Promise<string | null>;
  openFolder?: (path: string) => Promise<void>;
  saveFile?: (name: string, sourceUrl: string, outputDir: string) => Promise<string>;
  getExportPath?: () => Promise<string | null>;
};

declare global {
  interface Window {
    desktopAPI?: DesktopAPI;
  }
}

const fallbackExportPath = (): string => {
  const platform = typeof navigator !== 'undefined' ? navigator.platform.toLowerCase() : '';
  if (platform.includes('win')) return 'C:/Users/<user>/Videos/ClipperAI';
  if (platform.includes('mac')) return '~/Movies/ClipperAI';
  return '~/Videos/ClipperAI';
};

export const desktopBridge = {
  async selectFolder(currentPath: string): Promise<string | null> {
    if (window.desktopAPI?.selectFolder) return window.desktopAPI.selectFolder();
    const selected = window.prompt('Choose Export Folder', currentPath);
    return selected && selected.trim().length > 0 ? selected.trim() : null;
  },
  async openFolder(path: string): Promise<void> {
    console.log('[OPEN EXPORT FOLDER]', { path });
    if (window.desktopAPI?.openFolder) return window.desktopAPI.openFolder(path);
  },
  async saveFile(name: string, sourceUrl: string, outputDir: string): Promise<string> {
    if (window.desktopAPI?.saveFile) return window.desktopAPI.saveFile(name, sourceUrl, outputDir);
    console.log('[CLIP AUTO SAVED]', { name, sourceUrl, outputDir });
    return `${outputDir}/${name}`;
  },
  async getExportPath(): Promise<string> {
    if (window.desktopAPI?.getExportPath) {
      const value = await window.desktopAPI.getExportPath();
      if (value) return value;
    }
    return fallbackExportPath();
  },
};

console.log('[DESKTOP BRIDGE READY]');
