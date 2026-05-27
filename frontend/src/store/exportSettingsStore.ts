'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { desktopBridge } from '@/lib/desktopBridge';

type ExportSettingsState = {
  export_directory: string;
  auto_save_enabled: boolean;
  initialized: boolean;
  initialize: () => Promise<void>;
  setExportDirectory: (path: string) => void;
  setAutoSaveEnabled: (enabled: boolean) => void;
  chooseExportFolder: () => Promise<void>;
  folderPickerUnsupported: boolean;
  dismissFolderPickerUnsupported: () => void;
};

export const useExportSettingsStore = create<ExportSettingsState>()(persist((set, get) => ({
  export_directory: '~/Videos/ClipperAI',
  auto_save_enabled: true,
  initialized: false,
  folderPickerUnsupported: false,
  initialize: async () => {
    if (get().initialized) return;
    const export_directory = await desktopBridge.getExportPath();
    set({ export_directory, initialized: true });
    console.log('[EXPORT DIRECTORY INITIALIZED]', { export_directory });
    console.log('[AUTO SAVE ENABLED]', { enabled: get().auto_save_enabled });
  },
  setExportDirectory: (export_directory) => set({ export_directory }),
  setAutoSaveEnabled: (auto_save_enabled) => set({ auto_save_enabled }),
  chooseExportFolder: async () => {
    const selected = await desktopBridge.selectFolder(get().export_directory);
    if (!selected) {
      set({ folderPickerUnsupported: !window.desktopAPI?.selectFolder && typeof window.showDirectoryPicker !== 'function' });
      return;
    }
    set({ export_directory: selected.path, folderPickerUnsupported: false });
  },
  dismissFolderPickerUnsupported: () => set({ folderPickerUnsupported: false }),
}), {
  name: 'clipper-export-settings-store',
  partialize: (state) => ({
    export_directory: state.export_directory,
    auto_save_enabled: state.auto_save_enabled,
  }),
}));
