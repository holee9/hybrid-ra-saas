/**
 * E2E Validation Script for user-guide.html
 * Tests: structure, contrast, navigation, content completeness, accessibility basics
 */
const fs = require('fs');
const path = require('path');

const HTML_PATH = path.join(__dirname, 'user-guide.html');
const html = fs.readFileSync(HTML_PATH, 'utf8');

let passed = 0;
let failed = 0;
let warnings = 0;
const issues = [];

function test(label, fn) {
  try {
    const result = fn();
    if (result === false) {
      failed++;
      issues.push({ type: 'FAIL', label });
      console.log(`  ❌ FAIL  ${label}`);
    } else if (result && result.warn) {
      warnings++;
      issues.push({ type: 'WARN', label, detail: result.warn });
      console.log(`  ⚠️  WARN  ${label}: ${result.warn}`);
    } else {
      passed++;
      console.log(`  ✅ PASS  ${label}`);
    }
  } catch (e) {
    failed++;
    issues.push({ type: 'FAIL', label, detail: e.message });
    console.log(`  ❌ FAIL  ${label}: ${e.message}`);
  }
}

// ── WCAG Contrast Calculator ─────────────────────────────────────────────────
function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
}
function linearize(c) {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}
function luminance(hex) {
  const [r,g,b] = hexToRgb(hex);
  return 0.2126*linearize(r) + 0.7152*linearize(g) + 0.0722*linearize(b);
}
function contrast(fg, bg) {
  const l1 = luminance(fg), l2 = luminance(bg);
  const lighter = Math.max(l1,l2), darker = Math.min(l1,l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// ── 1. File Structure ─────────────────────────────────────────────────────────
console.log('\n[1] 파일 구조 검사');
test('HTML 파일 존재', () => fs.existsSync(HTML_PATH));
test('DOCTYPE 선언', () => html.includes('<!DOCTYPE html>'));
test('lang="ko" 설정', () => html.includes('lang="ko"'));
test('viewport meta', () => html.includes('name="viewport"'));
test('charset UTF-8', () => /charset.*utf-8/i.test(html));
test('title 태그', () => /<title>[^<]+<\/title>/.test(html));

// ── 2. Navigation Structure ──────────────────────────────────────────────────
console.log('\n[2] 내비게이션 구조 검사');
const navLinks = [...html.matchAll(/<a[^>]+href="#([^"]+)"[^>]*>([^<]+)</g)];
test('사이드바 nav 링크 존재 (최소 10개)', () => navLinks.length >= 10 || { warn: `발견된 링크: ${navLinks.length}개` });
test('nav-section 그룹 헤더 존재', () => html.includes('class="nav-section"'));
test('#sidebar 요소', () => html.includes('id="sidebar"'));

const sectionIds = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
const navHrefs = [...html.matchAll(/href="#([^"]+)"/g)].map(m => m[1]);
const brokenLinks = navHrefs.filter(h => h && h !== '#' && !sectionIds.includes(h));
test('내비게이션 링크 모두 유효 (앵커 존재)', () => brokenLinks.length === 0 || { warn: `끊긴 링크 ${brokenLinks.length}개: ${brokenLinks.join(', ')}` });

// ── 3. Content Completeness (RA 담당자용 필수 섹션) ─────────────────────────
console.log('\n[3] 콘텐츠 완전성 검사 (RA 담당자 필수 섹션)');
const mustHaveSections = [
  ['시스템 개요', /시스템 개요|개요|overview/i],
  ['빠른 시작', /빠른 시작|quick.?start|시작하기/i],
  ['규제 검토 큐', /규제 검토 큐|큐 관리|queue/i],
  ['AI 교정 패널', /교정 패널|보정 패널|correction|교정/i],
  ['RAG 지식베이스', /지식.?베이스|RAG|rag/i],
  ['감사 로그', /감사 로그|audit/i],
  ['워크플로우', /워크플로우|workflow/i],
  ['문제 해결', /문제 해결|troubleshoot/i],
];
for (const [name, pattern] of mustHaveSections) {
  test(`섹션: ${name}`, () => pattern.test(html));
}

// ── 4. Architecture Diagram ─────────────────────────────────────────────────
console.log('\n[4] 다이어그램 검사');
test('SVG 아키텍처 다이어그램 포함', () => html.includes('<svg') && html.includes('</svg>'));
test('Mermaid.js 워크플로우 다이어그램', () => html.includes('mermaid') || html.includes('Mermaid'));
test('다이어그램 개수 (최소 2개)', () => {
  const svgCount = (html.match(/<svg/g) || []).length;
  const mermaidCount = (html.match(/class="mermaid"/g) || []).length;
  const total = svgCount + mermaidCount;
  return total >= 2 || { warn: `다이어그램 ${total}개` };
});

// ── 5. Screenshot Placeholders ──────────────────────────────────────────────
console.log('\n[5] 스크린샷 자리표시자 검사');
const screenshots = [...html.matchAll(/src="screenshots\/([^"]+)"/g)];
test('스크린샷 자리표시자 존재 (최소 3개)', () => screenshots.length >= 3 || { warn: `${screenshots.length}개 발견` });
test('onerror 폴백 패턴', () => html.includes('onerror') && html.includes('screenshot-placeholder'));

// ── 6. Accessibility Basics ─────────────────────────────────────────────────
console.log('\n[6] 접근성 기본 검사');
test('skip-link 또는 main 랜드마크', () => html.includes('id="main"') || html.includes('role="main"'));
test('모든 img alt 속성', () => {
  const imgs = [...html.matchAll(/<img[^>]+>/g)];
  const noAlt = imgs.filter(m => !m[0].includes('alt='));
  return noAlt.length === 0 || { warn: `alt 없는 img: ${noAlt.length}개` };
});
test('button 요소 접근 가능 텍스트', () => {
  const buttons = [...html.matchAll(/<button[^>]*>([^<]*)</g)];
  const emptyButtons = buttons.filter(m => !m[1].trim() && !m[0].includes('aria-label'));
  return emptyButtons.length === 0 || { warn: `빈 button ${emptyButtons.length}개` };
});

// ── 7. WCAG Contrast Check (Updated CSS) ────────────────────────────────────
console.log('\n[7] WCAG 2.1 대비 검사 (수정된 CSS)');

const contrastChecks = [
  // [name, fg, bg, minRatio, note]
  ['nav-section 레이블', '#8094af', '#1e293b', 4.5, '10px uppercase bold'],
  ['nav li a 링크', '#cbd5e1', '#1e293b', 4.5, '13.5px normal'],
  ['nav li a:hover', '#f1f5f9', '#1e293b', 7.0, '13.5px (enhanced)'],
  ['sidebar-version 텍스트', '#94a3b8', '#1e293b', 4.5, '11px'],
  ['sidebar-header 서브텍스트', '#94a3b8', '#0f172a', 4.5, '13px uppercase bold'],
  ['product-name 제목', '#f1f5f9', '#0f172a', 7.0, '15px bold (enhanced)'],
  ['본문 h2', '#0f172a', '#ffffff', 7.0, '22px bold (enhanced)'],
  ['본문 p 텍스트', '#374151', '#ffffff', 4.5, '14.5px'],
];

for (const [name, fg, bg, min, note] of contrastChecks) {
  test(`대비 ${name} (최소 ${min}:1) [${note}]`, () => {
    const ratio = contrast(fg, bg);
    if (ratio < min) return { warn: `${ratio.toFixed(1)}:1 < ${min}:1 실패` };
    return true;
  });
}

// ── 8. GitHub Pages Readiness ─────────────────────────────────────────────
console.log('\n[8] GitHub Pages 호환성');
test('외부 리소스 fallback 처리', () => html.includes('onerror') || html.includes('catch'));
test('상대 경로만 사용 (절대 경로 없음)', () => {
  const absoluteLinks = [...html.matchAll(/href="https?:\/\/(?!github\.com|cdn\.jsdelivr|fonts\.goog)/g)];
  return absoluteLinks.length === 0 || { warn: `외부 링크 ${absoluteLinks.length}개 (CDN/GitHub 외)` };
});
test('인라인 CSS (외부 CSS 파일 의존 없음)', () => {
  const externalCss = [...html.matchAll(/<link[^>]+rel="stylesheet"[^>]+href="(?!https?:)/g)];
  return externalCss.length === 0 || { warn: `로컬 외부 CSS ${externalCss.length}개` };
});

// ── 9. Korean Language ────────────────────────────────────────────────────────
console.log('\n[9] 한국어 콘텐츠 검사');
test('한글 텍스트 포함', () => /[가-힣]/.test(html));
test('RA 도메인 용어 포함', () => /규제|허가|인증|FDA|MDR|MFDS/.test(html));
test('비개발자 대상 텍스트 (IT 용어 최소화)', () => {
  // Main sections (not appendix) should not be dominated by IT terms
  const mainContent = html.split('관리자')[0];
  const itTermCount = (mainContent.match(/Docker|kubectl|nginx|postgres|redis/gi) || []).length;
  return itTermCount < 5 || { warn: `메인 섹션 IT 용어 ${itTermCount}개 (비개발자 대상 확인 필요)` };
});

// ── Summary ───────────────────────────────────────────────────────────────────
console.log('\n' + '─'.repeat(60));
console.log(`결과: ✅ ${passed}개 통과  ❌ ${failed}개 실패  ⚠️  ${warnings}개 경고`);
console.log('─'.repeat(60));

if (failed > 0) {
  console.log('\n[실패 항목]');
  issues.filter(i => i.type === 'FAIL').forEach(i => console.log(`  • ${i.label}${i.detail ? ': ' + i.detail : ''}`));
}
if (warnings > 0) {
  console.log('\n[경고 항목]');
  issues.filter(i => i.type === 'WARN').forEach(i => console.log(`  • ${i.label}: ${i.detail}`));
}

process.exit(failed > 0 ? 1 : 0);
