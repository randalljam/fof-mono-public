/**
 * Van11y accordion transcript viewer — port of webflow-cms-template-van11y-accordion.html
 */
import { marked } from 'marked';

const ACCORDION_CONFIG = {
  LEVEL1_DEFAULT_OPEN: true,
  LEVEL2_QA_DEFAULT_OPEN: true,
  QUESTIONS_DEFAULT_OPEN: false,
};

function shouldOpenHeading(level, headerText, headingPath) {
  if (level === 1) return ACCORDION_CONFIG.LEVEL1_DEFAULT_OPEN;
  if (level === 2) {
    return headerText.trim().startsWith('Questions and Answers')
      ? ACCORDION_CONFIG.LEVEL2_QA_DEFAULT_OPEN
      : false;
  }
  if (level === 3) {
    return headingPath[1]?.trim().startsWith('Questions and Answers')
      ? ACCORDION_CONFIG.QUESTIONS_DEFAULT_OPEN
      : false;
  }
  return false;
}

function processContentToAccordion(htmlContent) {
  const MAX_HEADING_LEVEL = 4;
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, 'text/html');
  const children = Array.from(doc.body.childNodes);
  let index = 0;
  const stack = [];
  const headingPath = [];
  const rootAccordion = document.createElement('div');
  rootAccordion.className = 'js-accordion';
  rootAccordion.setAttribute('data-accordion-prefix-classes', 'minimalist');
  stack.push({ container: rootAccordion, level: 0 });
  while (index < children.length) {
    const node = children[index];
    if (node.nodeType === Node.ELEMENT_NODE && /^H[1-4]$/.test(node.tagName)) {
      const level = parseInt(node.tagName.substring(1), 10);
      const headerText = node.innerHTML;
      while (stack.length > 0 && level <= stack[stack.length - 1].level) {
        stack.pop();
      }
      if (stack.length === 0) {
        stack.push({ container: rootAccordion, level: 0 });
      }
      const parentAccordion = stack[stack.length - 1].container;
      headingPath[level - 1] = headerText;
      headingPath.length = level;
      const isOpened = shouldOpenHeading(level, headerText, headingPath);
      const header = document.createElement('div');
      header.className = 'js-accordion__header';
      header.classList.add(`level-${level}`);
      header.innerHTML = headerText;
      header.setAttribute('data-level', level);
      if (isOpened) header.setAttribute('data-accordion-opened', 'true');
      parentAccordion.appendChild(header);
      const panel = document.createElement('div');
      panel.className = 'js-accordion__panel minimalist-accordion__panel';
      panel.classList.add(`level-${level}`);
      parentAccordion.appendChild(panel);
      if (level < MAX_HEADING_LEVEL) {
        const nestedAccordion = document.createElement('div');
        nestedAccordion.className = 'js-accordion';
        nestedAccordion.setAttribute('data-accordion-prefix-classes', 'minimalist');
        panel.appendChild(nestedAccordion);
        const nextNode = children[index + 1];
        panel.classList.add(nextNode && /^H[1-4]$/.test(nextNode.tagName) ? 'has-subheadings' : 'has-content');
        stack.push({ container: nestedAccordion, level });
      } else {
        panel.classList.add('has-content');
        stack.push({ container: panel, level });
      }
      index += 1;
    } else {
      if (stack.length === 0) {
        index += 1;
        continue;
      }
      const currentItem = stack[stack.length - 1];
      const currentContainer = currentItem.container;
      const currentLevel = currentItem.level;
      if (currentLevel < MAX_HEADING_LEVEL) {
        const lastPanel = currentContainer.querySelector('.js-accordion__panel.minimalist-accordion__panel:last-child');
        if (lastPanel) lastPanel.appendChild(node.cloneNode(true));
        else currentContainer.appendChild(node.cloneNode(true));
      } else {
        currentContainer.appendChild(node.cloneNode(true));
      }
      index += 1;
    }
  }
  return rootAccordion;
}

export function renderVan11yMarkdown(contentDiv, markdownContent) {
  if (!contentDiv || !markdownContent) return;
  const content = markdownContent.replace(/<<NL>>/g, '\n');
  const renderer = new marked.Renderer();
  renderer.link = function link(href, title, text) {
    const baseLink = marked.Renderer.prototype.link.call(this, href, title, text);
    return baseLink.replace('<a', '<a target="_blank" rel="noopener"');
  };
  const htmlContent = marked.parse(content, { renderer, breaks: true });
  contentDiv.innerHTML = '';
  contentDiv.appendChild(processContentToAccordion(htmlContent));
  if (typeof van11yAccessibleAccordionAria === 'function') {
    const accordion = van11yAccessibleAccordionAria();
    accordion.attach(contentDiv);
  }
}

export function initVan11yTranscript(rootId, markdownContent) {
  const contentDiv = document.getElementById(rootId);
  if (!contentDiv) return;
  renderVan11yMarkdown(contentDiv, markdownContent);
}
