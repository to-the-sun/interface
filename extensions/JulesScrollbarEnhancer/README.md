# Jules.google.com Scrollbar Enhancer

A Chrome Extension (Manifest V3) that enhances the `jules.google.com` interface with prominent, highly visible scrollbars equipped with clickable top and bottom arrows on all scrollable panels.

## Features

- **Prominent Scrollbars**: Replaces invisible or thin scrollbars with relatively big, clear scrollbars across all panels and scroll containers.
- **Clickable Top & Bottom Arrows**: Features clickable increment/decrement arrow buttons (`::-webkit-scrollbar-button`) at the top and bottom of vertical scrollbars (and left/right on horizontal scrollbars) for easy navigation.
- **Shadow DOM Support**: Ensures scrollbar rules apply to both light DOM elements and nested Shadow DOM Roots (such as code editors or custom web components).
- **Dark Mode & Light Mode**: Seamlessly adapts to system theme preferences (`prefers-color-scheme`) and site dark theme attributes (`[data-theme="dark"]`, `.dark`).
- **Customizable Options Popup**: Easily toggle the enhancement on/off or choose between Medium (14px), Big (18px), and Extra Big (22px) scrollbar sizes.

## Installation

1. Open Google Chrome (or any Chromium-based browser like Edge, Brave, Opera).
2. Navigate to `chrome://extensions/`.
3. Enable **Developer mode** in the top-right corner.
4. Click **Load unpacked** in the top-left corner.
5. Select the `extensions/JulesScrollbarEnhancer` folder from this repository.
6. Open or refresh [jules.google.com](https://jules.google.com) to enjoy custom scrollbars on all panels!
