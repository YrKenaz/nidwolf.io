/**
 * Nidwolf Cookie Consent Banner
 * - KR/EN 자동 감지 (localStorage: nw-lang)
 * - 다크모드 자동 감지 (html[data-dark])
 * - 동의 여부 저장 (localStorage: nw-cookie-consent = 'accepted' | 'declined')
 */
(function () {
  var KEY = 'nw-cookie-consent';
  if (localStorage.getItem(KEY)) return; // 이미 선택됨 → 표시 안 함

  var isEn = (localStorage.getItem('nw-lang') || 'ko') === 'en';
  var isDark = document.documentElement.hasAttribute('data-dark');

  /* ── 텍스트 ── */
  var T = {
    msg: isEn
      ? 'We use cookies for advertising (Google AdSense) and analytics to improve your experience. See our <a href="/privacy.html">Privacy Policy</a>.'
      : '이 사이트는 광고 제공(Google AdSense) 및 이용 통계 분석을 위해 쿠키를 사용합니다. 자세한 내용은 <a href="/privacy.html">개인정보처리방침</a>을 확인하세요.',
    accept: isEn ? 'Accept All' : '전체 동의',
    decline: isEn ? 'Decline' : '거부',
  };

  /* ── 스타일 ── */
  var css = [
    '#nw-cc{position:fixed;bottom:0;left:0;right:0;z-index:99999;',
    'padding:14px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;',
    'font-family:inherit;font-size:13.5px;line-height:1.5;',
    isDark
      ? 'background:#1a1d2e;color:#c8cce8;border-top:1px solid #2e3254;'
      : 'background:#fff;color:#333;border-top:1px solid #dde1f0;',
    'box-shadow:0 -2px 12px rgba(0,0,0,.12);}',

    '#nw-cc a{color:#7C6CF5;text-decoration:underline;}',

    '#nw-cc-msg{flex:1;min-width:200px;}',

    '#nw-cc-btns{display:flex;gap:8px;flex-shrink:0;}',

    '#nw-cc-accept{',
    'background:#7C6CF5;color:#fff;border:none;border-radius:6px;',
    'padding:7px 16px;font-size:13px;cursor:pointer;font-weight:600;}',
    '#nw-cc-accept:hover{background:#6355e0;}',

    '#nw-cc-decline{',
    isDark
      ? 'background:#2a2e4a;color:#9094b8;'
      : 'background:#f0f1f8;color:#555;',
    'border:none;border-radius:6px;',
    'padding:7px 14px;font-size:13px;cursor:pointer;}',
    '#nw-cc-decline:hover{opacity:.8}',
  ].join('');

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  /* ── DOM ── */
  var bar = document.createElement('div');
  bar.id = 'nw-cc';
  bar.innerHTML = [
    '<span id="nw-cc-msg">', T.msg, '</span>',
    '<div id="nw-cc-btns">',
    '<button id="nw-cc-accept">', T.accept, '</button>',
    '<button id="nw-cc-decline">', T.decline, '</button>',
    '</div>',
  ].join('');
  document.body.appendChild(bar);

  /* ── 이벤트 ── */
  function dismiss(val) {
    localStorage.setItem(KEY, val);
    bar.style.transition = 'opacity .3s';
    bar.style.opacity = '0';
    setTimeout(function () { bar.remove(); }, 300);
  }

  document.getElementById('nw-cc-accept').addEventListener('click', function () {
    dismiss('accepted');
  });
  document.getElementById('nw-cc-decline').addEventListener('click', function () {
    dismiss('declined');
  });
})();
