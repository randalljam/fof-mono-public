export function processJsonToMarkdown(jsonData) {
  const content = jsonData.content;
  let markdownString = `\n\n\n## ${content.user_question}\n`;
  markdownString += `${content.route_preamble}\n\n`;

  if (content.quoted_qa) {
    const quotedQaLines = content.quoted_qa.split('\n');
    let formattedQa = '';
    quotedQaLines.forEach((line) => {
      if (line.trim().startsWith('QUESTION') && !line.trim().startsWith('QUESTION SIMILARITY SCORE')) {
        formattedQa += `### ${line.trim()}\n`;
      } else {
        formattedQa += `${line}\n`;
      }
    });
    markdownString += formattedQa;
  }

  markdownString += `### AI ANSWER:\n${content.ai_answer}`;
  return markdownString;
}

export function simpleMarkdownToHtml(markdownString) {
  let htmlContent = markdownString
    .replace(/^###### (.*$)/gim, '<span style="font-size: 0.67em;">$1</span>')
    .replace(/^##### (.*$)/gim, '<span style="font-size: 0.83em;">$1</span>')
    .replace(/^#### (.*$)/gim, '<span style="font-size: 1em;">$1</span>')
    .replace(/^### (.*$)/gim, '<span style="font-size: 1.17em;"><strong>$1</strong></span>')
    .replace(/^## (.*$)/gim, '<span style="font-size: 1.5em;"><strong>$1</strong></span>')
    .replace(/^# (.*$)/gim, '<span style="font-size: 2em;"><strong>$1</strong></span>');

  htmlContent = htmlContent
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/__(.*?)__/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');

  htmlContent = htmlContent
    .split('\n')
    .map((line) => {
      if (line.startsWith('TOPICS: [')) {
        return line.replace(/\['|'\]|'/g, '');
      }
      if (line.startsWith('SOURCE:')) {
        return line;
      }
      return line.replace(/_(.*?)_/g, '<em>$1</em>');
    })
    .join('\n');

  htmlContent = htmlContent.replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  htmlContent = htmlContent.replace(/\n/g, '<br>');
  return htmlContent.trim();
}

export function processMarkdownToTextAndHtml(markdownString) {
  const htmlContent = simpleMarkdownToHtml(markdownString);
  const firstLine = htmlContent.split('<br>')[0];
  const titleTag = `<span style="font-size: 2em; font-weight: bold;">${firstLine}</span>`;
  const modHtmlContent = htmlContent.replace(firstLine, titleTag);
  const plainTextContent = markdownString
    .replace(/[*_]/g, '')
    .replace(/#/g, '')
    .replace(/\n/g, ' ');
  return { plainText: plainTextContent, html: modHtmlContent };
}

export function displayTempMessage(message, type, duration, targetElement) {
  if (!targetElement) return;
  const botContainer = targetElement.closest('.bot-container');
  if (!botContainer) return;

  let messageDiv = botContainer.querySelector('.temp-message');
  if (!messageDiv) {
    messageDiv = document.createElement('div');
    messageDiv.className = 'temp-message';
    botContainer.insertBefore(messageDiv, botContainer.firstChild);
  }

  messageDiv.textContent = message;
  messageDiv.style.display = 'block';
  messageDiv.style.color = type === 'error' ? 'red' : (type === 'info' ? 'blue' : 'green');

  if (messageDiv.timeout) {
    clearTimeout(messageDiv.timeout);
  }
  messageDiv.timeout = setTimeout(() => {
    messageDiv.style.display = 'none';
  }, duration);
}

export function setButtonToStopState(button, icon) {
  button.classList.add('button-processing');
  button.classList.remove('button-initial');
  if (icon) {
    icon.textContent = 'stop_circle';
    icon.classList.add('icon-stop');
  }
}

export function resetButtonToInitialState(button, icon) {
  button.classList.remove('button-processing');
  button.classList.add('button-initial');
  if (icon) {
    icon.textContent = 'arrow_upward';
    icon.classList.remove('icon-stop');
    icon.classList.add('icon-arrow-up');
  }
}

export function adjustTextareaHeight(textarea, maxRows, lineHeight) {
  textarea.style.height = '';
  const scrollHeight = textarea.scrollHeight;
  const maxHeight = lineHeight * maxRows;
  if (scrollHeight > maxHeight) {
    textarea.style.height = `${maxHeight}px`;
    textarea.style.overflowY = 'auto';
  } else {
    textarea.style.height = `${scrollHeight}px`;
    textarea.style.overflowY = 'hidden';
  }
}

function appendAiAnswerDropdownBlock(jsonData) {
  if (!jsonData.content.ai_answer) return '';
  if (jsonData.content.ai_answer.startsWith('WAITING FOR AI ANSWER') || jsonData.content.ai_answer.startsWith('STILL WAITING FOR AI ANSWER')) {
    return `<div class="accordion-dropdown-text accordion-dropdown-text-waiting">${jsonData.content.ai_answer}</div>`;
  }
  return `<div class="accordion-dropdown-text accordion-dropdown-text-ai-answer"><span class="ai-answer-heading">AI ANSWER:</span><div class="ai-answer-body">${simpleMarkdownToHtml(jsonData.content.ai_answer)}</div></div>`;
}

export function generateDropdownContent(jsonData, displayType) {
  let dropdownContent = '';
  if (displayType === 'ai-answer-only') {
    dropdownContent += appendAiAnswerDropdownBlock(jsonData);
  } else if (displayType === 'quoted-qa-then-ai-answer') {
    dropdownContent += appendAiAnswerDropdownBlock(jsonData);
    if (jsonData.content.route_preamble) {
      dropdownContent += `<div class="accordion-dropdown-text">${simpleMarkdownToHtml(jsonData.content.route_preamble)}</div>`;
    }
    if (jsonData.content.quoted_qa) {
      dropdownContent += `<details class="extracted-quotes" open><summary class="extracted-quotes-summary">EXTRACTED QUOTES</summary><div class="accordion-dropdown-text">${simpleMarkdownToHtml(jsonData.content.quoted_qa)}</div></details>`;
    }
  }
  return dropdownContent;
}

function writeMarkdownToHiddenDiv(jsonData, botContainer, deleteTopHeadingFlag) {
  const MARKDOWN_HEADING_LEVEL = '##';
  const markdownContent = processJsonToMarkdown(jsonData);
  const hiddenDiv = botContainer.querySelector('.hidden-div');
  if (!hiddenDiv) return;

  let initialText = hiddenDiv.textContent;
  if (deleteTopHeadingFlag) {
    const firstHeadingIndex = initialText.indexOf(`\n${MARKDOWN_HEADING_LEVEL} `);
    if (firstHeadingIndex !== -1) {
      const nextHeadingIndex = initialText.indexOf(`\n${MARKDOWN_HEADING_LEVEL} `, firstHeadingIndex + 1);
      const preHeadingText = initialText.substring(0, firstHeadingIndex);
      if (nextHeadingIndex === -1) {
        initialText = preHeadingText;
      } else {
        initialText = preHeadingText + initialText.substring(nextHeadingIndex);
      }
    }
  }
  hiddenDiv.textContent = initialText;

  const firstMarkdownHeaderIndex = initialText.search(/##\s/);
  let insertionPoint;
  if (firstMarkdownHeaderIndex !== -1) {
    insertionPoint = initialText.substring(0, firstMarkdownHeaderIndex).search(/\S\s*$/) + 1;
  } else {
    insertionPoint = initialText.search(/\S\s*$/) + 1;
  }
  hiddenDiv.textContent = initialText.substring(0, insertionPoint) + markdownContent + initialText.substring(insertionPoint);
}

export function createAccordionItem(jsonData, submitButtonId, buttonParamsMapping) {
  const botContainer = document.getElementById(`container_${submitButtonId.replace('submitButton_', '')}`);
  if (!botContainer) return;

  if (!botContainer.querySelector('.hidden-div')) {
    createHiddenDivAndShareElements(botContainer, submitButtonId, buttonParamsMapping);
  }

  const accordionCard = botContainer.querySelector('.accordion-card');
  const accordionItem = document.createElement('div');
  accordionItem.className = 'accordion-item';

  const accordionToggle = document.createElement('div');
  accordionToggle.className = 'accordion-toggle';
  const userQuestion = jsonData.content.user_question.replace(/\n/g, '<br>');
  accordionToggle.innerHTML = `
    <div class="accordion-icon" aria-hidden="true">▸</div>
    <div class="accordion-title-text">${userQuestion}</div>
  `;

  const icon = accordionToggle.querySelector('.accordion-icon');
  icon.addEventListener('click', (e) => {
    e.stopPropagation();
    const dropdownList = accordionToggle.nextElementSibling;
    const isCollapsed = dropdownList.style.display === 'none';
    dropdownList.style.display = isCollapsed ? 'block' : 'none';
    icon.style.transform = isCollapsed ? 'rotate(90deg)' : 'rotate(0deg)';
  });

  const params = buttonParamsMapping[submitButtonId];
  const dropdownList = document.createElement('div');
  dropdownList.className = 'accordion-dropdown-list';
  dropdownList.style.display = 'block';
  dropdownList.innerHTML = generateDropdownContent(jsonData, params.displayType);

  writeMarkdownToHiddenDiv(jsonData, botContainer, false);
  accordionItem.appendChild(accordionToggle);
  accordionItem.appendChild(dropdownList);
  accordionCard.insertBefore(accordionItem, accordionCard.firstChild);
}

export function replaceAccordionItem(jsonData, submitButtonId, buttonParamsMapping) {
  const botContainer = document.getElementById(`container_${submitButtonId.replace('submitButton_', '')}`);
  if (!botContainer) return;

  const accordionCard = botContainer.querySelector('.accordion-card');
  const accordionItem = accordionCard?.querySelector('.accordion-item');
  if (!accordionItem) return;

  const accordionTitleText = accordionItem.querySelector('.accordion-title-text');
  accordionTitleText.innerHTML = jsonData.content.user_question.replace(/\n/g, '<br>');

  const params = buttonParamsMapping[submitButtonId];
  const dropdownList = accordionItem.querySelector('.accordion-dropdown-list');
  dropdownList.innerHTML = generateDropdownContent(jsonData, params.displayType);
  writeMarkdownToHiddenDiv(jsonData, botContainer, true);
}

function createHiddenDivAndShareElements(botContainer, submitButtonId, buttonParamsMapping) {
  const botTitle = buttonParamsMapping[submitButtonId].botTitle;
  const hiddenDiv = document.createElement('div');
  hiddenDiv.className = 'hidden-div';
  hiddenDiv.style.display = 'none';
  hiddenDiv.textContent = `${botTitle}\nby Randy True of focusonfoundations.org`;

  const shareDiv = document.createElement('div');
  shareDiv.className = 'share-div';
  shareDiv.innerHTML = `
    <div class="share-actions">
      <button type="button" class="icon-button" data-action="download" aria-label="Download"><span class="material-symbols-rounded">download</span></button>
      <button type="button" class="icon-button" data-action="email" aria-label="Email"><span class="material-symbols-rounded">mail</span></button>
      <div class="email-send-container" style="display:none">
        <input type="email" class="email-input-address" placeholder="Enter your email" autocomplete="email" data-lpignore="true" data-1p-ignore data-bwignore>
        <button type="button" class="email-send-button" data-action="email-send" aria-label="Send email"><span class="material-symbols-rounded">send</span></button>
      </div>
    </div>
    <div class="email-checkbox-container" style="display:none">
      <input type="checkbox" class="email-checkbox" id="email-list-${submitButtonId}">
      <label for="email-list-${submitButtonId}">Add me to the email list for updates to this project.</label>
    </div>
    <p class="email-status" style="display:none"></p>
  `;

  const resultsBox = botContainer.querySelector('.results-box');
  const accordionContainer = botContainer.querySelector('.accordion-container');
  botContainer.insertBefore(hiddenDiv, resultsBox);
  resultsBox.insertBefore(shareDiv, accordionContainer);
}

export function downloadMarkdown(botContainer, notifyCallback) {
  const hiddenDiv = botContainer.querySelector('.hidden-div');
  const markdownContent = hiddenDiv.textContent;
  const now = new Date();
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Los_Angeles',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const parts = formatter.formatToParts(now);
  const dateMap = {};
  parts.forEach((part) => { dateMap[part.type] = part.value; });
  const dateStr = `${dateMap.year}-${dateMap.month}-${dateMap.day}_${dateMap.hour}${dateMap.minute}${dateMap.second}`;

  let botType = 'QRag';
  const containerId = botContainer.id;
  if (containerId.includes('deutsch')) botType = 'QRAG-Deutsch';
  else if (containerId.includes('pv-evac')) botType = 'QRAG-PV-EPC';
  else if (containerId.includes('fda-townhalls')) botType = 'QRAG-FDATownHalls';
  else if (containerId.includes('sovereign-child')) botType = 'QRAG-SovereignChild';

  const filename = `FOF_AI-Tool_${dateStr}_${botType}.md`;
  const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  if (notifyCallback) notifyCallback('Download', markdownContent);
}
