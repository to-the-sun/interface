/**
 * Popup Script for SoundCloud Feed Default & Promoted Track Cleaner
 */

document.addEventListener('DOMContentLoaded', () => {
  const defaultToFeedToggle = document.getElementById('defaultToFeed');
  const routeLogoToFeedToggle = document.getElementById('routeLogoToFeed');
  const removePromotedTracksToggle = document.getElementById('removePromotedTracks');

  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get(['defaultToFeed', 'routeLogoToFeed', 'removePromotedTracks'], (result) => {
      if (result.defaultToFeed !== undefined) {
        defaultToFeedToggle.checked = result.defaultToFeed;
      }
      if (result.routeLogoToFeed !== undefined) {
        routeLogoToFeedToggle.checked = result.routeLogoToFeed;
      }
      if (result.removePromotedTracks !== undefined) {
        removePromotedTracksToggle.checked = result.removePromotedTracks;
      }
    });

    defaultToFeedToggle.addEventListener('change', () => {
      chrome.storage.sync.set({ defaultToFeed: defaultToFeedToggle.checked });
    });

    routeLogoToFeedToggle.addEventListener('change', () => {
      chrome.storage.sync.set({ routeLogoToFeed: routeLogoToFeedToggle.checked });
    });

    removePromotedTracksToggle.addEventListener('change', () => {
      chrome.storage.sync.set({ removePromotedTracks: removePromotedTracksToggle.checked });
    });
  }
});
