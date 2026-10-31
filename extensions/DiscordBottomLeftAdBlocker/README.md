# Discord & Freebuff Ad Blocker

An advanced, elegant, and flicker-free ad blocking solution tailored for Discord (`https://discord.com`) and Freebuff (`https://freebuff.com`).

* **Discord**: Retains its native 100% flicker-free advertisement removal and panel collapsing (`display: none !important`), protecting your user profile, voice, and RTC controls.
* **Freebuff.com**: Applies an opaque black rectangle overlay directly over ads (sidebar billboard cards and prompt composer partner placements), neutralizing ads while preserving page structure and layout stability.

This project provides two distinct ways to block ads depending on your preference:
1. **Chrome Extension (Manifest V3)**: A lightweight, standalone extension with a dedicated dark-themed settings and stats popup.
2. **Tampermonkey Userscript**: A seamless, all-in-one script that integrates directly into Discord's native button bar and protects Freebuff.com tabs.

---

## 🚀 Key Features

* **Freebuff.com Opaque Black Rectangle Overlay**: Neutralizes sidebar ad cards (billboards, gravity ads) and composer partner ads by drawing an opaque solid black overlay (`#000000`, 100% opacity) directly over ad boundaries without removing elements or altering chat box layouts.
* **Discord Native Flicker-Free Ad Removal**: Blocks Quests, Nitro promotions, store items, and popup callouts cleanly and instantaneously at `document_start`.
* **Zero Layout Pop-in**: Injects stylesheet rules before the DOM begins rendering.
* **Live Statistics Counter**: See exactly how many advertisements and promotions have been neutralized in real-time, with an option to reset at any time.

---

## 🛠 Installation Instructions

### Option A: Chrome Extension (Recommended)

1. **Open Extensions Page**: Open Google Chrome (or any Chromium browser like Brave, Edge, Opera) and navigate to `chrome://extensions/`.
2. **Enable Developer Mode**: In the top-right corner, toggle the **Developer mode** switch to **ON**.
3. **Load Unpacked Extension**: Click the **Load unpacked** button in the top-left corner.
4. **Select Directory**: Select the `extensions/DiscordBottomLeftAdBlocker/chrome-extension/` directory from this project.
5. **Start Blocking**: Pin the extension to your toolbar and visit [Discord](https://discord.com/app) or [Freebuff](https://freebuff.com/app).

### Option B: Tampermonkey Userscript

1. **Install Userscript Manager**: Install [Tampermonkey](https://www.tampermonkey.net/) or [Violentmonkey](https://violentmonkey.github.io/) from your browser's extension store.
2. **Create New Script**: Open the Tampermonkey dashboard and click the **+** (Create a new script) button.
3. **Paste Code**: Copy the entire content of `extensions/DiscordBottomLeftAdBlocker/userscript/discord-adblocker.user.js` and paste it into the editor.
4. **Save**: Press `Ctrl + S` (or click File -> Save).
5. **Integrated Settings Widget**: Open [Discord](https://discord.com/app). Next to your user profile settings gear icon in the bottom-left corner, click the shield icon to open the configuration panel!
