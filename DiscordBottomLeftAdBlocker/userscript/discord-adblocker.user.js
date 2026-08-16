// ==UserScript==
// @name         Discord Bottom-Left Ad Blocker
// @namespace    https://github.com/jules/discord-adblocker
// @version      1.0.0
// @description  Blocks intrusive advertisements, Quests, Nitro upsells, and promo popups in the bottom-left corner of Discord. Includes a beautiful integrated in-app settings widget next to your profile panel!
// @author       Jules
// @match        https://discord.com/*
// @match        https://*.discord.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
  'use strict';

  // Default CSS Rules targeting all kinds of promotional elements
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

    /* Custom style for the injected adblocker button */
    .adblocker-widget-btn {
      background: none;
      border: none;
      padding: 0;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 4px;
      cursor: pointer;
      color: #949ba4;
      position: relative;
      transition: color 0.15s, background-color 0.15s;
    }
    .adblocker-widget-btn:hover {
      background-color: rgba(78, 80, 88, 0.3);
      color: #f2f3f5;
    }
    .adblocker-widget-btn svg {
      width: 20px;
      height: 20px;
    }

    /* Adblocker Modal Overlay */
    .adblocker-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background-color: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 99999;
      font-family: sans-serif;
    }
    .adblocker-modal {
      background-color: #313338;
      color: #f2f3f5;
      width: 360px;
      border-radius: 8px;
      border: 1px solid #3f4147;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }
    .adblocker-modal-header {
      background-color: #1e1f22;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #3f4147;
    }
    .adblocker-modal-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .adblocker-modal-close {
      background: none;
      border: none;
      color: #949ba4;
      font-size: 20px;
      cursor: pointer;
    }
    .adblocker-modal-close:hover {
      color: #f2f3f5;
    }
    .adblocker-modal-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .adblocker-modal-stats {
      background-color: #2b2d31;
      padding: 16px;
      border-radius: 8px;
      text-align: center;
      border: 1px solid #3f4147;
    }
    .adblocker-modal-stats-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      color: #949ba4;
      letter-spacing: 0.5px;
    }
    .adblocker-modal-stats-val {
      font-size: 32px;
      font-weight: 800;
      color: #5865f2;
      margin: 8px 0;
    }
    .adblocker-modal-btn {
      background-color: #da373c;
      color: white;
      border: none;
      border-radius: 4px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s;
    }
    .adblocker-modal-btn:hover {
      background-color: #a92b2f;
    }
    .adblocker-modal-setting {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background-color: #2b2d31;
      padding: 12px;
      border-radius: 6px;
      border: 1px solid #3f4147;
    }
    .adblocker-modal-setting-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .adblocker-modal-setting-title {
      font-size: 13px;
      font-weight: 600;
    }
    .adblocker-modal-setting-desc {
      font-size: 11px;
      color: #949ba4;
    }
    /* Simple Toggle Switch inside userscript */
    .adblocker-modal-switch {
      position: relative;
      display: inline-block;
      width: 36px;
      height: 20px;
    }
    .adblocker-modal-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .adblocker-modal-slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #80848e;
      transition: .15s;
      border-radius: 20px;
    }
    .adblocker-modal-slider:before {
      position: absolute;
      content: "";
      height: 14px;
      width: 14px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .15s;
      border-radius: 50%;
    }
    .adblocker-modal-switch input:checked + .adblocker-modal-slider {
      background-color: #23a55a;
    }
    .adblocker-modal-switch input:checked + .adblocker-modal-slider:before {
      transform: translateX(16px);
    }
  `;

  // Inject CSS rules instantly at document-start
  const styleEl = document.createElement('style');
  styleEl.id = 'discord-adblocker-userscript-style';
  styleEl.textContent = DEFAULT_CSS;
  (document.head || document.documentElement).appendChild(styleEl);

  // Configuration management using localStorage
  let config = {
    enabled: true,
    blockQuests: true,
    blockNitro: true,
    blockPopups: true,
    blockedCount: 0
  };

  function loadConfig() {
    try {
      const saved = localStorage.getItem('discord_adblocker_config');
      if (saved) {
        const parsed = JSON.parse(saved);
        config = { ...config, ...parsed };
      }
      const savedCount = localStorage.getItem('discord_adblocker_count');
      if (savedCount) {
        config.blockedCount = parseInt(savedCount, 10) || 0;
      }
    } catch (e) {
      console.error('[AdBlocker] Failed to load config', e);
    }
  }

  function saveConfig() {
    try {
      localStorage.setItem('discord_adblocker_config', JSON.stringify({
        enabled: config.enabled,
        blockQuests: config.blockQuests,
        blockNitro: config.blockNitro,
        blockPopups: config.blockPopups
      }));
      localStorage.setItem('discord_adblocker_count', config.blockedCount.toString());
    } catch (e) {
      console.error('[AdBlocker] Failed to save config', e);
    }
  }

  function applyConfig() {
    if (!config.enabled) {
      styleEl.textContent = '.adblocker-widget-btn { display: flex; }'; // Keep button styling only
      return;
    }

    let css = DEFAULT_CSS;
    if (!config.blockQuests) {
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
          display: inherit !important;
        }
      `;
    }
    if (!config.blockNitro) {
      css += `
        button[aria-label="Send a gift"],
        a[data-list-item-id$="___nitro"],
        a[data-list-item-id*="shop"] {
          display: inherit !important;
        }
      `;
    }

    styleEl.textContent = css;
  }

  loadConfig();
  applyConfig();

  function incrementBlockedCount() {
    config.blockedCount++;
    saveConfig();
    const statsVal = document.getElementById('adblocker-modal-stats-val');
    if (statsVal) {
      statsVal.textContent = config.blockedCount.toLocaleString();
    }
  }

  // Targeted Ad Detection and MutationObserver
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

      // Coordinate-based popups
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

    // Initial Scan
    const scanElements = () => {
      const activeSelectors = getActiveSelectors();
      if (activeSelectors.length > 0) {
        document.querySelectorAll(activeSelectors.join(',')).forEach(checkAndMarkAd);
      }
    };
    scanElements();

    // Set up MutationObserver to watch for additions
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

              // Try injecting our shield button next to the User Settings gear
              tryInjectWidgetButton(node);
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

  // Inject Settings widget button inside Discord user panels
  function tryInjectWidgetButton(rootNode) {
    if (document.getElementById('discord-adblocker-btn')) return;

    const settingsBtn = (rootNode && rootNode.querySelector) ? rootNode.querySelector('button[aria-label="User Settings"]') : document.querySelector('button[aria-label="User Settings"]');
    if (!settingsBtn) return;

    const btnGroup = settingsBtn.parentElement;
    if (!btnGroup) return;

    const widgetBtn = document.createElement('button');
    widgetBtn.id = 'discord-adblocker-btn';
    widgetBtn.className = 'adblocker-widget-btn';
    widgetBtn.setAttribute('aria-label', 'Ad Blocker Settings');
    widgetBtn.title = 'Discord Ad Blocker Settings';
    widgetBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C11.5 2 6 4 6 4V11C6 16.1 9.5 19.8 12 21C14.5 19.8 18 16.1 18 11V4C18 4 12.5 2 12 2ZM12 19.1C10.2 18.1 7.8 15.1 7.8 11V5.4L12 3.8L16.2 5.4V11C16.2 15.1 13.8 18.1 12 19.1ZM11 7H13V13H11V7ZM11 15H13V17H11V15Z"/>
      </svg>
    `;

    widgetBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openSettingsModal();
    });

    btnGroup.insertBefore(widgetBtn, settingsBtn);
  }

  // Modal Overlay for Userscript
  function openSettingsModal() {
    if (document.getElementById('adblocker-modal-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'adblocker-modal-overlay';
    overlay.className = 'adblocker-modal-overlay';

    overlay.innerHTML = `
      <div class="adblocker-modal">
        <div class="adblocker-modal-header">
          <h3>
            <svg viewBox="0 0 24 24" fill="currentColor" style="width: 22px; height: 22px; color: #5865f2;">
              <path d="M12 2C11.5 2 6 4 6 4V11C6 16.1 9.5 19.8 12 21C14.5 19.8 18 16.1 18 11V4C18 4 12.5 2 12 2ZM12 19.1C10.2 18.1 7.8 15.1 7.8 11V5.4L12 3.8L16.2 5.4V11C16.2 15.1 13.8 18.1 12 19.1Z"/>
            </svg>
            Ad Blocker Settings
          </h3>
          <button class="adblocker-modal-close" id="adblocker-modal-close-btn">&times;</button>
        </div>
        <div class="adblocker-modal-body">
          <div class="adblocker-modal-stats">
            <div class="adblocker-modal-stats-label">Blocked Advertisements</div>
            <div id="adblocker-modal-stats-val" class="adblocker-modal-stats-val">${config.blockedCount.toLocaleString()}</div>
            <button class="adblocker-modal-btn" id="adblocker-modal-reset">Reset Counter</button>
          </div>

          <div class="adblocker-modal-setting">
            <div class="adblocker-modal-setting-info">
              <span class="adblocker-modal-setting-title">Enable Ad Blocker</span>
              <span class="adblocker-modal-setting-desc">Toggles bottom-left advertisement blocking.</span>
            </div>
            <label class="adblocker-modal-switch">
              <input type="checkbox" id="adblocker-toggle-enable" ${config.enabled ? 'checked' : ''}>
              <span class="adblocker-modal-slider"></span>
            </label>
          </div>

          <div class="adblocker-modal-setting" id="setting-quests-container">
            <div class="adblocker-modal-setting-info">
              <span class="adblocker-modal-setting-title">Block Discord Quests</span>
              <span class="adblocker-modal-setting-desc">Hides sponsored game quest promotions.</span>
            </div>
            <label class="adblocker-modal-switch">
              <input type="checkbox" id="adblocker-toggle-quests" ${config.blockQuests ? 'checked' : ''} ${config.enabled ? '' : 'disabled'}>
              <span class="adblocker-modal-slider"></span>
            </label>
          </div>

          <div class="adblocker-modal-setting" id="setting-nitro-container">
            <div class="adblocker-modal-setting-info">
              <span class="adblocker-modal-setting-title">Block Nitro Promos</span>
              <span class="adblocker-modal-setting-desc">Hides Nitro gifts & store options.</span>
            </div>
            <label class="adblocker-modal-switch">
              <input type="checkbox" id="adblocker-toggle-nitro" ${config.blockNitro ? 'checked' : ''} ${config.enabled ? '' : 'disabled'}>
              <span class="adblocker-modal-slider"></span>
            </label>
          </div>

          <div class="adblocker-modal-setting" id="setting-popups-container">
            <div class="adblocker-modal-setting-info">
              <span class="adblocker-modal-setting-title">Block Popup Callouts</span>
              <span class="adblocker-modal-setting-desc">Hides bottom-left tooltips & promotions.</span>
            </div>
            <label class="adblocker-modal-switch">
              <input type="checkbox" id="adblocker-toggle-popups" ${config.blockPopups ? 'checked' : ''} ${config.enabled ? '' : 'disabled'}>
              <span class="adblocker-modal-slider"></span>
            </label>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const closeBtn = document.getElementById('adblocker-modal-close-btn');
    const resetBtn = document.getElementById('adblocker-modal-reset');
    const toggleEnable = document.getElementById('adblocker-toggle-enable');
    const toggleQuests = document.getElementById('adblocker-toggle-quests');
    const toggleNitro = document.getElementById('adblocker-toggle-nitro');
    const togglePopups = document.getElementById('adblocker-toggle-popups');

    function updateElementsOpacity() {
      const dependents = ['setting-quests-container', 'setting-nitro-container', 'setting-popups-container'];
      dependents.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.style.opacity = config.enabled ? '1' : '0.5';
        }
      });
    }

    updateElementsOpacity();

    closeBtn.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });

    resetBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to reset the blocked advertisements counter?')) {
        config.blockedCount = 0;
        saveConfig();
        document.getElementById('adblocker-modal-stats-val').textContent = '0';
      }
    });

    toggleEnable.addEventListener('change', () => {
      config.enabled = toggleEnable.checked;
      toggleQuests.disabled = !config.enabled;
      toggleNitro.disabled = !config.enabled;
      togglePopups.disabled = !config.enabled;
      updateElementsOpacity();
      saveConfig();
      applyConfig();
    });

    toggleQuests.addEventListener('change', () => {
      config.blockQuests = toggleQuests.checked;
      saveConfig();
      applyConfig();
    });

    toggleNitro.addEventListener('change', () => {
      config.blockNitro = toggleNitro.checked;
      saveConfig();
      applyConfig();
    });

    togglePopups.addEventListener('change', () => {
      config.blockPopups = togglePopups.checked;
      saveConfig();
      applyConfig();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setupObserver();
      tryInjectWidgetButton();
    });
  } else {
    setupObserver();
    tryInjectWidgetButton();
  }
})();
