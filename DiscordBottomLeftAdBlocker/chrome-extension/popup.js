// Discord Bottom-Left Ad Blocker Popup Script

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const masterEnable = document.getElementById('master-enable');
  const blockedCount = document.getElementById('blocked-count');
  const resetStatsBtn = document.getElementById('reset-stats');
  const blockQuests = document.getElementById('block-quests');
  const blockNitro = document.getElementById('block-nitro');
  const blockPopups = document.getElementById('block-popups');

  // Load and populate settings
  chrome.storage.local.get({
    enabled: true,
    blockedCount: 0,
    blockQuests: true,
    blockNitro: true,
    blockPopups: true
  }, (items) => {
    masterEnable.checked = items.enabled;
    blockedCount.textContent = items.blockedCount.toLocaleString();
    blockQuests.checked = items.blockQuests;
    blockNitro.checked = items.blockNitro;
    blockPopups.checked = items.blockPopups;

    // Toggle grey out if master disabled
    toggleSettingsDisableState(!items.enabled);
  });

  // Helper to grey out/disable settings if blocker is turned off
  function toggleSettingsDisableState(isDisabled) {
    const settingItems = document.querySelectorAll('.setting-item');
    settingItems.forEach(item => {
      if (isDisabled) {
        item.style.opacity = '0.5';
        item.querySelector('input').disabled = true;
      } else {
        item.style.opacity = '1';
        item.querySelector('input').disabled = false;
      }
    });
  }

  // Save config state helper
  function saveAndPropagateConfig() {
    const config = {
      enabled: masterEnable.checked,
      blockQuests: blockQuests.checked,
      blockNitro: blockNitro.checked,
      blockPopups: blockPopups.checked
    };

    chrome.storage.local.set(config, () => {
      // Propagate config updates to any active Discord tabs
      chrome.tabs.query({ url: '*://*.discord.com/*' }, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            action: 'updateConfig',
            config: config
          }).catch(() => {
            // Tab might be in background or still loading, ignore error
          });
        });
      });
    });
  }

  // Event Listeners for controls
  masterEnable.addEventListener('change', () => {
    toggleSettingsDisableState(!masterEnable.checked);
    saveAndPropagateConfig();
  });

  blockQuests.addEventListener('change', saveAndPropagateConfig);
  blockNitro.addEventListener('change', saveAndPropagateConfig);
  blockPopups.addEventListener('change', saveAndPropagateConfig);

  // Reset stats button click listener
  resetStatsBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to reset the blocked advertisements counter?')) {
      chrome.storage.local.set({ blockedCount: 0 }, () => {
        blockedCount.textContent = '0';
      });
    }
  });

  // Periodically refresh the blocked ad count while popup is open
  setInterval(() => {
    chrome.storage.local.get({ blockedCount: 0 }, (items) => {
      blockedCount.textContent = items.blockedCount.toLocaleString();
    });
  }, 1000);
});
