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

  // Refined CSS selectors to avoid collision with "request" (Friend/Message Requests) and "question" (Help/FAQ)
  const QUEST_SELECTOR = `[class*="quest" i]:not([class*="request" i]):not([class*="question" i])`;

  // Default CSS Rules targeting all kinds of promotional elements (using modern, case-insensitive, and :has() selectors)
  const DEFAULT_CSS = `
    /* Block Discord Quests & Quest Banners globally (case-insensitive, excluding request/question) */
    ${QUEST_SELECTOR} {
      display: none !important;
    }

    /* Block Nitro Promotions & Send Gift buttons in chat/panels */
    button[aria-label*="gift" i],
    a[data-list-item-id$="___nitro" i],
    a[data-list-item-id*="shop" i],
    [class*="upsell" i],
    [class*="premiumSubscribeButton" i] {
      display: none !important;
    }

    /* Block promotional banners and cards within panels */
    div[class*="promotions" i],
    div[class*="promo" i] {
      display: none !important;
    }

    /* Hide any tooltip, layer, or popout wrapper that contains a quest, promo, or upsell element */
    [class*="layer_"]:has(${QUEST_SELECTOR}),
    [class*="layer_"]:has([class*="promo" i]),
    [class*="layer_"]:has([class*="upsell" i]),
    [class*="tooltip_"]:has(${QUEST_SELECTOR}),
    [class*="tooltip_"]:has([class*="promo" i]),
    [class*="tooltip_"]:has([class*="upsell" i]),
    [class*="popout_"]:has(${QUEST_SELECTOR}),
    [class*="popout_"]:has([class*="promo" i]),
    [class*="popout_"]:has([class*="upsell" i]),
    div[class*="overlayBackground_"]:has(div[class*="premiumSubscribeButton" i]),
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
      // Also fetch stats counter
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
      // Deactivate quest rules
      css += `
        ${QUEST_SELECTOR} {
          display: block !important;
        }
        [class*="layer_"]:has(${QUEST_SELECTOR}),
        [class*="tooltip_"]:has(${QUEST_SELECTOR}),
        [class*="popout_"]:has(${QUEST_SELECTOR}) {
          display: block !important;
        }
      `;
    }
    if (!config.blockNitro) {
      // Deactivate nitro rules
      css += `
        button[aria-label*="gift" i],
        a[data-list-item-id$="___nitro" i],
        a[data-list-item-id*="shop" i],
        [class*="upsell" i],
        [class*="premiumSubscribeButton" i] {
          display: flex !important;
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
    // Update active UI elements if open
    const statsVal = document.getElementById('adblocker-modal-stats-val');
    if (statsVal) {
      statsVal.textContent = config.blockedCount.toLocaleString();
    }
  }

  // Helper to determine if a panel inside div[class*="panels_"] is a legitimate UI element
  function isLegitimatePanel(el) {
    if (!el) return false;

    // 1. Check User Profile Panel: contains settings button + mute/deafen button
    const hasSettings = el.querySelector && el.querySelector('button[aria-label*="settings" i]');
    const hasMute = el.querySelector && el.querySelector('button[aria-label*="mute" i]');
    const hasDeafen = el.querySelector && el.querySelector('button[aria-label*="deafen" i]');
    if (hasSettings && (hasMute || hasDeafen)) {
      return true; // Legitimate Profile Panel
    }

    // 2. Check RTC/Voice Connection Panel: contains connection status text or a disconnect button
    const hasDisconnect = el.querySelector && el.querySelector('button[aria-label*="disconnect" i]');
    const hasConnectionStatus = el.textContent && (
      el.textContent.includes('Voice Connected') ||
      el.textContent.includes('RTC Connecting') ||
      el.textContent.includes('No Route')
    );
    if (hasDisconnect || hasConnectionStatus) {
      return true; // Legitimate RTC Panel
    }

    // 3. Check Game Activity/Streaming Panel: contains stream/screen share controls
    const hasActivityControls = el.querySelector && (
      el.querySelector('button[aria-label*="stream" i]') ||
      el.querySelector('button[aria-label*="screen" i]')
    );
    if (hasActivityControls) {
      return true; // Legitimate Activity Panel
    }

    return false;
  }

  // Heuristic Ad Detection and MutationObserver
  function setupObserver() {
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

    function checkAndMarkAd(el) {
      if (!config.enabled) return;
      if (el.dataset && el.dataset.discordAdblockerBlocked === 'true') return;

      let matchesAd = false;

      // 1. Selector match
      if (config.blockQuests && containsQuest(el)) {
        matchesAd = true;
      }
      if (config.blockNitro && containsUpsell(el)) {
        matchesAd = true;
      }
      if (containsPromo(el)) {
        matchesAd = true;
      }

      // 2. Bottom-left panels container heuristic
      const isInsidePanels = el.closest && el.closest('div[class*="panels_"]');
      if (!matchesAd && isInsidePanels) {
        let directChildInPanels = el;
        while (directChildInPanels.parentElement && !directChildInPanels.parentElement.matches('div[class*="panels_"]')) {
          directChildInPanels = directChildInPanels.parentElement;
        }

        if (directChildInPanels && directChildInPanels.tagName === 'DIV' && !isLegitimatePanel(directChildInPanels)) {
          matchesAd = true;
        }
      }

      // 3. Absolute layers / popups near bottom-left
      if (!matchesAd && config.blockPopups && el.matches && (el.matches('[class*="layer_"]') || el.matches('[class*="tooltip_"]') || el.matches('[class*="popout_"]'))) {
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
                incrementBlockedCount();
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
        incrementBlockedCount();
      }
    }

    // Initial Scan
    document.querySelectorAll(`${QUEST_SELECTOR}, [class*="promo" i], [class*="upsell" i]`).forEach(checkAndMarkAd);

    // Set up MutationObserver to watch for additions
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.addedNodes) {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              checkAndMarkAd(node);
              node.querySelectorAll(`${QUEST_SELECTOR}, [class*="promo" i], [class*="upsell" i]`).forEach(checkAndMarkAd);

              // Check direct children of panels container
              const panels = node.matches && node.matches('div[class*="panels_"]') ? node : node.querySelector && node.querySelector('div[class*="panels_"]');
              if (panels) {
                Array.from(panels.children).forEach(checkAndMarkAd);
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

    // Create our elegant shield/adblocker button
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

    // Click handler to open settings modal
    widgetBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openSettingsModal();
    });

    // Insert next to the User Settings gear button
    btnGroup.insertBefore(widgetBtn, settingsBtn);
  }

  // Beautiful Modal Overlay for Userscript
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

    // Event handlers
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

  // Initialize observer and try button injection
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
