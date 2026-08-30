(function () {
  'use strict';

  const DEFAULT_SETTINGS = {
    enabled: true,
    scrollbarSize: '18px'
  };

  let currentSettings = { ...DEFAULT_SETTINGS };

  function applySettings(settings) {
    currentSettings = { ...DEFAULT_SETTINGS, ...settings };

    if (!currentSettings.enabled) {
      removeStyles();
      return;
    }

    const root = document.documentElement;
    if (root) {
      root.style.setProperty('--jules-scrollbar-size', currentSettings.scrollbarSize);
    }

    ensureStylesInDocument(document);
    applyStylesToShadowRoots(document);
  }

  function getCSSRuleString() {
    const size = currentSettings.scrollbarSize || '18px';
    return `
      :root {
        --jules-scrollbar-size: ${size} !important;
      }
      *, *::before, *::after {
        scrollbar-width: auto !important;
      }
      ::-webkit-scrollbar {
        width: ${size} !important;
        height: ${size} !important;
        display: block !important;
      }
      ::-webkit-scrollbar-button {
        display: block !important;
      }
      ::-webkit-scrollbar-button:vertical {
        height: ${size} !important;
        width: ${size} !important;
      }
      ::-webkit-scrollbar-button:horizontal {
        height: ${size} !important;
        width: ${size} !important;
      }
    `;
  }

  function ensureStylesInDocument(docOrShadow) {
    if (!docOrShadow || !currentSettings.enabled) return;
    const styleId = 'jules-scrollbar-dynamic-style';
    let styleEl = docOrShadow.querySelector(`#${styleId}`);
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = styleId;
      const targetNode = docOrShadow.head || docOrShadow.body || docOrShadow.documentElement || docOrShadow;
      if (targetNode && targetNode.appendChild) {
        targetNode.appendChild(styleEl);
      }
    }
    if (styleEl) {
      styleEl.textContent = getCSSRuleString();
    }
  }

  function applyStylesToShadowRoots(node) {
    if (!node || !currentSettings.enabled) return;
    const elements = node.querySelectorAll ? node.querySelectorAll('*') : [];
    elements.forEach((el) => {
      if (el.shadowRoot) {
        ensureStylesInDocument(el.shadowRoot);
        applyStylesToShadowRoots(el.shadowRoot);
      }
    });
  }

  function removeStyles() {
    const styleEls = document.querySelectorAll('#jules-scrollbar-dynamic-style');
    styleEls.forEach((el) => el.remove());
  }

  function loadAndApplySettings() {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
      chrome.storage.sync.get(DEFAULT_SETTINGS, (stored) => {
        applySettings(stored);
      });
    } else {
      applySettings(DEFAULT_SETTINGS);
    }
  }

  // Observe DOM additions for Shadow DOM roots or dynamic element mounts
  const observer = new MutationObserver(() => {
    if (currentSettings.enabled) {
      applyStylesToShadowRoots(document);
    }
  });

  if (document.documentElement) {
    observer.observe(document.documentElement, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      if (document.documentElement) {
        observer.observe(document.documentElement, { childList: true, subtree: true });
      }
    });
  }

  // Listen for setting changes
  if (typeof chrome !== 'undefined' && chrome.storage) {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'sync') {
        const updated = { ...currentSettings };
        if (changes.enabled) updated.enabled = changes.enabled.newValue;
        if (changes.scrollbarSize) updated.scrollbarSize = changes.scrollbarSize.newValue;
        applySettings(updated);
      }
    });
  }

  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === 'SETTINGS_UPDATED') {
        applySettings(message.settings);
        if (sendResponse) sendResponse({ status: 'ok' });
      }
    });
  }

  // Initialize
  loadAndApplySettings();
})();
