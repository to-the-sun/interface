// Discord Bottom-Left Ad Blocker Content Script
// Injects styles instantly at document_start to prevent flicker and uses MutationObserver
// to dynamically catch and hide promotional elements and popups.

// Default stylesheet targeting ads, quests, and promotional elements
const DEFAULT_CSS = `
  /* Block Outer Quest Cards & Panels in bottom-left area */
  div[class*="panels_"] > div:has([class*="quest" i]),
  div[class*="panels_"] > div:has([aria-label*="Quest" i]),
  div[class*="panels_"] > div:has(a[href*="/quests"]),
  div[class*="activityPanel_"]:has([class*="quest" i]),
  div[class*="activityPanel_"]:has([aria-label*="Quest" i]),
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
  [class*="questBanner"],
  [class*="questButton"],
  [class*="questsButton"],
  [class*="questBody"],
  [class*="questReward"],
  [class*="questPrompt"],
  [class*="questNotice"],
  [class*="questEmbed"],
  [class*="quest_"],
  [class*="quests_"],
  [class*="quest-"],
  [class*="quests-"],
  [data-list-item-id*="quest" i]:not([data-list-item-id*="request" i]):not([data-list-item-id*="question" i]),
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
      div[class*="panels_"] > div:has([class*="quest" i]),
      div[class*="panels_"] > div:has([aria-label*="Quest" i]),
      div[class*="panels_"] > div:has(a[href*="/quests"]),
      div[class*="activityPanel_"]:has([class*="quest" i]),
      div[class*="activityPanel_"]:has([aria-label*="Quest" i]),
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
      [class*="questBanner"],
      [class*="questButton"],
      [class*="questsButton"],
      [class*="questBody"],
      [class*="questReward"],
      [class*="questPrompt"],
      [class*="questNotice"],
      [class*="questEmbed"],
      [class*="quest_"],
      [class*="quests_"],
      [class*="quest-"],
      [class*="quests-"],
      [data-list-item-id*="quest" i]:not([data-list-item-id*="request" i]):not([data-list-item-id*="question" i]),
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
    let current = parseInt(localStorage.getItem('discord_adblocker_count') || '0', 10);
    localStorage.setItem('discord_adblocker_count', (current + 1).toString());
  }
}

// Targeted Ad Detector and MutationObserver
function setupObserver() {
  const questSelectors = [
    'div[class*="panels_"] > div:has([class*="quest" i])',
    'div[class*="panels_"] > div:has([aria-label*="Quest" i])',
    'div[class*="panels_"] > div:has(a[href*="/quests"])',
    'div[class*="activityPanel_"]:has([class*="quest" i])',
    'div[class*="activityPanel_"]:has([aria-label*="Quest" i])',
    '.quests-container',
    '.quest-promo-banner',
    '.quest-progress-bar',
    '[class*="questsContainer"]',
    '[class*="questsCard"]',
    '[class*="questsWrapper"]',
    '[class*="questTile"]',
    '[class*="questBar"]',
    '[class*="questCard"]',
    '[class*="questPanel"]',
    '[class*="questBanner"]',
    '[class*="questButton"]',
    '[class*="questsButton"]',
    '[class*="questBody"]',
    '[class*="questReward"]',
    '[class*="questPrompt"]',
    '[class*="questNotice"]',
    '[class*="questEmbed"]',
    '[class*="quest_"]',
    '[class*="quests_"]',
    '[class*="quest-"]',
    '[class*="quests-"]',
    '[data-list-item-id*="quest" i]:not([data-list-item-id*="request" i]):not([data-list-item-id*="question" i])',
    'div[aria-label="Quests"]'
  ];

  const nitroSelectors = [
    'button[aria-label="Send a gift"]',
    'a[data-list-item-id$="___nitro"]',
    'a[data-list-item-id*="shop"]',
    '[class*="premiumSubscribeButton_"]'
  ];

  const promoSelectors = [
    'div[class*="promotions_"]',
    'div[class*="promo_"]'
  ];

  function getActiveSelectors() {
    let selectors = [];
    if (config.blockQuests) selectors = selectors.concat(questSelectors);
    if (config.blockNitro) selectors = selectors.concat(nitroSelectors);
    selectors = selectors.concat(promoSelectors);
    return selectors;
  }

  // Helper to check if an element is an ad and mark it
  function checkAndMarkAd(el) {
    if (!config.enabled) return;
    if (el.dataset && el.dataset.discordAdblockerBlocked === 'true') return;

    let matchesAd = false;

    // Check quest selectors if enabled
    if (config.blockQuests) {
      for (const sel of questSelectors) {
        if (el.matches && el.matches(sel)) {
          matchesAd = true;
          break;
        }
      }
    }

    // Check nitro selectors if enabled
    if (!matchesAd && config.blockNitro) {
      for (const sel of nitroSelectors) {
        if (el.matches && el.matches(sel)) {
          matchesAd = true;
          break;
        }
      }
    }

    // Check general promo selectors
    if (!matchesAd) {
      for (const sel of promoSelectors) {
        if (el.matches && el.matches(sel)) {
          matchesAd = true;
          break;
        }
      }
    }

    // Coordinate-based and keyword-based popup/tooltip/callout detection
    if (!matchesAd && config.blockPopups && el.matches && (el.matches('[class*="layer_"]') || el.matches('[class*="tooltip_"]') || el.matches('[class*="popout_"]'))) {
      const text = (el.textContent || '').toLowerCase();
      const hasPromoKeyword = text.includes('quest') || text.includes('nitro') || text.includes('shop') || text.includes('gift') || text.includes('promotion') || text.includes('subscribe');

      if (hasPromoKeyword) {
        const rect = el.getBoundingClientRect();
        const isBottomLeft = rect.left < 360 && rect.top > (window.innerHeight - 350);
        if (isBottomLeft) {
          matchesAd = true;
        }
      }
    }

    if (matchesAd) {
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
  const scanElements = () => {
    const selectors = getActiveSelectors();
    if (selectors.length > 0) {
      document.querySelectorAll(selectors.join(',')).forEach(checkAndMarkAd);
    }
  };
  scanElements();

  // Monitor DOM changes for dynamic promotional elements
  const observer = new MutationObserver((mutations) => {
    if (!config.enabled) return;
    for (const mutation of mutations) {
      if (mutation.addedNodes) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            checkAndMarkAd(node);
            const activeSelectors = getActiveSelectors();
            if (activeSelectors.length > 0) {
              node.querySelectorAll(activeSelectors.join(',')).forEach(checkAndMarkAd);
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
