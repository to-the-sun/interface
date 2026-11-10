# SoundCloud Feed Default & Promoted Track Cleaner

A Manifest V3 Google Chrome extension that customizes SoundCloud (`soundcloud.com`) by:
1. **Setting the Feed page (`/feed`) as the default page** rather than the Home/Discover page (`/` or `/discover`).
2. **Routing the SoundCloud logo and Home buttons directly to the Feed page** upon click.
3. **Removing Promoted tracks** at the top of track lists and streams without interfering with regular tracks or page layout.
4. **Defaulting the Reposts toggle on the Feed page to OFF** automatically.
5. **Removing the ARTIST TOOLS panel** from the right sidebar.
6. **Removing the top promotional banner** (announcements and promos).
7. **Removing "Try Go+" and "Try Artist Pro"** upsell links from the header bar.

---

## Features

- **Instant Default Page Redirect**: Automatically redirects `soundcloud.com/`, `soundcloud.com/discover`, and `soundcloud.com/home` straight to `soundcloud.com/feed` at `document_start` using `location.replace` to prevent browser history clutter.
- **SPA History Navigation Handling**: Hooks into HTML5 history methods (`pushState`, `replaceState`, `popstate`) so internal client-side navigation seamlessly stays on the Feed.
- **Logo & Navigation Interception**: Automatically updates header logo links (`a.header__logoLink`) and captures navigation clicks to ensure that clicking the logo or Home always leads to your Feed.
- **Promoted Track Remover**: Removes sponsored and promoted tracks appearing at the top of stream and track lists (targeting `.soundContext__promoted`, `.promotedBadge`, `.sc-promoted-icon`, etc.) using pure CSS `:has()` rules and a dynamic `MutationObserver` that catches lazy-loaded tracks.
- **Reposts Default to OFF**: Automatically detects the Reposts filter toggle at the top of the feed and turns it off.
- **Promotional Panels & Upsell Removal**: Cleanly hides and removes the top promotional banner (e.g. vinyl studio, announcements), the ARTIST TOOLS sidebar panel, and the Try Go+ / Try Artist Pro upsell links.
- **Clean Dark Theme Popup**: Built-in popup interface allowing you to toggle each feature independently with real-time settings synchronization via `chrome.storage`.

---

## Installation

1. Open Google Chrome (or any Chromium-based browser such as Brave, Edge, or Opera).
2. Navigate to `chrome://extensions/` in your address bar.
3. Enable **Developer mode** using the toggle in the upper right corner.
4. Click **Load unpacked**.
5. Select the `extensions/SoundCloudFeedDefault` folder.
6. Visit [SoundCloud](https://soundcloud.com) — you will immediately land on your Feed page with promoted tracks, top banners, artist tools, and reposts cleanly filtered!

---

## File Structure

```
extensions/SoundCloudFeedDefault/
├── manifest.json       # Manifest V3 extension configuration
├── content.js          # Content script handling redirects, logo clicks, and DOM cleanup
├── styles.css          # CSS rules for immediate hiding of promoted tracks & promotional units
├── popup.html          # Extension popup UI
├── popup.js            # Settings toggle handler for popup
└── README.md           # Documentation
```
