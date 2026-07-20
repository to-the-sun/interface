# Discord Bottom-Left Ad Blocker

An advanced, elegant, and 100% flicker-free advertisement and promotion blocker tailored specifically for the Discord web app (`https://discord.com`).

This project provides two distinct ways to block ads depending on your preference:
1. **Chrome Extension (Manifest V3)**: A lightweight, standalone extension with a dedicated dark-themed settings and stats popup.
2. **Tampermonkey Userscript**: A seamless, all-in-one script that integrates a beautiful settings widget directly into Discord's native user settings button bar!

---

## 🚀 Key Features

* **Instantaneous CSS Injection (`document_start`)**: Injects stylesheet rules before the DOM begins rendering. This guarantees **zero visual flicker or pop-in**—promotions and ads are blocked before they are ever drawn.
* **Intelligent Heuristic Blocker**: Discord obfuscates CSS class names (e.g. `panels_a4d3d2`). This blocker uses a smart positional heuristic: any child of the bottom-left `panels` container that is *not* your profile panel, voice connection panel, or game activity panel is identified as an ad and blocked automatically.
* **Geometric & Keyword Callout Blocking**: Dynamically intercepts overlay layers, tooltips, and popouts (like "Try Nitro" or "New Quest available") pointing to the bottom-left corner of the screen using geometric coordinates and ad-related keyword analysis.
* **Granular Settings**: Customize what you block:
  * **Discord Quests**: Sponsored games and activities.
  * **Nitro Promos & Gift Icon**: Hides "Send a Gift" buttons and subscription upsells.
  * **Popup Callouts**: Absolute-positioned tooltips targeting your settings panel.
* **Live Statistics Counter**: See exactly how many advertisements and promotions have been blocked in real-time, with option to reset at any time.

---

## 🛠 Installation Instructions

### Option A: Chrome Extension (Recommended)

1. **Download the Code**: Clone or download this repository.
2. **Open Extensions Page**: Open Google Chrome (or any Chromium browser like Brave, Edge, Opera) and navigate to `chrome://extensions/`.
3. **Enable Developer Mode**: In the top-right corner, toggle the **Developer mode** switch to **ON**.
4. **Load Unpacked Extension**: Click the **Load unpacked** button in the top-left corner.
5. **Select Directory**: Select the `DiscordBottomLeftAdBlocker/chrome-extension/` directory from this project.
6. **Start Blocking**: Pin the extension to your toolbar, open [Discord](https://discord.com/app), and enjoy an ad-free bottom-left panel!

### Option B: Tampermonkey Userscript

1. **Install Userscript Manager**: Install [Tampermonkey](https://www.tampermonkey.net/) or [Violentmonkey](https://violentmonkey.github.io/) from your browser's extension store.
2. **Create New Script**: Open the Tampermonkey dashboard and click the **+** (Create a new script) button.
3. **Paste Code**: Copy the entire content of `DiscordBottomLeftAdBlocker/userscript/discord-adblocker.user.js` and paste it into the editor.
4. **Save**: Press `Ctrl + S` (or click File -> Save).
5. **Integrated Settings Widget**: Open [Discord](https://discord.com/app). Next to your user profile settings gear icon in the bottom-left corner, you will see a new **Shield icon**. Click it to open a beautiful native Discord-themed configuration panel!

---

## 🧠 Under the Hood

### CSS Injection
Static injection of display rules prevents the browser's layout engine from rendering known ad elements:
```css
.quests-container,
.quest-promo-banner,
div[class*="questsContainer_"],
div[class*="questsButton_"],
div[aria-label="Quests"],
div[class*="promotions_"],
div[class*="promo_"],
button[aria-label="Send a gift"],
a[data-list-item-id$="___nitro"],
a[data-list-item-id*="shop"] {
  display: none !important;
}
```

### Heuristic Analysis
The script watches DOM insertions via `MutationObserver` and analyzes child elements of `div[class*="panels_"]`. The only legitimate child nodes of this area are:
1. **Profile Panel**: containing avatar and mute/deafen buttons (`[class*="container_"]`).
2. **RTC Voice Panel**: containing voice metrics and channel name (`[class*="rtcConnection_"]` or `[class*="connection_"]`).
3. **Activity Panel**: containing currently played games (`[class*="activityPanel_"]`).

Any other div element placed inside is treated as a promotional banner/advertisement, marked, cleanly hidden, and logged in the blocker's storage counter.
