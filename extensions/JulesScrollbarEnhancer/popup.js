document.addEventListener('DOMContentLoaded', () => {
  const toggleEnabled = document.getElementById('toggle-enabled');
  const sizeBtns = document.querySelectorAll('.size-btn');
  const statusMsg = document.getElementById('status-msg');

  const DEFAULT_SETTINGS = {
    enabled: true,
    scrollbarSize: '18px'
  };

  function showStatus() {
    statusMsg.classList.add('visible');
    setTimeout(() => {
      statusMsg.classList.remove('visible');
    }, 1500);
  }

  function updateUI(settings) {
    toggleEnabled.checked = settings.enabled;
    sizeBtns.forEach(btn => {
      if (btn.dataset.size === settings.scrollbarSize) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function saveSettings(newSettings) {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
      chrome.storage.sync.set(newSettings, () => {
        showStatus();
      });
    }

    // Notify active tabs matching jules.google.com
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      chrome.tabs.query({ url: 'https://jules.google.com/*' }, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            type: 'SETTINGS_UPDATED',
            settings: newSettings
          });
        });
      });
    }
  }

  // Load current settings
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (settings) => {
      updateUI(settings);
    });
  } else {
    updateUI(DEFAULT_SETTINGS);
  }

  // Event Listeners
  toggleEnabled.addEventListener('change', () => {
    const enabled = toggleEnabled.checked;
    const activeBtn = document.querySelector('.size-btn.active');
    const scrollbarSize = activeBtn ? activeBtn.dataset.size : '18px';

    saveSettings({ enabled, scrollbarSize });
  });

  sizeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      sizeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const enabled = toggleEnabled.checked;
      const scrollbarSize = btn.dataset.size;

      saveSettings({ enabled, scrollbarSize });
    });
  });
});
