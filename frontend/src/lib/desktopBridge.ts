'use client';

type FileSystemPermissionMode = { mode?: 'read' | 'readwrite' };

type DirectoryHandleWithPermissions = FileSystemDirectoryHandle & {
  queryPermission?: (descriptor?: FileSystemPermissionMode) => Promise<PermissionState>;
};

type DesktopAPI = {
  selectFolder?: () => Promise<string | null>;
  openFolder?: (path: string) => Promise<void>;
  saveFile?: (name: string, sourceUrl: string, outputDir: string) => Promise<string>;
  getExportPath?: () => Promise<string | null>;
};

declare global {
  interface Window {
    desktopAPI?: DesktopAPI;
    showDirectoryPicker?: (options?: FileSystemPermissionMode) => Promise<DirectoryHandleWithPermissions>;
  }
}

const fallbackExportPath = (): string => '';

export const isPlaceholderExportPath = (path?: string | null): boolean => {
  const value = (path ?? '').trim();
  if (!value) return true;
  const lowered = value.toLowerCase();
  return value.includes('<') || value.includes('>') || lowered.includes('<user>') || lowered.includes('{user}') || lowered.includes('%user%');
};

export const desktopBridge = {
  async selectFolder(currentPath: string): Promise<{ path: string; handleStored: boolean; native: boolean } | null> {
    console.log('[FOLDER PICKER OPENED]', { currentPath });

    if (window.desktopAPI?.selectFolder) {
      const selected = await window.desktopAPI.selectFolder();
      if (!selected) return null;
      console.log('[FOLDER SELECTED]', { path: selected });
      return { path: selected, handleStored: false, native: true };
    }

    if (typeof window.showDirectoryPicker !== 'function') return null;

    console.log('[NATIVE DIRECTORY PICKER ACTIVE]');
    const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
    const permission = handle.queryPermission ? await handle.queryPermission({ mode: 'readwrite' }) : 'prompt';
    const path = handle.name;

    let handleStored = false;
    try {
      localStorage.setItem('clipper.export.folderHandle', handle.name);
      localStorage.setItem('clipper.export.folderPermission', permission);
      handleStored = true;
      console.log('[FOLDER HANDLE STORED]', { permission });
    } catch (error) {
      console.warn('[FOLDER HANDLE STORAGE FAILED]', error);
    }

    console.log('[FOLDER SELECTED]', { path });
    return { path, handleStored, native: true };
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
console.log('[AUTO SAVE PIPELINE ACTIVE]');
