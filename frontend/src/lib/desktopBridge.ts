'use client';

type FileSystemPermissionMode = { mode?: 'read' | 'readwrite' };

type DirectoryHandleWithPermissions = FileSystemDirectoryHandle & {
  queryPermission?: (descriptor?: FileSystemPermissionMode) => Promise<PermissionState>;
};

type DesktopAPI = {
  openDirectoryPicker?: () => Promise<string | null>;
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

export const BROWSER_INTERNAL_SAVE_FOLDER_MESSAGE = 'No navegador, os clipes serão salvos na pasta interna do app. Para escolher uma pasta do PC, use a versão desktop.';
export const INTERNAL_APP_FOLDER_LABEL = 'Pasta interna do app';

export const isAbsoluteLocalPath = (path?: string | null): boolean => {
  const value = (path ?? '').trim();
  if (!value) return false;
  return /^(?:[a-zA-Z]:[\\/]|\\\\|\/)/.test(value);
};

export const isPlaceholderExportPath = (path?: string | null): boolean => {
  const value = (path ?? '').trim();
  if (!value) return true;
  const lowered = value.toLowerCase();
  return value.includes('<') || value.includes('>') || lowered.includes('<user>') || lowered.includes('{user}') || lowered.includes('%user%');
};

export const desktopBridge = {
  async selectFolder(currentPath: string): Promise<{ path: string; handleStored: boolean; native: boolean } | null> {
    console.log('[FOLDER PICKER OPENED]', { currentPath });

    const nativePicker = window.desktopAPI?.openDirectoryPicker ?? window.desktopAPI?.selectFolder;
    if (nativePicker) {
      const selected = await nativePicker();
      if (!selected) return null;
      console.log('[FOLDER SELECTED]', { path: selected });
      return { path: selected, handleStored: false, native: true };
    }

    // The browser File System Access API only exposes a handle/name, not a real
    // absolute OS path that the backend can write to. In web mode we therefore
    // fall back to the backend's internal app folder instead of sending a
    // relative folder name such as "Video" or "Clipes".
    if (typeof window.showDirectoryPicker === 'function') {
      console.log('[BROWSER DIRECTORY PICKER IGNORED_NO_ABSOLUTE_PATH]');
    }
    return null;
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
