(function () {
  'use strict';

  const STORAGE_KEY = 'bc_clean_player_volume';
  let currentVolume = parseFloat(localStorage.getItem(STORAGE_KEY));
  if (isNaN(currentVolume) || currentVolume < 0 || currentVolume > 1) {
    currentVolume = 0.8;
  }

  function applyVolumeToAudioElements(volume) {
    const audioElements = document.querySelectorAll('audio');
    audioElements.forEach((audio) => {
      audio.volume = volume;
    });
  }

  function setupAudioVolumeBinding() {
    applyVolumeToAudioElements(currentVolume);

    // Watch for new <audio> elements added to DOM or attribute changes
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'AUDIO') {
              node.volume = currentVolume;
            } else {
              const audios = node.querySelectorAll && node.querySelectorAll('audio');
              if (audios) {
                audios.forEach((audio) => {
                  audio.volume = currentVolume;
                });
              }
            }
          }
        });
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Also override HTMLAudioElement prototype / play events if needed
    document.addEventListener('play', (e) => {
      if (e.target && e.target.tagName === 'AUDIO') {
        e.target.volume = currentVolume;
      }
    }, true);
  }

  function setupVolumeSliderInPlayer() {
    const playerTable = document.querySelector('.inline_player table');
    if (!playerTable) return;

    if (playerTable.querySelector('.volume_cell')) {
      return; // Already initialized
    }

    const playCell = playerTable.querySelector('td.play_cell');
    if (playCell) {
      playCell.setAttribute('rowspan', '3');
    }

    const volRow = document.createElement('tr');
    volRow.className = 'volume_row';

    const volTd = document.createElement('td');
    volTd.className = 'volume_cell';
    volTd.setAttribute('colspan', '3');

    const volContainer = document.createElement('div');
    volContainer.className = 'bc-volume-container';

    // Speaker icon SVG
    const iconBtn = document.createElement('span');
    iconBtn.className = 'bc-volume-icon';
    iconBtn.title = 'Mute / Unmute';
    iconBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
      </svg>
    `;

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.className = 'bc-volume-slider';
    slider.min = '0';
    slider.max = '1';
    slider.step = '0.01';
    slider.value = currentVolume;

    const valLabel = document.createElement('span');
    valLabel.className = 'bc-volume-value';
    valLabel.textContent = Math.round(currentVolume * 100) + '%';

    let lastNonZeroVolume = currentVolume > 0 ? currentVolume : 0.8;

    slider.addEventListener('input', (e) => {
      const vol = parseFloat(e.target.value);
      currentVolume = vol;
      if (vol > 0) {
        lastNonZeroVolume = vol;
      }
      localStorage.setItem(STORAGE_KEY, currentVolume.toString());
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ [STORAGE_KEY]: currentVolume });
      }
      valLabel.textContent = Math.round(vol * 100) + '%';
      applyVolumeToAudioElements(currentVolume);
    });

    iconBtn.addEventListener('click', () => {
      if (currentVolume > 0) {
        lastNonZeroVolume = currentVolume;
        currentVolume = 0;
      } else {
        currentVolume = lastNonZeroVolume;
      }
      slider.value = currentVolume;
      valLabel.textContent = Math.round(currentVolume * 100) + '%';
      localStorage.setItem(STORAGE_KEY, currentVolume.toString());
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ [STORAGE_KEY]: currentVolume });
      }
      applyVolumeToAudioElements(currentVolume);
    });

    volContainer.appendChild(iconBtn);
    volContainer.appendChild(slider);
    volContainer.appendChild(valLabel);
    volTd.appendChild(volContainer);
    volRow.appendChild(volTd);

    playerTable.appendChild(volRow);
  }

  function init() {
    setupAudioVolumeBinding();
    setupVolumeSliderInPlayer();

    // Re-check periodically or on DOM changes for dynamically loaded players
    const observer = new MutationObserver(() => {
      setupVolumeSliderInPlayer();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
