const ADD_ON_TITLE = 'Email Vault';
const DEFAULT_CATEGORY = 'General';
const ADD_ON_VERSION = '0.1.0';
const ARCHIVE_THREAD_PATH = '/archive/thread';
const GMAIL_FINALIZATION_PATH = '/archive/thread/gmail-finalization';
const GMAIL_FINALIZATION_CALLBACK_PATH = '/archive/thread/gmail-finalization/callback';
const BACKEND_URL_PROPERTY = 'EMAIL_VAULT_BACKEND_URL';
const BACKEND_SIGNING_SECRET_PROPERTY = 'EMAIL_VAULT_ADDON_SIGNING_SECRET';
const BACKEND_SIGNATURE_VERSION = 'v1';
const BACKEND_TIMESTAMP_HEADER = 'X-Email-Vault-Timestamp';
const BACKEND_SIGNATURE_HEADER = 'X-Email-Vault-Signature';

// PROJECT BEACON: This shell is the Gmail-facing entry point; it previews and
// signs requests, while the backend owns preservation and mutation boundaries.

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
 * Confirmation button action. This can call the backend only when deployment
 * properties are configured, and it deliberately performs no Gmail mutation.
 */
function archiveThreadAction(event) {
  const category = valueOrDefault_(formValue_(event, 'category'), DEFAULT_CATEGORY);
  const markRead = formValue_(event, 'markReadAfterPreserve') === 'true';
  const archive = formValue_(event, 'archiveAfterPreserve') === 'true';
  const config = readBackendConfig_();

  if (!config.configured) {
    return buildActionResponse_(
      'Backend is not configured. Gmail is unchanged.',
      buildStatusCard_('Configuration needed', preferenceSummary_(category, markRead, archive))
    );
  }

  try {
    const payload = buildArchiveThreadRequest_(event, category, markRead, archive);
    const idToken = ScriptApp.getIdentityToken();
    if (!idToken) {
      return buildActionResponse_(
        'Google identity token is unavailable. Gmail is unchanged.',
        buildStatusCard_('Archive not sent', 'The backend requires a Google identity token before preservation can start.')
      );
    }
    const result = sendArchiveThreadRequest_(config, payload, idToken);
    return buildArchiveResultResponse_(result, category, markRead, archive, config, idToken);
  } catch (error) {
    return buildActionResponse_(
      'Archive request failed before Gmail changes. Gmail is unchanged.',
      buildStatusCard_('Archive not sent', 'Backend preservation could not be started from the add-on.')
    );
  }
}

function buildActionResponse_(notificationText, card) {
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(notificationText))
    .setNavigation(CardService.newNavigation().updateCard(card))
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

function readBackendConfig_() {
  const properties = PropertiesService.getScriptProperties().getProperties();
  const backendUrl = valueOrDefault_(properties[BACKEND_URL_PROPERTY], '');
  const signingSecret = valueOrDefault_(properties[BACKEND_SIGNING_SECRET_PROPERTY], '');
  return {
    backendUrl: backendUrl,
    signingSecret: signingSecret,
    configured: backendUrl !== '' && signingSecret !== ''
  };
}

function sendArchiveThreadRequest_(config, payload, idToken) {
  const options = buildSignedArchiveRequestOptions_(
    ARCHIVE_THREAD_PATH,
    payload,
    config.signingSecret,
    idToken
  );
  const response = UrlFetchApp.fetch(joinBackendUrl_(config.backendUrl, ARCHIVE_THREAD_PATH), options);
  const statusCode = response.getResponseCode();
  const text = response.getContentText() || '{}';
  return {
    statusCode: statusCode,
    body: parseJsonOrFallback_(text)
  };
}

function buildArchiveResultResponse_(result, category, markRead, archive, config, idToken) {
  const status = result.body && result.body.status ? result.body.status : 'FAILED';
  if (result.statusCode >= 200 && result.statusCode < 300 && (status === 'PRESERVED' || status === 'DUPLICATE')) {
    const record = result.body && result.body.record ? result.body.record : null;
    if (record && record.record_id) {
      try {
        const finalization = sendGmailFinalizationRequest_(
          config,
          buildGmailFinalizationRequest_(record.record_id, category, markRead, archive),
          idToken
        );
        if (finalization.statusCode >= 200 && finalization.statusCode < 300) {
          return buildActionResponse_(
            'Backend preservation returned ' + status + '. Gmail finalization instructions are pending.',
            buildStatusCard_(
              'Finalization pending',
              'Category: ' + category + '. Gmail is unchanged until the add-on mutation step is enabled.'
            )
          );
        }
      } catch (error) {
        // Preservation already completed. Finalization can be retried later
        // without implying Gmail changed or the archive failed.
      }
    }
    return buildActionResponse_(
      'Backend preservation returned ' + status + '. Gmail is unchanged.',
      buildStatusCard_('Preservation ' + status.toLowerCase(), 'Category: ' + category + '. Gmail finalization was not requested.')
    );
  }
  return buildActionResponse_(
    'Backend preservation did not complete. Gmail is unchanged.',
    buildStatusCard_('Archive not completed', 'The backend did not return a preserved or duplicate result.')
  );
}

function sendGmailFinalizationRequest_(config, payload, idToken) {
  const options = buildSignedArchiveRequestOptions_(
    GMAIL_FINALIZATION_PATH,
    payload,
    config.signingSecret,
    idToken
  );
  const response = UrlFetchApp.fetch(joinBackendUrl_(config.backendUrl, GMAIL_FINALIZATION_PATH), options);
  return {
    statusCode: response.getResponseCode(),
    body: parseJsonOrFallback_(response.getContentText() || '{}')
  };
}

function sendGmailFinalizationCallback_(config, recordId, succeeded, idToken) {
  const payload = buildGmailFinalizationCallback_(recordId, succeeded);
  const options = buildSignedArchiveRequestOptions_(
    GMAIL_FINALIZATION_CALLBACK_PATH,
    payload,
    config.signingSecret,
    idToken
  );
  const response = UrlFetchApp.fetch(joinBackendUrl_(config.backendUrl, GMAIL_FINALIZATION_CALLBACK_PATH), options);
  return {
    statusCode: response.getResponseCode(),
    body: parseJsonOrFallback_(response.getContentText() || '{}')
  };
}

function buildGmailFinalizationRequest_(recordId, category, markRead, archive) {
  return {
    record_id: recordId,
    preferences: {
      category: category,
      mark_read_after_preserve: markRead,
      archive_after_preserve: archive
    }
  };
}

function buildGmailFinalizationCallback_(recordId, succeeded) {
  return {
    record_id: recordId,
    succeeded: succeeded
  };
}

function buildArchiveThreadRequest_(event, category, markRead, archive) {
  const selected = readSelectedThreadForArchive_(event);
  const messages = selected.thread.getMessages();
  const messageSnapshots = messages.map(function(message, index) {
    return buildMessageSnapshot_(message, selected.thread, index);
  });
  const firstDate = messages[0].getDate();
  const lastDate = messages[messages.length - 1].getDate();
  return {
    request_id: 'addon-' + Utilities.getUuid(),
    client_context: {
      add_on_version: ADD_ON_VERSION,
      locale: valueOrDefault_(Session.getActiveUserLocale(), 'en-US'),
      timezone: valueOrDefault_(Session.getScriptTimeZone(), 'UTC')
    },
    preferences: {
      category: category,
      mark_read_after_preserve: markRead,
      archive_after_preserve: archive
    },
    confirmed_at: new Date().toISOString(),
    thread: {
      thread_id: selected.thread.getId(),
      gmail_thread_id: selected.thread.getId(),
      subject: valueOrDefault_(selected.thread.getFirstMessageSubject(), 'Selected Gmail thread'),
      date_range_start: firstDate.toISOString(),
      date_range_end: lastDate.toISOString(),
      messages: messageSnapshots
    }
  };
}

function readSelectedThreadForArchive_(event) {
  if (!event || !event.gmail || !event.gmail.messageId || !event.gmail.accessToken) {
    throw new Error('A selected Gmail message is required.');
  }
  GmailApp.setCurrentMessageAccessToken(event.gmail.accessToken);
  const message = GmailApp.getMessageById(event.gmail.messageId);
  return {
    message: message,
    thread: message.getThread()
  };
}

function buildMessageSnapshot_(message, thread, index) {
  const messageId = message.getId();
  return {
    message_id: messageId,
    gmail_message_id: messageId,
    sent_at: message.getDate().toISOString(),
    from: parseParticipant_(message.getFrom()),
    to: parseParticipantList_(message.getTo()),
    cc: parseParticipantList_(readMessageAddressField_(message, 'getCc')),
    bcc: parseParticipantList_(readMessageAddressField_(message, 'getBcc')),
    labels: thread.getLabels().map(function(label) { return label.getName(); }),
    is_read: !message.isUnread(),
    bodies: buildBodyRepresentations_(message),
    attachments: buildAttachmentDescriptors_(message, messageId, index)
  };
}

function readMessageAddressField_(message, methodName) {
  if (typeof message[methodName] !== 'function') {
    return '';
  }
  return message[methodName]();
}

function buildBodyRepresentations_(message) {
  const plainText = valueOrDefault_(message.getPlainBody(), '');
  const html = valueOrDefault_(message.getBody(), '');
  const bodies = [];
  if (plainText !== '') {
    bodies.push({mime_type: 'text/plain', content: plainText});
  }
  if (html !== '') {
    bodies.push({mime_type: 'text/html', content: html});
  }
  if (bodies.length === 0) {
    bodies.push({mime_type: 'text/plain', content: ''});
  }
  return bodies;
}

function buildAttachmentDescriptors_(message, messageId, messageIndex) {
  return message.getAttachments({includeInlineImages: false, includeAttachments: true}).map(function(attachment, index) {
    const bytes = attachment.getBytes();
    return {
      attachment_id: messageId + '-attachment-' + String(messageIndex) + '-' + String(index),
      original_filename: valueOrDefault_(attachment.getName(), 'attachment'),
      mime_type: valueOrDefault_(attachment.getContentType(), 'application/octet-stream'),
      size_bytes: bytes.length,
      content_sha256: bytesToHex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes)),
      trusted_content_base64: Utilities.base64Encode(bytes)
    };
  });
}

function parseParticipantList_(value) {
  if (!value) {
    return [];
  }
  return String(value).split(',').map(function(item) {
    return parseParticipant_(item);
  }).filter(function(participant) {
    return participant.email.indexOf('@') !== -1;
  });
}

function parseParticipant_(value) {
  const text = valueOrDefault_(value, 'unknown@example.com');
  const match = text.match(/^(.*)<([^>]+)>$/);
  if (match) {
    return {
      email: match[2].trim(),
      display_name: valueOrDefault_(match[1].replace(/^"|"$/g, ''), null)
    };
  }
  const emailMatch = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return {
    email: emailMatch ? emailMatch[0] : 'unknown@example.com',
    display_name: emailMatch && text !== emailMatch[0] ? text.replace(emailMatch[0], '').trim() : null
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

function buildSignedArchiveRequestOptions_(path, payload, signingSecret, idToken, timestamp) {
  const body = JSON.stringify(payload);
  const requestedAt = timestamp || String(Math.floor(Date.now() / 1000));
  const signature = signBackendRequest_('POST', path, requestedAt, body, signingSecret);
  return {
    method: 'post',
    contentType: 'application/json',
    payload: body,
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + idToken,
      [BACKEND_TIMESTAMP_HEADER]: requestedAt,
      [BACKEND_SIGNATURE_HEADER]: signature
    }
  };
}

function joinBackendUrl_(backendUrl, path) {
  return backendUrl.replace(/\/+$/, '') + path;
}

function parseJsonOrFallback_(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return {};
  }
}

function signBackendRequest_(method, path, timestamp, body, signingSecret) {
  if (!signingSecret) {
    throw new Error('Backend signing secret is required.');
  }
  const bodyHash = bytesToHex_(Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    body,
    Utilities.Charset.UTF_8
  ));
  const canonical = [
    BACKEND_SIGNATURE_VERSION,
    method.toUpperCase(),
    path,
    timestamp,
    bodyHash
  ].join('\n');
  return bytesToHex_(Utilities.computeHmacSha256Signature(
    canonical,
    signingSecret,
    Utilities.Charset.UTF_8
  ));
}

function bytesToHex_(bytes) {
  return bytes.map(function(byteValue) {
    const unsigned = byteValue < 0 ? byteValue + 256 : byteValue;
    return ('0' + unsigned.toString(16)).slice(-2);
  }).join('');
}
