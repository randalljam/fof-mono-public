/**
 * Client-side transcript/Q&A viewer — port of webflow-cms-template-embed*.html
 */

export function applyToggleLevel(container, level, variant, hasH4Sections) {
  if (!container) return;
  const useFullControls = variant === 'fda' || hasH4Sections;
  const details = container.querySelectorAll('details');
  if (!useFullControls) {
    if (level === 'collapse') {
      details.forEach((detail) => detail.removeAttribute('open'));
    } else if (level === 'all') {
      details.forEach((detail) => detail.setAttribute('open', ''));
    }
    return;
  }
  if (level === 'collapse') {
    details.forEach((detail) => detail.removeAttribute('open'));
    return;
  }
  details.forEach((detail) => {
    switch (level) {
      case 'sections':
        detail.setAttribute('open', '');
        break;
      case 'questions':
        if (detail.parentElement.tagName !== 'DETAILS') {
          detail.setAttribute('open', '');
        } else {
          detail.removeAttribute('open');
        }
        break;
      case 'answers':
        if (
          detail.parentElement.tagName === 'DETAILS'
          && detail.parentElement.parentElement.tagName !== 'DETAILS'
        ) {
          detail.setAttribute('open', '');
          detail.parentElement.setAttribute('open', '');
        }
        break;
      case 'all':
        detail.setAttribute('open', '');
        break;
      default:
        break;
    }
  });
}

export function detectHasH4Sections(container) {
  return Boolean(container?.querySelector('h4'));
}

export async function fetchTranscriptHtml(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load content (${response.status})`);
  }
  return response.text();
}

export function wireTranscriptViewer(root, options) {
  const {
    transcriptUrl,
    qaUrl,
    variant = 'generic',
  } = options;
  const transcriptContainer = root.querySelector('[data-transcript-container]');
  const qaContainer = root.querySelector('[data-qa-container]');
  if (!transcriptContainer || !qaContainer) {
    throw new Error('Transcript viewer containers not found');
  }
  let hasH4Sections = variant === 'fda';
  let toggleDocButton = null;

  function getVisibleContainer() {
    return transcriptContainer.style.display !== 'none' ? transcriptContainer : qaContainer;
  }

  function bindToggleDocButton(container) {
    const button = container.querySelector('#toggleDocButton');
    if (!button || button === toggleDocButton) return;
    toggleDocButton = button;
    button.addEventListener('click', () => {
      const transcriptVisible = transcriptContainer.style.display !== 'none';
      if (transcriptVisible) {
        transcriptContainer.style.display = 'none';
        qaContainer.style.display = 'block';
        button.textContent = 'View Q&A';
      } else {
        qaContainer.style.display = 'none';
        transcriptContainer.style.display = 'block';
        button.textContent = 'View Transcript';
      }
    });
  }

  function updateControlPanel(container) {
    if (variant !== 'fda' && container === transcriptContainer) {
      hasH4Sections = detectHasH4Sections(container);
      const controlPanel = container.querySelector('.control-panel');
      if (controlPanel && !hasH4Sections) {
        controlPanel.style.display = 'none';
      }
    }
    if (variant !== 'fda' && container === qaContainer && !hasH4Sections) {
      const controlPanel = container.querySelector('.control-panel');
      if (controlPanel) {
        controlPanel.querySelectorAll('button').forEach((button) => {
          if (
            button.textContent.includes('Questions')
            || button.textContent.includes('Answers')
            || button.textContent.includes('Sections')
          ) {
            button.style.display = 'none';
          }
        });
      }
    }
    bindToggleDocButton(container);
  }

  async function loadContent(url, container) {
    try {
      container.innerHTML = await fetchTranscriptHtml(url);
      updateControlPanel(container);
    } catch (error) {
      console.error('Error loading transcript content:', error);
      container.innerHTML = '<p>Error loading content. Please try again later.</p>';
    }
  }

  root.toggleLevel = (level) => {
    applyToggleLevel(getVisibleContainer(), level, variant, hasH4Sections);
  };

  if (typeof window !== 'undefined') {
    window.toggleLevel = root.toggleLevel;
  }

  return Promise.all([
    loadContent(transcriptUrl, transcriptContainer),
    loadContent(qaUrl, qaContainer),
  ]);
}

export function initTranscriptViewer(rootId, options) {
  const root = document.getElementById(rootId);
  if (!root) return Promise.resolve();
  return wireTranscriptViewer(root, options);
}
export function initTranscriptViewers(scope = document) {
  const roots = scope.querySelectorAll('[data-transcript-viewer]');
  return Promise.all(Array.from(roots).map((root) => wireTranscriptViewer(root, {
    transcriptUrl: root.dataset.transcriptUrl,
    qaUrl: root.dataset.qaUrl,
    variant: root.dataset.variant || 'generic',
  })));
}
