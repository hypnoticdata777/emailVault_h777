const ADD_ON_TITLE = 'Email Vault';
const DEFAULT_CATEGORY = 'General';

/**
 * Home card shown when Gmail has not provided a selected message context.
 */
function onHomepage() {
  return buildStatusCard_(
    'Open a Gmail thread',
    'Email Vault appears after a message is opened. The current shell is preview-only.'
  );
}

/**
 * Gmail contextual entry point. This may read the current message/thread for a
 * user preview, but it must not mutate Gmail state.
 */
function onGmailMessageOpen(event) {
  const preview = readSelectedThreadPreview_(event);
  return buildThreadPreviewCard_(preview);
}

/**
 * Placeholder action for the confirmation button. Backend orchestration is not
 * wired yet, so this deliberately performs no Gmail label/read/archive action.
 */
function archiveThreadAction(event) {
  const category = valueOrDefault_(formValue_(event, 'category'), DEFAULT_CATEGORY);
  const markRead = formValue_(event, 'markReadAfterPreserve') === 'true';
  const archive = formValue_(event, 'archiveAfterPreserve') === 'true';

  return CardService.newActionResponseBuilder()
    .setNotification(
      CardService.newNotification().setText(
        'Preview captured for "' + category + '". Gmail is unchanged until backend preservation is complete.'
      )
    )
    .setNavigation(CardService.newNavigation().updateCard(buildStatusCard_(
      'Preview ready',
      preferenceSummary_(category, markRead, archive)
    )))
    .build();
}

function buildThreadPreviewCard_(preview) {
  const section = CardService.newCardSection()
    .addWidget(CardService.newDecoratedText().setTopLabel('Thread').setText(preview.subject))
    .addWidget(CardService.newDecoratedText().setTopLabel('Messages').setText(String(preview.messageCount)))
    .addWidget(CardService.newTextInput().setFieldName('category').setTitle('Category').setValue(DEFAULT_CATEGORY))
    .addWidget(CardService.newSelectionInput()
      .setType(CardService.SelectionInputType.CHECK_BOX)
      .setFieldName('markReadAfterPreserve')
      .addItem('Mark read after verified preservation', 'true', false))
    .addWidget(CardService.newSelectionInput()
      .setType(CardService.SelectionInputType.CHECK_BOX)
      .setFieldName('archiveAfterPreserve')
      .addItem('Archive after verified preservation', 'true', false))
    .addWidget(CardService.newTextButton()
      .setText('Prepare Archive')
      .setTextButtonStyle(CardService.TextButtonStyle.FILLED)
      .setOnClickAction(CardService.newAction().setFunctionName('archiveThreadAction')));

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle(ADD_ON_TITLE).setSubtitle('Preview-only shell'))
    .addSection(section)
    .build();
}

function buildStatusCard_(title, message) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle(ADD_ON_TITLE).setSubtitle(title))
    .addSection(CardService.newCardSection().addWidget(CardService.newTextParagraph().setText(message)))
    .build();
}

function readSelectedThreadPreview_(event) {
  const fallback = {
    subject: 'Selected Gmail thread',
    messageCount: 1
  };

  if (!event || !event.gmail || !event.gmail.messageId || !event.gmail.accessToken) {
    return fallback;
  }

  GmailApp.setCurrentMessageAccessToken(event.gmail.accessToken);
  const message = GmailApp.getMessageById(event.gmail.messageId);
  const thread = message.getThread();
  return {
    subject: valueOrDefault_(thread.getFirstMessageSubject(), fallback.subject),
    messageCount: thread.getMessageCount()
  };
}

function preferenceSummary_(category, markRead, archive) {
  const readText = markRead ? 'mark read after verification' : 'leave read state unchanged';
  const archiveText = archive ? 'archive after verification' : 'leave in mailbox after verification';
  return 'Category: ' + category + '. Requested follow-up: ' + readText + '; ' + archiveText + '.';
}

function valueOrDefault_(value, fallback) {
  if (value === null || value === undefined || String(value).trim() === '') {
    return fallback;
  }
  return String(value).trim();
}

function formValue_(event, fieldName) {
  if (event && event.formInput && event.formInput[fieldName]) {
    return event.formInput[fieldName];
  }

  const formInputs = event && event.commonEventObject && event.commonEventObject.formInputs;
  const field = formInputs && formInputs[fieldName];
  if (!field) {
    return '';
  }
  if (field.stringInputs && field.stringInputs.value && field.stringInputs.value.length > 0) {
    return field.stringInputs.value[0];
  }
  if (field.dateInput) {
    return field.dateInput.msSinceEpoch;
  }
  return '';
}
