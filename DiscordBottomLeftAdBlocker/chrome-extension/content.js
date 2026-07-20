// Discord Bottom-Left Ad Blocker Content Script
// This script runs at document_start to inject styles instantly (preventing flicker)
// and sets up a MutationObserver to catch and count dynamic promotional elements.

// Default stylesheet targeting ads, quests, and promotional elements
const DEFAULT_CSS = `
  /* Block Discord Quests & Quest Banners in sidebar/panels */
  .quests-container,
  .quest-promo-banner,
  .quest-progress-bar,
  [data-list-item-id*="quest"],
  [aria-label*="quest"],
  div[class*="questsButton_"],
  div[class*="questsContainer_"],
  div[aria-label="Quests"] {
    display: none !important;
  }

  /* Block Nitro Promotions & Send Gift buttons in the bottom-left profile area */
  button[aria-label="Send a gift"],
  a[data-list-item-id$="___nitro"],
  a[data-list-item-id*="shop"] {
    display: none !important;
  }

  /* Block promotional banners and upsells within bottom-left panels */
  div[class*="promotions_"],
  div[class*="promo_"],
  [class*="premiumSubscribeButton_"] {
    display: none !important;
  }

  /* Block interactive callouts & overlay upsells */
  div[class*="overlayBackground_"]:has(div[class*="premiumSubscribeButton_"]),
  div[class*="overlayBackground_"]:has(div[class*="contentText_"] > a[role="button"]) {
    display: none !important;
  }
`;

// Helper to inject the CSS stylesheet immediately
function injectStyles(css) {
  const style = document.createElement('style');
  style.id = 'discord-adblocker-static-style';
  style.textContent = css;
  // Append to documentElement because document.head might not be ready at document_start
  (document.head || document.documentElement).appendChild(style);
}

// Inject default rules instantly
injectStyles(DEFAULT_CSS);

// Configuration state loaded from storage
let config = {
  enabled: true,
  blockQuests: true,
  blockNitro: true,
  blockPopups: true
};

// Retrieve configuration and apply refinements if needed
if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
  chrome.storage.local.get(['enabled', 'blockQuests', 'blockNitro', 'blockPopups'], (res) => {
    // Update config with stored values
    if (res.enabled !== undefined) config.enabled = res.enabled;
    if (res.blockQuests !== undefined) config.blockQuests = res.blockQuests;
    if (res.blockNitro !== undefined) config.blockNitro = res.blockNitro;
    if (res.blockPopups !== undefined) config.blockPopups = res.blockPopups;

    applyConfig();
  });
}

function applyConfig() {
  const styleEl = document.getElementById('discord-adblocker-static-style');
  if (!styleEl) return;

  if (!config.enabled) {
    styleEl.textContent = '';
    return;
  }

  let css = '';
  if (config.blockQuests) {
    css += `
      .quests-container,
      .quest-promo-banner,
      .quest-progress-bar,
      [data-list-item-id*="quest"],
      [aria-label*="quest"],
      div[class*="questsButton_"],
      div[class*="questsContainer_"],
      div[aria-label="Quests"] {
        display: none !important;
      }
    `;
  }
  if (config.blockNitro) {
    css += `
      button[aria-label="Send a gift"],
      a[data-list-item-id$="___nitro"],
      a[data-list-item-id*="shop"],
      [class*="premiumSubscribeButton_"],
      div[class*="overlayBackground_"]:has(div[class*="premiumSubscribeButton_"]),
      div[class*="overlayBackground_"]:has(div[class*="contentText_"] > a[role="button"]) {
        display: none !important;
      }
    `;
  }
  // Standard promo and banner classes always blocked when enabled
  css += `
    div[class*="promotions_"],
    div[class*="promo_"] {
      display: none !important;
    }
  `;

  styleEl.textContent = css;
}

// Function to safely increment the blocked count in chrome storage
function incrementBlockedCount() {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get('blockedCount', (res) => {
      const current = res.blockedCount || 0;
      chrome.storage.local.set({ blockedCount: current + 1 });
    });
  } else {
    // Fallback for Tampermonkey or environment without chrome storage
    let current = parseInt(localStorage.getItem('discord_adblocker_count') || '0', 10);
    localStorage.setItem('discord_adblocker_count', (current + 1).toString());
  }
}

// Heuristic Ad Detector and MutationObserver
function setupObserver() {
  // Selectors to target for counting
  const adSelectors = [
    '.quests-container',
    '.quest-promo-banner',
    'div[class*="questsContainer_"]',
    'div[class*="questsButton_"]',
    'div[aria-label="Quests"]',
    'div[class*="promotions_"]',
    'div[class*="promo_"]',
    'button[aria-label="Send a gift"]',
    'a[data-list-item-id$="___nitro"]',
    'a[data-list-item-id*="shop"]'
  ];

  // Helper to check if an element is an ad and mark it
  function checkAndMarkAd(el) {
    if (!config.enabled) return;
    if (el.dataset && el.dataset.discordAdblockerBlocked === 'true') return;

    // Check matches for explicit selectors
    let matchesAd = false;
    for (const sel of adSelectors) {
      if (el.matches && el.matches(sel)) {
        matchesAd = true;
        break;
      }
    }

    // Heuristic 1: Inspect bottom-left "panels" children
    // Any child of [class*="panels_"] that is not Profile, RTC, or Activity Panel is an ad
    if (!matchesAd && el.parentElement && el.parentElement.matches && el.parentElement.matches('div[class*="panels_"]')) {
      const isProfile = el.matches('div[class*="container_"]') || el.querySelector('button[aria-label="User Settings"]');
      const isRTC = el.matches('div[class*="rtcConnection_"]') || el.matches('div[class*="connection_"]');
      const isActivity = el.matches('div[class*="activityPanel_"]');

      if (!isProfile && !isRTC && !isActivity && el.tagName === 'DIV') {
        matchesAd = true;
      }
    }

    // Heuristic 2: Coordinate-based and keyword-based popup/tooltip/callout detection
    if (!matchesAd && config.blockPopups && el.matches && (el.matches('[class*="layer_"]') || el.matches('[class*="tooltip_"]') || el.matches('[class*="popout_"]'))) {
      const text = (el.textContent || '').toLowerCase();
      const hasPromoKeyword = text.includes('quest') || text.includes('nitro') || text.includes('shop') || text.includes('gift') || text.includes('promotion') || text.includes('subscribe');

      if (hasPromoKeyword) {
        // Check if the popup is positioned near the bottom-left panel
        const rect = el.getBoundingClientRect();
        const isBottomLeft = rect.left < 360 && rect.top > (window.innerHeight - 350);
        if (isBottomLeft) {
          matchesAd = true;
        }
      }
    }

    if (matchesAd) {
      // Mark as blocked, apply CSS to guarantee it is hidden, and increment counter
      if (el.style) {
        el.style.setProperty('display', 'none', 'important');
      }
      if (el.setAttribute) {
        el.setAttribute('data-discord-adblocker-blocked', 'true');
      }
      incrementBlockedCount();
    }
  }

  // Scan existing DOM on load
  document.querySelectorAll(adSelectors.join(',')).forEach(checkAndMarkAd);

  // Monitor panels container specifically if available, otherwise fallback to entire document
  const observer = new MutationObserver((mutations) => {
    if (!config.enabled) return;
    for (const mutation of mutations) {
      if (mutation.addedNodes) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check the node itself
            checkAndMarkAd(node);
            // Check children of the node
            adSelectors.forEach(sel => {
              node.querySelectorAll(sel).forEach(checkAndMarkAd);
            });
            // Check direct children of panels if the node is or contains panels container
            const panels = node.matches && node.matches('div[class*="panels_"]') ? node : node.querySelector && node.querySelector('div[class*="panels_"]');
            if (panels) {
              Array.from(panels.children).forEach(checkAndMarkAd);
            }
          }
        }
      }
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true
  });
}

// Initialize observer once DOM is loaded or loading
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupObserver);
} else {
  setupObserver();
}

// Message receiver to apply runtime updates from popup settings
if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'updateConfig') {
      config = { ...config, ...request.config };
      applyConfig();
      sendResponse({ status: 'success' });
    }
  });
}
