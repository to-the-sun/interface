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
    routeLogoToFeed: true
  };

  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get(['defaultToFeed', 'removePromotedTracks', 'routeLogoToFeed'], (result) => {
      if (result.defaultToFeed !== undefined) config.defaultToFeed = result.defaultToFeed;
      if (result.removePromotedTracks !== undefined) config.removePromotedTracks = result.removePromotedTracks;
      if (result.routeLogoToFeed !== undefined) config.routeLogoToFeed = result.routeLogoToFeed;
    });

    chrome.storage.onChanged.addListener((changes) => {
      if (changes.defaultToFeed) config.defaultToFeed = changes.defaultToFeed.newValue;
      if (changes.removePromotedTracks) config.removePromotedTracks = changes.removePromotedTracks.newValue;
      if (changes.routeLogoToFeed) config.routeLogoToFeed = changes.routeLogoToFeed.newValue;
    });
  }

  // --- 1. DEFAULT TO FEED REDIRECTION ---

  function shouldRedirectToFeed(pathname) {
    if (!config.defaultToFeed) return false;
    const cleanPath = (pathname || window.location.pathname).replace(/\/+$/, '') || '/';
    return (
      cleanPath === '/' ||
      cleanPath === '/discover' ||
      cleanPath === '/home'
    );
  }

  function checkAndRedirect() {
    if (shouldRedirectToFeed()) {
      // Use replace to prevent polluting browser history
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
      cleanPromotedTracks();
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
      cleanPromotedTracks();
      return res;
    };

    window.addEventListener('popstate', () => {
      checkAndRedirect();
      cleanPromotedTracks();
    });
  }

  try {
    hookHistory();
  } catch (e) {
    // History hook fallback
  }

  // --- 2. HEADER LOGO & HOME ROUTING ---

  function handleLogoAndHomeClicks(event) {
    if (!config.defaultToFeed) return;

    // Check if clicked element is inside header logo link or Home menu item
    const target = event.target;
    if (!target) return;

    const logoLink = target.closest('a.header__logoLink, .header__logo a, a[data-menu-name="home"]');
    if (logoLink) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (window.location.pathname !== '/feed') {
        window.location.href = '/feed';
      }
    }
  }

  // Update link hrefs when header is available in DOM
  function updateNavLinks() {
    if (!config.routeLogoToFeed) return;

    const logoLinks = document.querySelectorAll('a.header__logoLink, .header__logo a, a[data-menu-name="home"]');
    logoLinks.forEach((link) => {
      if (link.getAttribute('href') !== '/feed') {
        link.setAttribute('href', '/feed');
      }
    });
  }

  // --- 3. REMOVE PROMOTED TRACKS ---

  /**
   * Selectors identifying promoted track indicators within track elements or list items
   */
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

  /**
   * Container selectors representing a track entry in lists
   */
  const TRACK_CONTAINER_SELECTORS = [
    'li.soundList__item',
    '.soundList__item',
    '.lazyLoadingList__list > li',
    'ul.sc-list-nostyle > li',
    '.stream__list > li'
  ];

  function isPromotedElement(element) {
    if (!element || !(element instanceof Element)) return false;

    // Direct check for text content or indicators
    for (const sel of PROMOTED_INDICATOR_SELECTORS) {
      if (element.matches && element.matches(sel)) return true;
      if (element.querySelector && element.querySelector(sel)) return true;
    }

    // Check for "Promoted" text badge inside sound badge / sound header
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

    // Check all track containers
    const trackItems = document.querySelectorAll(TRACK_CONTAINER_SELECTORS.join(', '));
    trackItems.forEach((item) => {
      if (isPromotedElement(item)) {
        item.remove();
      }
    });

    // Also look specifically for promoted elements anywhere inside list containers
    for (const sel of PROMOTED_INDICATOR_SELECTORS) {
      const indicators = document.querySelectorAll(sel);
      indicators.forEach((indicator) => {
        const parentTrack = indicator.closest(TRACK_CONTAINER_SELECTORS.join(', '));
        if (parentTrack) {
          parentTrack.remove();
        } else {
          // If not in a known list container, find the highest sound component
          const soundRoot = indicator.closest('.sound, .soundList__item, [role="group"]');
          if (soundRoot && soundRoot.parentElement) {
            soundRoot.remove();
          }
        }
      });
    }

    updateNavLinks();
  }

  // --- 4. DOM SETUP & MUTATION OBSERVER ---

  function initDOMListeners() {
    // Capture-phase click listener for logo & home
    document.addEventListener('click', handleLogoAndHomeClicks, true);

    // Initial pass
    cleanPromotedTracks();
    updateNavLinks();

    // Observe subsequent DOM updates (lazy loading lists, navigation changes)
    const observer = new MutationObserver((mutations) => {
      let shouldClean = false;
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          shouldClean = true;
          break;
        }
      }
      if (shouldClean) {
        cleanPromotedTracks();
      }
    });

    if (document.body) {
      observer.observe(document.body, {
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
        cleanPromotedTracks();
        updateNavLinks();
      });
    }
  }

  // Initialize listeners when document is accessible
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
      updateNavLinks
    };
  }
})();
