// Discord Bottom-Left Ad Blocker Content Script
// This script runs at document_start to inject styles instantly (preventing flicker)
// and sets up a MutationObserver to catch and count dynamic promotional elements.

// Refined CSS selectors to avoid collision with "request" (Friend/Message Requests) and "question" (Help/FAQ Menu)
const QUEST_SELECTOR = `[class*="quest" i]:not([class*="request" i]):not([class*="question" i])`;

// Default stylesheet targeting ads, quests, and promotional elements
const DEFAULT_CSS = `
  /* Block Discord Quests & Quest Banners in specific sections only */
  [class*="sidebar_"] ${QUEST_SELECTOR},
  [class*="panels_"] ${QUEST_SELECTOR},
  [data-list-item-id*="quest" i]:not([data-list-item-id*="request" i]),
  [aria-label*="quest" i]:not([aria-label*="request" i]):not([aria-label*="question" i]),
  div[class*="questsContainer_"],
  div[class*="questsButton_"],
  div[aria-label="Quests"] {
    display: none !important;
  }

  /* Block Nitro Promotions & Send Gift buttons in specific user/chat areas */
  [class*="sidebar_"] [class*="upsell" i],
  [class*="panels_"] [class*="upsell" i],
  [class*="sidebar_"] [class*="premiumSubscribe" i],
  [class*="panels_"] [class*="premiumSubscribe" i],
  button[aria-label*="gift" i],
  a[data-list-item-id$="___nitro" i],
  a[data-list-item-id*="shop" i] {
    display: none !important;
  }

  /* Block promotional banners and cards within panels */
  [class*="panels_"] div[class*="promotions" i],
  [class*="panels_"] div[class*="promo" i] {
    display: none !important;
  }

  /* Hide any tooltip, popout, or callout wrapper that contains a quest, promo, or upsell element */
  [class*="tooltip_"]:has(${QUEST_SELECTOR}),
  [class*="tooltip_"]:has([class*="promo" i]),
  [class*="tooltip_"]:has([class*="upsell" i]),
  [class*="popout_"]:has(${QUEST_SELECTOR}),
  [class*="popout_"]:has([class*="promo" i]),
  [class*="popout_"]:has([class*="upsell" i]),
  div[class*="overlayBackground_"]:has([class*="premiumSubscribe" i]),
  div[class*="overlayBackground_"]:has(div[class*="contentText_"] > a[role="button"]) {
    display: none !important;
  }
`;

// Helper to inject the CSS stylesheet immediately
function injectStyles(css) {
  let style = document.getElementById('discord-adblocker-static-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'discord-adblocker-static-style';
    (document.head || document.documentElement).appendChild(style);
  }
  style.textContent = css;
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
  if (!config.enabled) {
    injectStyles('');
    return;
  }

  let css = '';

  if (config.blockQuests) {
    css += `
      [class*="sidebar_"] ${QUEST_SELECTOR},
      [class*="panels_"] ${QUEST_SELECTOR},
      [data-list-item-id*="quest" i]:not([data-list-item-id*="request" i]),
      [aria-label*="quest" i]:not([aria-label*="request" i]):not([aria-label*="question" i]),
      div[class*="questsContainer_"],
      div[class*="questsButton_"],
      div[aria-label="Quests"] {
        display: none !important;
      }
      [class*="tooltip_"]:has(${QUEST_SELECTOR}),
      [class*="popout_"]:has(${QUEST_SELECTOR}) {
        display: none !important;
      }
    `;
  }

  if (config.blockNitro) {
    css += `
      [class*="sidebar_"] [class*="upsell" i],
      [class*="panels_"] [class*="upsell" i],
      [class*="sidebar_"] [class*="premiumSubscribe" i],
      [class*="panels_"] [class*="premiumSubscribe" i],
      button[aria-label*="gift" i],
      a[data-list-item-id$="___nitro" i],
      a[data-list-item-id*="shop" i],
      [class*="tooltip_"]:has([class*="upsell" i]),
      [class*="popout_"]:has([class*="upsell" i]),
      div[class*="overlayBackground_"]:has([class*="premiumSubscribe" i]),
      div[class*="overlayBackground_"]:has(div[class*="contentText_"] > a[role="button"]) {
        display: none !important;
      }
    `;
  }

  // Standard promo and banner classes always blocked when enabled
  css += `
    [class*="panels_"] div[class*="promotions" i],
    [class*="panels_"] div[class*="promo" i] {
      display: none !important;
    }
    [class*="tooltip_"]:has([class*="promo" i]),
    [class*="popout_"]:has([class*="promo" i]) {
      display: none !important;
    }
  `;

  injectStyles(css);
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
  // Helpers to test if elements or descendants contain quest/promo indicators (excluding request & question)
  function containsQuest(el) {
    if (!el) return false;

    function isQuestClass(className) {
      if (!className || typeof className !== 'string') return false;
      const lower = className.toLowerCase();
      return lower.includes('quest') && !lower.includes('request') && !lower.includes('question');
    }

    if (el.classList) {
      for (const cls of el.classList) {
        if (isQuestClass(cls)) return true;
      }
    }

    if (el.matches && el.matches(QUEST_SELECTOR)) return true;
    return !!(el.querySelector && el.querySelector(QUEST_SELECTOR));
  }

  function containsPromo(el) {
    if (!el) return false;
    if (el.matches && (el.matches('[class*="promo" i]') || el.matches('[class*="promotions" i]'))) return true;
    return !!(el.querySelector && (el.querySelector('[class*="promo" i]') || el.querySelector('[class*="promotions" i]')));
  }

  function containsUpsell(el) {
    if (!el) return false;
    if (el.matches && (el.matches('[class*="upsell" i]') || el.matches('[class*="premium" i]'))) return true;
    return !!(el.querySelector && (el.querySelector('[class*="upsell" i]') || el.querySelector('[class*="premium" i]')));
  }

  // Check if an element is an ad and mark it
  function checkAndMarkAd(el) {
    if (!config.enabled) return;
    if (el.dataset && el.dataset.discordAdblockerBlocked === 'true') return;

    let matchesAd = false;

    // 1. Explicit Selector Match
    if (config.blockQuests && containsQuest(el)) {
      matchesAd = true;
    }
    if (config.blockNitro && containsUpsell(el)) {
      matchesAd = true;
    }
    if (containsPromo(el)) {
      matchesAd = true;
    }

    // 2. Absolute layers / popups near bottom-left
    if (!matchesAd && config.blockPopups && el.matches && (el.matches('[class*="tooltip_"]') || el.matches('[class*="popout_"]'))) {
      const text = (el.textContent || '').toLowerCase();
      const hasCollidingKeyword = text.includes('request') || text.includes('question');

      if (!hasCollidingKeyword) {
        const hasPromoKeyword = text.includes('quest') || text.includes('nitro') || text.includes('shop') || text.includes('gift') || text.includes('promotion') || text.includes('subscribe');

        if (hasPromoKeyword || containsQuest(el) || containsPromo(el) || containsUpsell(el)) {
          // Layout timing fix: Use requestAnimationFrame to let browser compute dimensions before checking coordinates
          requestAnimationFrame(() => {
            if (el.dataset && el.dataset.discordAdblockerBlocked === 'true') return;

            const rect = el.getBoundingClientRect();
            const isNearBottomLeft = rect.left < 360 && rect.top > (window.innerHeight - 350);
            const isUnrenderedButExplicit = rect.width === 0 && (containsQuest(el) || containsPromo(el) || containsUpsell(el));

            if (isNearBottomLeft || isUnrenderedButExplicit) {
              if (el.style) {
                el.style.setProperty('display', 'none', 'important');
              }
              if (el.setAttribute) {
                el.setAttribute('data-discord-adblocker-blocked', 'true');
              }

              // Over-counting fix: Only increment stats count if this is the top-most blocked element in this subtree
              const isAncestorAlreadyBlocked = el.parentElement && el.parentElement.closest('[data-discord-adblocker-blocked="true"]');
              if (!isAncestorAlreadyBlocked) {
                incrementBlockedCount();
              }
            }
          });
          return; // Skip synchronous handling since it's deferred to RAF
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

      // Over-counting fix: Only increment stats count if this is the top-most blocked element in this subtree
      const isAncestorAlreadyBlocked = el.parentElement && el.parentElement.closest('[data-discord-adblocker-blocked="true"]');
      if (!isAncestorAlreadyBlocked) {
        incrementBlockedCount();
      }
    }
  }

  // Scan existing DOM on load
  document.querySelectorAll(`${QUEST_SELECTOR}, [class*="promo" i], [class*="upsell" i]`).forEach(checkAndMarkAd);

  // Monitor panels container and full page insertions
  const observer = new MutationObserver((mutations) => {
    if (!config.enabled) return;
    for (const mutation of mutations) {
      if (mutation.addedNodes) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            checkAndMarkAd(node);

            // Check matching children
            node.querySelectorAll(`${QUEST_SELECTOR}, [class*="promo" i], [class*="upsell" i]`).forEach(checkAndMarkAd);

            // Inspect panels direct children specifically
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
