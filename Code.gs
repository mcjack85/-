// =====================================================
// 인카다이렉트 위너스지사 - 상담 신청 백엔드
// Google Apps Script Web App
// =====================================================

// ⚙️ 설정값 - 여기만 수정하세요
const SHEET_ID = 'YOUR_GOOGLE_SHEET_ID_HERE';  // Google Sheets URL의 /d/XXXXX/edit 에서 XXXXX 부분
const SHEET_NAME = '상담신청';
const ADMIN_PASSWORD = 'winners2026!';           // 관리자 페이지 비밀번호 (반드시 변경하세요)

// =====================================================
// POST: 폼 제출 처리
// =====================================================
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    const ss = SpreadsheetApp.openById(SHEET_ID);
    let sheet = ss.getSheetByName(SHEET_NAME);

    // 시트 없으면 생성 + 헤더 설정
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      const headers = ['접수시간', '이름', '연락처', '거주지역', '경력', '희망시간', '유입경로'];
      sheet.appendRow(headers);
      sheet.getRange(1, 1, 1, headers.length)
        .setFontWeight('bold')
        .setBackground('#1a1a2e')
        .setFontColor('#ffffff');
      sheet.setFrozenRows(1);
    }

    // 한국 시간(KST) 타임스탬프
    const now = new Date();
    const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
    const timestamp = Utilities.formatDate(kst, 'GMT', 'yyyy-MM-dd HH:mm:ss');

    sheet.appendRow([
      timestamp,
      data.name    || '',
      data.phone   || '',
      data.region  || '',
      data.career  || '',
      data.time    || '미선택',
      data.utm     || '직접접속'
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// =====================================================
// GET: 관리자 데이터 조회
// =====================================================
function doGet(e) {
  const password = e.parameter.password;

  // 비밀번호 검증
  if (password !== ADMIN_PASSWORD) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'unauthorized' }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  try {
    const ss = SpreadsheetApp.openById(SHEET_ID);
    const sheet = ss.getSheetByName(SHEET_NAME);

    if (!sheet || sheet.getLastRow() <= 1) {
      return ContentService
        .createTextOutput(JSON.stringify({ status: 'success', data: [], total: 0 }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const rows = sheet.getDataRange().getValues();
    const headers = rows[0]; // 첫 행 = 헤더

    // 데이터 행만 추출 (최신순 정렬)
    const data = rows.slice(1).reverse().map(row => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = row[i] !== undefined ? row[i] : ''; });
      return obj;
    });

    // 오늘 접수 수 계산
    const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    const todayCount = data.filter(r => String(r['접수시간']).startsWith(today)).length;

    return ContentService
      .createTextOutput(JSON.stringify({
        status: 'success',
        data: data,
        total: data.length,
        today: todayCount
      }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
