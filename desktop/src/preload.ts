/**
 * DealForge Desktop — Electron Preload Script.
 *
 * Runs in a privileged context (Node + browser) but exposes only
 * a safe, explicitly defined API to the renderer via contextBridge.
 *
 * Add IPC handlers here as needed — never expose raw `ipcRenderer`
 * or `require` to the renderer process.
 */

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("dealforgeElectron", {
  /** App version from Electron */
  getVersion: () => ipcRenderer.invoke("app:version"),

  /** Platform info */
  platform: process.platform,

  /** Open a URL in the system default browser */
  openExternal: (url: string) => ipcRenderer.invoke("shell:openExternal", url),
});
