/**
 * Boya Shop — Google Sheets order webhook
 *
 * SETUP
 * 1. Open your Google Sheet (headers optional — added automatically on first order)
 * 2. Extensions → Apps Script → paste this file → Save
 * 3. Deploy → New deployment → Type: Web app
 *      Execute as: Me
 *      Who has access: Anyone
 * 4. Copy the Web app URL into backend .env:
 *      GOOGLE_SHEETS_WEBHOOK_URL=<paste deployment URL here>
 */

const SHEET_NAME = ''; // leave empty for active tab, or e.g. 'Orders'

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse({ ok: false, error: 'Missing POST body' }, 400);
    }

    const data = JSON.parse(e.postData.contents);
    const sheet = getTargetSheet_();
    ensureHeaders_(sheet);

    sheet.appendRow([
      data.date || '',
      data.orderid || '',
      data.nom || '',
      data['téléphone'] || data.telephone || '',
      data.adress || data.address || '',
      data.produit || '',
      data.sku || '',
      data['QTé'] || data.qte || '',
      data['prix total'] || data.total || '',
    ]);

    return jsonResponse({ ok: true });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err) }, 500);
  }
}

function doGet() {
  return ContentService.createTextOutput('Boya Shop webhook is running. Use POST to append orders.');
}

function getTargetSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (SHEET_NAME) {
    const named = ss.getSheetByName(SHEET_NAME);
    if (!named) {
      throw new Error('Sheet not found: ' + SHEET_NAME);
    }
    return named;
  }
  return ss.getActiveSheet();
}

function ensureHeaders_(sheet) {
  if (sheet.getLastRow() > 0) return;

  sheet.appendRow([
    'date',
    'orderid',
    'nom',
    'téléphone',
    'adress',
    'produit',
    'sku',
    'QTé',
    'prix total',
  ]);
}

function jsonResponse(payload, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(
    ContentService.MimeType.JSON
  );

  if (statusCode && typeof output.setStatusCode === 'function') {
    output.setStatusCode(statusCode);
  }

  return output;
}
