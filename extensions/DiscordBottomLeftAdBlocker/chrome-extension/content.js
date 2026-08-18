// Discord Bottom-Left Ad Blocker Content Script
// Injects styles instantly at document_start to prevent flicker and uses MutationObserver
// to dynamically catch and hide promotional elements and popups without hiding main application layout.

// Default stylesheet targeting ads, quests, and promotional elements
const DEFAULT_CSS = `
  /* Block Outer Quest Cards & Banners strictly inside bottom-left panels_ area */
  div[class*="panels_"] > *:has([class*="quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
  div[class*="panels_"] > *:has([aria-label*="Quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
  div[class*="panels_"] > *:has(a[href*="/quests"]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
  div[class*="panels_"] > *:has([class*="reward" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
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
  [class*="questContainer"],
  [class*="questWrapper"],
  [class*="questBox"],
  [class*="questContent"],
  [class*="questHome"],
  [class*="questBarWrapper"],
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
      div[class*="panels_"] > *:has([class*="quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
      div[class*="panels_"] > *:has([aria-label*="Quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
      div[class*="panels_"] > *:has(a[href*="/quests"]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
      div[class*="panels_"] > *:has([class*="reward" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"])),
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
      [class*="questContainer"],
      [class*="questWrapper"],
      [class*="questBox"],
      [class*="questContent"],
      [class*="questHome"],
      [class*="questBarWrapper"],
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

// Find highest safe quest parent container to collapse entire quest card box
function findHighestSafeQuestContainer(startEl) {
  let curr = startEl;
  let highestSafe = null;

  while (curr && curr !== document.body && curr !== document.documentElement) {
    if (curr.matches && (curr.matches('[class*="sidebar_"]') || curr.matches('[class*="panels_"]') || curr.matches('#app-mount') || curr.tagName === 'BODY' || curr.tagName === 'HTML')) {
      break;
    }

    const hasUserProfile = curr.querySelector('button[aria-label="User Settings"]') || curr.querySelector('[class*="avatar_"]');
    const hasVoicePanel = curr.querySelector('[class*="rtcConnection_"]') || curr.querySelector('[class*="connection_"]');
    if (hasUserProfile || hasVoicePanel) {
      break;
    }

    highestSafe = curr;
    curr = curr.parentElement;
  }

  return highestSafe;
}

// Inspect bottom-left panel cards specifically to ensure whole quest card container is collapsed
function checkAndHideQuestPanels() {
  if (!config.enabled || !config.blockQuests) return;

  const panelsContainer = document.querySelector('div[class*="panels_"]');
  if (!panelsContainer) return;

  for (const card of panelsContainer.children) {
    if (card.closest && card.closest('[data-discord-adblocker-blocked="true"]')) continue;

    // Never hide the user profile panel or RTC voice panel
    const isUserProfile = card.querySelector('button[aria-label="User Settings"]') || card.querySelector('[class*="avatar_"]');
    const isVoicePanel = card.querySelector('[class*="rtcConnection_"]') || card.querySelector('[class*="connection_"]');
    if (isUserProfile || isVoicePanel) continue;

    const cardText = (card.textContent || '').toLowerCase();
    const isQuestCard = cardText.includes('quest') ||
                        cardText.includes('orbs') ||
                        cardText.includes('get reward') ||
                        cardText.includes('claim reward') ||
                        cardText.includes('points to win') ||
                        card.querySelector('[class*="quest" i]') ||
                        card.querySelector('a[href*="/quests"]') ||
                        card.querySelector('[aria-label*="quest" i]');

    if (isQuestCard) {
      const highestContainer = findHighestSafeQuestContainer(card) || card;
      highestContainer.style.setProperty('display', 'none', 'important');
      highestContainer.setAttribute('data-discord-adblocker-blocked', 'true');
      card.setAttribute('data-discord-adblocker-blocked', 'true');
      incrementBlockedCount();
    }
  }
}

// Targeted Ad Detector and MutationObserver
function setupObserver() {
  const questSelectors = [
    'div[class*="panels_"] > *:has([class*="quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"]))',
    'div[class*="panels_"] > *:has([aria-label*="Quest" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"]))',
    'div[class*="panels_"] > *:has(a[href*="/quests"]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"]))',
    'div[class*="panels_"] > *:has([class*="reward" i]):not(:has(button[aria-label="User Settings"])):not(:has([class*="avatar_"]))',
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
    '[class*="questContainer"]',
    '[class*="questWrapper"]',
    '[class*="questBox"]',
    '[class*="questContent"]',
    '[class*="questHome"]',
    '[class*="questBarWrapper"]',
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
    if (el.closest && el.closest('[data-discord-adblocker-blocked="true"]')) return;

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
    if (!matchesAd && config.blockPopups && el.matches && (el.matches('[class*="tooltip_"]') || el.matches('[class*="popout_"]'))) {
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

      const highestSafe = findHighestSafeQuestContainer(el);
      if (highestSafe) {
        highestSafe.style.setProperty('display', 'none', 'important');
        highestSafe.setAttribute('data-discord-adblocker-blocked', 'true');
      }

      incrementBlockedCount();
    }
  }

  // Scan existing DOM on load
  const scanElements = () => {
    checkAndHideQuestPanels();
    const selectors = getActiveSelectors();
    if (selectors.length > 0) {
      document.querySelectorAll(selectors.join(',')).forEach(checkAndMarkAd);
    }
  };
  scanElements();

  // Monitor DOM changes for dynamic promotional elements
  const observer = new MutationObserver((mutations) => {
    if (!config.enabled) return;
    checkAndHideQuestPanels();
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
