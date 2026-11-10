/**
 * SoundCloud Feed Default & Promoted Track Cleaner
 * Content Script
 */

(function () {
  'use strict';

  // Configuration options (synced with chrome.storage if available)
  const config = {
    defaultToFeed: true,
    removePromotedTracks: true,
    routeLogoToFeed: true,
    defaultRepostsOff: true,
    removeArtistTools: true,
    removeTopBanner: true,
    removeUpsellLinks: true
  };

  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get([
      'defaultToFeed',
      'removePromotedTracks',
      'routeLogoToFeed',
      'defaultRepostsOff',
      'removeArtistTools',
      'removeTopBanner',
      'removeUpsellLinks'
    ], (result) => {
      if (result.defaultToFeed !== undefined) config.defaultToFeed = result.defaultToFeed;
      if (result.removePromotedTracks !== undefined) config.removePromotedTracks = result.removePromotedTracks;
      if (result.routeLogoToFeed !== undefined) config.routeLogoToFeed = result.routeLogoToFeed;
      if (result.defaultRepostsOff !== undefined) config.defaultRepostsOff = result.defaultRepostsOff;
      if (result.removeArtistTools !== undefined) config.removeArtistTools = result.removeArtistTools;
      if (result.removeTopBanner !== undefined) config.removeTopBanner = result.removeTopBanner;
      if (result.removeUpsellLinks !== undefined) config.removeUpsellLinks = result.removeUpsellLinks;
    });

    chrome.storage.onChanged.addListener((changes) => {
      if (changes.defaultToFeed) config.defaultToFeed = changes.defaultToFeed.newValue;
      if (changes.removePromotedTracks) config.removePromotedTracks = changes.removePromotedTracks.newValue;
      if (changes.routeLogoToFeed) config.routeLogoToFeed = changes.routeLogoToFeed.newValue;
      if (changes.defaultRepostsOff) config.defaultRepostsOff = changes.defaultRepostsOff.newValue;
      if (changes.removeArtistTools) config.removeArtistTools = changes.removeArtistTools.newValue;
      if (changes.removeTopBanner) config.removeTopBanner = changes.removeTopBanner.newValue;
      if (changes.removeUpsellLinks) config.removeUpsellLinks = changes.removeUpsellLinks.newValue;
    });
  }

  // --- 1. DEFAULT TO FEED REDIRECTION ---

  function shouldRedirectToFeed(pathname) {
    if (!config.defaultToFeed) return false;
    const cleanPath = (pathname || window.location.pathname).replace(/\/+$/, '') || '/';
    return cleanPath === '/';
  }

  function checkAndRedirect() {
    if (shouldRedirectToFeed()) {
      window.location.replace('/feed');
    }
  }

  // Check immediately at document_start
  checkAndRedirect();

  // Intercept Single-Page Application (SPA) navigation
  function hookHistory() {
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function (state, title, url) {
      if (url && typeof url === 'string') {
        try {
          const parsed = new URL(url, window.location.origin);
          if (shouldRedirectToFeed(parsed.pathname)) {
            return originalPushState.apply(this, [state, title, '/feed']);
          }
        } catch (e) {
          // ignore parsing error
        }
      }
      const res = originalPushState.apply(this, arguments);
      cleanPageElements();
      schedulePeriodicCleaning();
      return res;
    };

    history.replaceState = function (state, title, url) {
      if (url && typeof url === 'string') {
        try {
          const parsed = new URL(url, window.location.origin);
          if (shouldRedirectToFeed(parsed.pathname)) {
            return originalReplaceState.apply(this, [state, title, '/feed']);
          }
        } catch (e) {
          // ignore parsing error
        }
      }
      const res = originalReplaceState.apply(this, arguments);
      cleanPageElements();
      schedulePeriodicCleaning();
      return res;
    };

    window.addEventListener('popstate', () => {
      checkAndRedirect();
      cleanPageElements();
      schedulePeriodicCleaning();
    });
  }

  try {
    hookHistory();
  } catch (e) {
    // History hook fallback
  }

  // --- 2. HEADER LOGO ROUTING ---

  function handleLogoClicks(event) {
    if (!config.routeLogoToFeed && !config.defaultToFeed) return;

    const target = event.target;
    if (!target) return;

    const logoLink = target.closest('a.header__logoLink, .header__logo a');
    if (logoLink) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (window.location.pathname !== '/feed') {
        window.location.href = '/feed';
      }
    }
  }

  function updateNavLinks() {
    if (!config.routeLogoToFeed) return;

    const logoLinks = document.querySelectorAll('a.header__logoLink, .header__logo a');
    logoLinks.forEach((link) => {
      if (link.getAttribute('href') !== '/feed') {
        link.setAttribute('href', '/feed');
      }
    });
  }

  // --- 3. REPOSTS TOGGLE (DEFAULT TO OFF) ---

  let repostsTurnedOffForCurrentView = false;

  function isFeedPage() {
    const path = window.location.pathname.replace(/\/+$/, '') || '/';
    return path === '/feed' || path.endsWith('/feed') || path.includes('feed');
  }

  function defaultRepostsToOff() {
    if (!config.defaultRepostsOff) return;
    if (!isFeedPage()) {
      repostsTurnedOffForCurrentView = false;
      return;
    }
    if (repostsTurnedOffForCurrentView) return;

    const candidates = document.querySelectorAll('button, input[type="checkbox"], [role="switch"], [class*="toggle"], [class*="switch"]');
    for (const el of candidates) {
      const parent = el.closest('div, section, header, label');
      const labelText = (parent ? parent.textContent : '') || el.getAttribute('aria-label') || '';

      if (/\breposts\b/i.test(labelText)) {
        const isChecked =
          el.checked === true ||
          el.getAttribute('aria-checked') === 'true' ||
          el.classList.contains('active') ||
          el.classList.contains('checked') ||
          el.classList.contains('m-active') ||
          (el.style && el.style.backgroundColor && el.style.backgroundColor.includes('rgb(255, 85, 0)'));

        if (isChecked) {
          el.click();
          repostsTurnedOffForCurrentView = true;
          break;
        } else if (el.checked === false || el.getAttribute('aria-checked') === 'false') {
          repostsTurnedOffForCurrentView = true;
          break;
        }
      }
    }
  }

  // --- 4. REMOVE PROMOTED TRACKS, PANELS, AND BANNERS ---

  const PROMOTED_INDICATOR_SELECTORS = [
    '.soundContext__promoted',
    '.promotedBadge',
    '.sc-promoted-icon',
    '.sc-promoted-icon-small',
    '.sc-promoted-icon-medium',
    '.promotedBadge__promoter',
    'span[title*="Promoted" i]',
    'a[title*="Promoted" i]',
    '[aria-label*="Promoted" i]',
    '[data-test-id*="promoted" i]'
  ];

  const TRACK_CONTAINER_SELECTORS = [
    'li.soundList__item',
    '.soundList__item',
    '.lazyLoadingList__list > li',
    'ul.sc-list-nostyle > li',
    '.stream__list > li'
  ];

  function isPromotedElement(element) {
    if (!element || !(element instanceof Element)) return false;

    for (const sel of PROMOTED_INDICATOR_SELECTORS) {
      if (element.matches && element.matches(sel)) return true;
      if (element.querySelector && element.querySelector(sel)) return true;
    }

    const soundContext = element.querySelector('.soundContext, .sound__header, .soundTitle__secondary');
    if (soundContext) {
      const text = soundContext.textContent || '';
      if (/\bpromoted\b/i.test(text)) {
        return true;
      }
    }

    return false;
  }

  function cleanPromotedTracks() {
    if (!config.removePromotedTracks) return;

    const trackItems = document.querySelectorAll(TRACK_CONTAINER_SELECTORS.join(', '));
    trackItems.forEach((item) => {
      if (isPromotedElement(item)) {
        item.remove();
      }
    });

    for (const sel of PROMOTED_INDICATOR_SELECTORS) {
      const indicators = document.querySelectorAll(sel);
      indicators.forEach((indicator) => {
        const parentTrack = indicator.closest(TRACK_CONTAINER_SELECTORS.join(', '));
        if (parentTrack) {
          parentTrack.remove();
        } else {
          const soundRoot = indicator.closest('.sound, .soundList__item, [role="group"]');
          if (soundRoot && soundRoot.parentElement) {
            soundRoot.remove();
          }
        }
      });
    }
  }

  function cleanPromotionalPanels() {
    // 1. Remove Top Announcement Banner (supporting delayed loads)
    if (config.removeTopBanner) {
      const bannerSelectors = [
        '.banner',
        '.banner__contentContainer',
        '.announcements',
        '.announcement',
        '[class*="announcement" i]',
        '.crossfade-announcement-wrapper',
        '.l-product-banners',
        '[class*="PromotionBanner" i]'
      ];

      document.querySelectorAll(bannerSelectors.join(', ')).forEach((b) => {
        b.remove();
      });

      // Cleanly remove banners by their dismiss buttons or specific banner containers
      const dismissButtons = document.querySelectorAll('.banner__close, .announcement__dismiss');
      dismissButtons.forEach((btn) => {
        const bannerContainer = btn.closest('.banner, .announcements, .announcement, [class*="banner" i], [class*="announcement" i]');
        if (bannerContainer) {
          bannerContainer.remove();
        }
      });

      // Query specific promotional containers or links for vinyl/promos
      const promoLinks = document.querySelectorAll('a[href*="vinyl-studio"], a[href*="pages/vinyl"]');
      promoLinks.forEach((link) => {
        const promoContainer = link.closest('.banner, .announcements, .announcement, [class*="banner" i], [class*="announcement" i]');
        if (promoContainer) {
          promoContainer.remove();
        }
      });
    }

    // 2. Remove "ARTIST TOOLS" panel in right sidebar
    if (config.removeArtistTools) {
      const sidebarModules = document.querySelectorAll('.sidebarModule, [class*="sidebarModule"]');
      sidebarModules.forEach((mod) => {
        const text = mod.textContent || '';
        if (
          /\bartist tools\b/i.test(text) ||
          mod.querySelector('[id*="credit-tracker"]') ||
          mod.querySelector('iframe[src*="credit-tracker"]')
        ) {
          mod.remove();
        }
      });
    }

    // 3. Remove "Try Go+" and "Try Artist Pro" links at top of header
    if (config.removeUpsellLinks) {
      const upsells = document.querySelectorAll('.header__upsellWrapper, .header__creatorUpsell, .header__fanUpsell, .creatorSubscriptionsButton');
      upsells.forEach((u) => u.remove());

      const headerLinks = document.querySelectorAll('header a, .header a');
      headerLinks.forEach((link) => {
        const text = link.textContent.trim();
        if (/^Try Go\+/i.test(text) || /^Try Artist Pro/i.test(text)) {
          link.remove();
        }
      });
    }
  }

  function cleanPageElements() {
    cleanPromotedTracks();
    cleanPromotionalPanels();
    defaultRepostsToOff();
    updateNavLinks();
  }

  // Periodic cleaning for delayed-loading banners and content
  let periodicCleaningTimer = null;
  function schedulePeriodicCleaning() {
    if (periodicCleaningTimer) clearInterval(periodicCleaningTimer);

    let count = 0;
    periodicCleaningTimer = setInterval(() => {
      cleanPageElements();
      count++;
      if (count > 20) {
        clearInterval(periodicCleaningTimer);
        periodicCleaningTimer = null;
      }
    }, 250);
  }

  // --- 5. DOM SETUP & MUTATION OBSERVER ---

  function initDOMListeners() {
    document.addEventListener('click', handleLogoClicks, true);

    cleanPageElements();
    schedulePeriodicCleaning();

    const observer = new MutationObserver(() => {
      cleanPageElements();
    });

    const targetNode = document.body || document.documentElement;
    if (targetNode) {
      observer.observe(targetNode, {
        childList: true,
        subtree: true
      });
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        if (document.body) {
          observer.observe(document.body, {
            childList: true,
            subtree: true
          });
        }
        cleanPageElements();
        schedulePeriodicCleaning();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDOMListeners);
  } else {
    initDOMListeners();
  }

  // Export functions for testing if running in Node environment
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      config,
      shouldRedirectToFeed,
      isPromotedElement,
      cleanPromotedTracks,
      cleanPromotionalPanels,
      defaultRepostsToOff,
      updateNavLinks
    };
  }
})();
