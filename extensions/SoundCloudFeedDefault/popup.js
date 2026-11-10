/**
 * Popup Script for SoundCloud Feed Default & Promoted Track Cleaner
 */

document.addEventListener('DOMContentLoaded', () => {
  const fields = [
    'defaultToFeed',
    'routeLogoToFeed',
    'removePromotedTracks',
    'defaultRepostsOff',
    'removeArtistTools',
    'removeTopBanner',
    'removeUpsellLinks'
  ];

  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get(fields, (result) => {
      fields.forEach((field) => {
        const el = document.getElementById(field);
        if (el && result[field] !== undefined) {
          el.checked = result[field];
        }
      });
    });

    fields.forEach((field) => {
      const el = document.getElementById(field);
      if (el) {
        el.addEventListener('change', () => {
          chrome.storage.sync.set({ [field]: el.checked });
        });
      }
    });
  }
});
