/**
 * DealForge Desktop — Electron Main Process.
 *
 * Opens the React frontend in a native BrowserWindow.
 * In development: loads http://localhost:5173 (Vite dev server).
 * In production: loads the built index.html from the frontend/dist folder.
 */

import { app, BrowserWindow, shell } from "electron";
import path from "path";

const isDev = process.env.NODE_ENV !== "production";

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 600,
    title: "DealForge",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    // Load the Vite dev server
    win.loadURL("http://localhost:5173");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    // Load the production build
    win.loadFile(
      path.join(__dirname, "..", "..", "frontend", "dist", "index.html")
    );
  }

  // Open external links in the system browser, not in Electron
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
