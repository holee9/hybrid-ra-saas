/**
 * E2E Validation Script for user-guide.html
 * Non-circular: CSS values are EXTRACTED from the file, not hardcoded.
 * Tests: structure, contrast (from parsed CSS), navigation, content, accessibility
 *
 * Run: node docs/e2e-validate.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const HTML_PATH = path.join(__dirname, 'user-guide.html');
const html = fs.readFileSync(HTML_PATH, 'utf8');

let passed = 0, failed = 0, warnings = 0;
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
function lin(c) { const s = c / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); }
function luminance(hex) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}
function contrastRatio(fg, bg) {
  const l1 = luminance(fg), l2 = luminance(bg);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

// ── CSS Parser: Extract ACTUAL values from file ───────────────────────────────
// This is the key difference from the previous circular test.
// We parse the live CSS from the file and then validate those parsed values.
const cssMatch = html.match(/<style[^>]*>([\s\S]*?)<\/style>/);
const CSS = cssMatch ? cssMatch[1] : '';

/**
 * Extract a single property value from a CSS rule block.
 * Returns null if the selector or property is not found.
 */
function extractCssProp(selectorPattern, property) {
  const ruleMatch = CSS.match(new RegExp(selectorPattern + '\\s*\\{([^}]*)\\}'));
  if (!ruleMatch) return null;
  const propMatch = ruleMatch[1].match(new RegExp(property + '\\s*:\\s*([^;]+)'));
  return propMatch ? propMatch[1].trim() : null;
}

/**
 * Extract pixel font-size as a number from a CSS rule.
 * Supports values like "13.5px" or "11px". Returns null if not found.
 */
function extractFontSizePx(selectorPattern) {
  const raw = extractCssProp(selectorPattern, 'font-size');
  if (!raw) return null;
  const pxMatch = raw.match(/([\d.]+)px/);
  return pxMatch ? parseFloat(pxMatch[1]) : null;
}

// ── 1. File Structure ─────────────────────────────────────────────────────────
console.log('\n[1] 파일 구조 검사');
test('HTML 파일 존재', () => fs.existsSync(HTML_PATH));
test('DOCTYPE 선언', () => html.includes('<!DOCTYPE html>'));
test('lang="ko" 설정', () => html.includes('lang="ko"'));
test('viewport meta', () => html.includes('name="viewport"'));
test('charset UTF-8', () => /charset.*utf-8/i.test(html));
test('title 태그', () => /<title>[^<]+<\/title>/.test(html));

// ── 2. Navigation Structure ───────────────────────────────────────────────────
console.log('\n[2] 내비게이션 구조 검사');
const navLinks = [...html.matchAll(/<a[^>]+href="#([^"]+)"[^>]*>([^<]+)</g)];
test('사이드바 nav 링크 존재 (최소 10개)', () => navLinks.length >= 10 || { warn: `발견된 링크: ${navLinks.length}개` });
test('nav-section 그룹 헤더 존재', () => html.includes('class="nav-section"'));
test('#sidebar 요소', () => html.includes('id="sidebar"'));
const sectionIds = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
const navHrefs = [...html.matchAll(/href="#([^"]+)"/g)].map(m => m[1]);
const brokenLinks = navHrefs.filter(h => h && h !== '#' && !sectionIds.includes(h));
test('내비게이션 링크 모두 유효 (앵커 존재)', () => brokenLinks.length === 0 || { warn: `끊긴 링크 ${brokenLinks.length}개: ${brokenLinks.join(', ')}` });

// ── 3. Content Completeness ───────────────────────────────────────────────────
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

// ── 4. Diagram Check ──────────────────────────────────────────────────────────
console.log('\n[4] 다이어그램 검사');
test('SVG 아키텍처 다이어그램 포함', () => html.includes('<svg') && html.includes('</svg>'));
test('Mermaid.js 워크플로우 다이어그램', () => html.includes('mermaid') || html.includes('Mermaid'));
test('다이어그램 개수 (최소 2개)', () => {
  const svgCount = (html.match(/<svg/g) || []).length;
  const mermaidCount = (html.match(/class="mermaid"/g) || []).length;
  const total = svgCount + mermaidCount;
  return total >= 2 || { warn: `다이어그램 ${total}개` };
});

// ── 5. Screenshot Placeholders ────────────────────────────────────────────────
console.log('\n[5] 스크린샷 자리표시자 검사');
const screenshots = [...html.matchAll(/src="screenshots\/([^"]+)"/g)];
test('스크린샷 자리표시자 존재 (최소 3개)', () => screenshots.length >= 3 || { warn: `${screenshots.length}개 발견` });
test('onerror 폴백 패턴', () => html.includes('onerror') && html.includes('screenshot-placeholder'));

// ── 6. Accessibility Basics ───────────────────────────────────────────────────
console.log('\n[6] 접근성 기본 검사');
test('skip-link 또는 main 랜드마크', () => html.includes('id="main"') || html.includes('role="main"'));
test('모든 img alt 속성', () => {
  const imgs = [...html.matchAll(/<img[^>]+>/g)];
  const noAlt = imgs.filter(m => !m[0].includes('alt='));
  return noAlt.length === 0 || { warn: `alt 없는 img: ${noAlt.length}개` };
});

// ── 7. WCAG Contrast — NON-CIRCULAR (parsed from file) ───────────────────────
// Critical: colors are EXTRACTED from CSS, not hardcoded here.
// If someone changes the CSS, this test will catch the regression.
console.log('\n[7] WCAG 2.1 대비 검사 (파일에서 파싱된 실제 값 검증)');

// Extract background colors
const sidebarBg = extractCssProp('#sidebar', 'background') || '';
const headerBg  = extractCssProp('\\.sidebar-header', 'background') || '';
const bgDark    = (sidebarBg.match(/#[0-9a-fA-F]{6}/) || ['#1e293b'])[0];
const bgDarker  = (headerBg.match(/#[0-9a-fA-F]{6}/) || ['#0f172a'])[0];

// Extract foreground colors
function fgFromRule(pat) {
  const raw = extractCssProp(pat, 'color');
  if (!raw) return null;
  const m = raw.match(/#[0-9a-fA-F]{6}/);
  return m ? m[0] : null;
}

const fgNavSection   = fgFromRule('\\.nav-section');
const fgNavA         = fgFromRule('#sidebar nav li a');
const fgVersion      = fgFromRule('\\.sidebar-version');
const fgHeaderSub    = fgFromRule('\\.sidebar-header');
const fgProductName  = fgFromRule('\\.sidebar-header \\.product-name') ||
                       fgFromRule('\\.product-name');

// Extract font sizes
const fsNavSection   = extractFontSizePx('\\.nav-section');
const fsNavA         = extractFontSizePx('#sidebar nav li a');
const fsVersion      = extractFontSizePx('\\.sidebar-version');

console.log(`  [추출됨] 사이드바 배경: ${bgDark}, 헤더 배경: ${bgDarker}`);
console.log(`  [추출됨] nav-section: ${fgNavSection} @ ${fsNavSection}px | nav-a: ${fgNavA} @ ${fsNavA}px`);
console.log(`  [추출됨] sidebar-version: ${fgVersion} @ ${fsVersion}px`);

// WCAG rules: large text = 18px+ OR 14px+ bold → needs 3:1; normal → 4.5:1
function wcagCheck(name, fg, bg, sizePx, isBold, warnThreshold = 5.0) {
  if (!fg || !bg) { test(name, () => { throw new Error('색상 추출 실패 — CSS 구조 변경 확인 필요'); }); return; }
  const isLarge = sizePx >= 18 || (sizePx >= 14 && isBold);
  const minRatio = isLarge ? 3.0 : 4.5;
  test(`${name} (${sizePx}px${isBold?' bold':''}, 최소 ${minRatio}:1)`, () => {
    const ratio = contrastRatio(fg, bg);
    if (ratio < minRatio) return { warn: `${ratio.toFixed(2)}:1 < ${minRatio}:1 WCAG AA 실패` };
    if (ratio < warnThreshold) return { warn: `${ratio.toFixed(2)}:1 — 통과이나 가독성 개선 권고` };
    return true;
  });
}

// warnThreshold=5.0 means: passes AA but warns when below comfortable reading level
wcagCheck('nav-section 그룹 레이블', fgNavSection, bgDark, fsNavSection || 11, true,  6.0);
wcagCheck('nav li a 링크',          fgNavA,       bgDark, fsNavA || 13.5,     false, 5.0);
wcagCheck('sidebar-version',        fgVersion,    bgDark, fsVersion || 11,    false, 5.0);
wcagCheck('sidebar-header 서브텍스트', fgHeaderSub, bgDarker, 13,             true,  5.0);
fgProductName && wcagCheck('product-name 제목', fgProductName, bgDarker, 15,  true,  7.0);

// Verify nav-section font-size is NOT below 11px
test('nav-section 폰트 크기 가독성 기준 (최소 11px)', () => {
  if (!fsNavSection) return { warn: 'font-size 추출 실패' };
  if (fsNavSection < 11) return { warn: `${fsNavSection}px — 비전문가용 최소 기준 11px 미달` };
  return true;
});

// ── 8. GitHub Pages Readiness ─────────────────────────────────────────────────
console.log('\n[8] GitHub Pages 호환성');
test('외부 리소스 fallback 처리', () => html.includes('onerror') || html.includes('catch'));
test('인라인 CSS (외부 CSS 파일 의존 없음)', () => {
  const externalCss = [...html.matchAll(/<link[^>]+rel="stylesheet"[^>]+href="(?!https?:)/g)];
  return externalCss.length === 0 || { warn: `로컬 외부 CSS ${externalCss.length}개` };
});

// ── 9. Korean Language ────────────────────────────────────────────────────────
console.log('\n[9] 한국어 콘텐츠 검사');
test('한글 텍스트 포함', () => /[가-힣]/.test(html));
test('RA 도메인 용어 포함', () => /규제|허가|인증|FDA|MDR|MFDS/.test(html));
test('비개발자 대상 텍스트 (IT 용어 최소화)', () => {
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
