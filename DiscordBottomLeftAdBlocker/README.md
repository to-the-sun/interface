# Discord Bottom-Left Ad Blocker

An advanced, elegant, and 100% flicker-free advertisement and promotion blocker tailored specifically for the Discord web app (`https://discord.com`).

This project provides two distinct ways to block ads depending on your preference:
1. **Chrome Extension (Manifest V3)**: A lightweight, standalone extension with a dedicated dark-themed settings and stats popup.
2. **Tampermonkey Userscript**: A seamless, all-in-one script that integrates a beautiful settings widget directly into Discord's native user settings button bar!

---

## 🚀 Key Features

* **Instantaneous CSS Injection (`document_start`)**: Injects stylesheet rules before the DOM begins rendering. This guarantees **zero visual flicker or pop-in**—promotions and ads are blocked before they are ever drawn.
* **Targeted Outer Container Blocker**: Uses CSS `:has()` rules and dynamic parent-chain climbing algorithms (`findHighestSafeQuestContainer`) to target and hide the entire outer Quest panel card box in the bottom-left sidebar while leaving user profile, voice, and RTC panels 100% intact.
* **Geometric & Keyword Callout Blocking**: Dynamically intercepts tooltips and popouts (like "Try Nitro" or "New Quest available") pointing to the bottom-left corner of the screen using geometric coordinates and ad-related keyword analysis.
* **Granular Settings**: Customize what you block:
  * **Discord Quests**: Sponsored games and activities (using explicit developer-class prefixes and parent walking to prevent hash collisions and squashed/crumpled containers).
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

### CSS Injection & Outer Container Targeting
Static injection of display rules uses `:has()` parent selectors to collapse outer Quest card wrappers:
```css
div[class*="panels_"] > *:has([class*="quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
div[class*="activityPanel_"]:has([class*="quest" i]),
.quests-container,
.quest-promo-banner,
.quest-progress-bar,
[class*="questsContainer"],
[class*="questsCard"],
[class*="questsWrapper"],
[class*="questTile"],
[class*="questBar"],
[class*="questCard"],
[class*="questPanel"],
[class*="questContainer"],
[class*="questWrapper"],
[class*="questBox"],
div[aria-label="Quests"],
div[class*="promotions_"],
div[class*="promo_"],
button[aria-label="Send a gift"],
a[data-list-item-id$="___nitro"],
a[data-list-item-id*="shop"] {
  display: none !important;
}
```

### Heuristic Analysis & Parent-Chain Climbing
The script watches DOM insertions via `MutationObserver` and dynamically flags promotional elements based on active user preferences:
1. **Quest Elements & Outer Cards**: Leverages parent-chain walking (`findHighestSafeQuestContainer`) and `:has()` rules to collapse the entire Quest tile box so no squashed banner or brown tab remains, while targeting specific developer-class prefixes (`questTile`, `questsContainer`, `questCard`, `quest_`) and using explicit user profile negation filters to avoid hiding main user panel components.
2. **Nitro & Shop Promotions**: Intercepts Nitro gift buttons, store link items, and premium subscription callouts.
3. **Bottom-Left Popup Callouts**: Analyzes absolute-positioned tooltips and popouts rendered near the bottom-left corner (`left < 360` & `top > innerHeight - 350`) containing promotional keywords.
