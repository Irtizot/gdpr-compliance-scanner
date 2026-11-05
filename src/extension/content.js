(() => {
  if (window.__consentSignalsLoaded) return;
  window.__consentSignalsLoaded = true;

  const IS_TOP = window === window.top;
  const SETTLE_MS = 4000;
  const BANNER_WAIT_EXTRA_MS = 14000;
  const BANNER_POLL_MS = 2000;
  const MIN_BANNER_AREA_PX = 4000;
  const MAX_BANNER_TEXT_CHARS = 6000;
  const BANNER_KEYWORDS = ["cookie", "consent", "privacy"];

  const BANNER_SELECTORS = [
    "#onetrust-banner-sdk", "#CybotCookiebotDialog", "#didomi-popup", "#didomi-host",
    ".qc-cmp2-container", "#truste-consent-track", "#cookiescript_injected",
    "[id*='cookie' i]", "[class*='cookie' i]",
    "[id*='consent' i]", "[class*='consent' i]",
    "[aria-label*='cookie' i]", "[aria-label*='consent' i]",
    "[role='dialog']", "[aria-modal='true']"
  ];

  const REJECT_RE = /\b(reject|decline|deny|refuse|disagree|no,? thanks|do not (consent|accept|agree)|don['’]?t (consent|accept|agree|enable|allow)|do not (enable|allow)|necessary only|only necessary|essential only|only essential|continue without (accepting|agreeing))\b/i;
  const SETTINGS_RE = /\b(manage|settings|preferences|customi[sz]e|options|more info|more options|choose|personali[sz]e)\b/i;
  const ACCEPT_RE = /\b(accept|agree|allow|enable|ok|okay|got it|i understand|yes,? i['’]?m happy|consent)\b/i;

  const MAX_LEVELS_UP = 4;
  const WIDEN_MAX_TEXT = 5000;
  const SIZE_RATIO = 1.5;
  const CONTRAST_DIFF = 2.0;
  const FILLED_DISTANCE = 40;

  const LEXICON_SRC = {
    confirmshaming: [
      /no,? i (don['’]?t|do not) (want|like|care)/i, /i (prefer|choose) to (pay|miss|lose)/i,
      /no thanks,? i('| wi)ll (pay|miss)/i, /i('| a)m not interested in (saving|privacy|deals)/i,
      /i (hate|don['’]?t like) (saving|deals|discounts)/i
    ],
    implied_consent: [
      /by (continuing|using|browsing|closing|scrolling|dismissing)[^.]{0,80}?(you )?(agree|consent|accept)/i,
      /if you continue (to )?(use|browse)/i, /continued use of (this|our) (site|website)/i,
      /(closing|dismissing) this (banner|message|notice)[^.]{0,40}(agree|accept|consent)/i
    ],
    vague_purpose: [
      /(improve|enhance|enrich|optimi[sz]e) (your|the) (browsing )?experience/i,
      /(better|improved|enhanced) (browsing )?experience/i,
      /(various|certain|other) purposes(?!,? (including|such as|namely))/i,
      /(personali[sz]e|tailor)(ed)? your (browsing )?experience/i
    ],
    pressure: [
      /you must (accept|agree|consent)/i, /don['’]?t miss out/i, /limited time/i,
      /last chance/i, /act now/i, /required to (continue|proceed|access)/i
    ]
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => String(s || "").replace(/\s+/g, " ").trim();

  function shadowRoots() {
    const roots = [];
    const walk = (root) => {
      for (const e of root.querySelectorAll("*")) {
        if (e.shadowRoot) { roots.push(e.shadowRoot); walk(e.shadowRoot); }
      }
    };
    walk(document);
    return roots;
  }

  function deepAll(selector, scope, roots) {
    const out = [];
    const base = scope || document;
    try { out.push(...base.querySelectorAll(selector)); } catch (e) { return out; }
    if (!scope) {
      for (const r of roots || shadowRoots()) {
        try { out.push(...r.querySelectorAll(selector)); } catch (e) { /* skip */ }
      }
    } else {
      const walk = (root) => {
        for (const e of root.querySelectorAll("*")) {
          if (e.shadowRoot) {
            try { out.push(...e.shadowRoot.querySelectorAll(selector)); } catch (x) { /* skip */ }
            walk(e.shadowRoot);
          }
        }
      };
      walk(scope);
      if (scope.shadowRoot) {
        try { out.push(...scope.shadowRoot.querySelectorAll(selector)); } catch (x) { /* skip */ }
        walk(scope.shadowRoot);
      }
    }
    return out;
  }

  function isVisible(e) {
    try {
      const r = e.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0)) return false;
      return getComputedStyle(e).visibility !== "hidden";
    } catch (x) { return false; }
  }

  function parentOf(n) {
    return n.parentElement || (n.getRootNode() instanceof ShadowRoot ? n.getRootNode().host : null);
  }

  function findBySelectors() {
    const roots = shadowRoots();
    for (const selector of BANNER_SELECTORS) {
      const matches = deepAll(selector, null, roots).slice(0, 8);
      for (const el of matches) {
        try {
          if (!isVisible(el)) continue;
          if (el.tagName === "BODY" || el.tagName === "HTML") continue;
          const r = el.getBoundingClientRect();
          if (r.width * r.height < MIN_BANNER_AREA_PX) continue;
          const text = (el.innerText || "").toLowerCase();
          if (text.length > MAX_BANNER_TEXT_CHARS) continue;
          if (!BANNER_KEYWORDS.some((w) => text.includes(w))) continue;
          return { element: el, selector, text, stage: "selector" };
        } catch (e) { /* next */ }
      }
    }
    return null;
  }

  function findIframeBody() {
    if (IS_TOP) return null;
    try {
      if (window.innerWidth * window.innerHeight < MIN_BANNER_AREA_PX) return null;
      const body = document.body;
      if (!body) return null;
      const text = (body.innerText || "").toLowerCase();
      if (text.length > MAX_BANNER_TEXT_CHARS) return null;
      if (!BANNER_KEYWORDS.some((w) => text.includes(w))) return null;
      return { element: body, selector: "iframe:" + (location.hostname || "unknown"), text, stage: "iframe" };
    } catch (e) { return null; }
  }

  function findByText() {
    if (!IS_TOP) return null;
    const WANT = /cookie|consent/i;
    const GOOD = /\b(accept|agree|allow|enable|got it|i understand|ok|okay|reject|decline|deny|refuse|essential only|necessary only)\b/i;
    const BAD = /policy|preferences|settings|manage|notice|learn more|more info/i;
    const MAX_TEXT = 2000, MIN_AREA = 4000, MAX_UP = 10;
    const all = [];
    const collect = (root) => {
      for (const e of root.querySelectorAll("*")) { all.push(e); if (e.shadowRoot) collect(e.shadowRoot); }
    };
    collect(document);
    const shown = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const clickable = (e) => e.matches('button, a, [role="button"], input[type="button"], input[type="submit"], [onclick]')
      || getComputedStyle(e).cursor === "pointer";
    let best = null, bestArea = Infinity;
    for (const b of all) {
      if (!clickable(b) || !shown(b)) continue;
      if (b.closest('footer, [role="contentinfo"]')) continue;
      const label = ((b.innerText || b.value || b.getAttribute("aria-label") || "") + "").replace(/\s+/g, " ").trim();
      if (!label || label.length > 30 || !GOOD.test(label) || BAD.test(label)) continue;
      let c = parentOf(b);
      for (let i = 0; c && i < MAX_UP; i++, c = parentOf(c)) {
        if (c === document.body || c === document.documentElement) break;
        const t = (c.innerText || "").trim();
        if (t.length > MAX_TEXT) break;
        if (t.length >= 40 && WANT.test(t) && shown(c)) {
          const r = c.getBoundingClientRect();
          const area = r.width * r.height;
          if (area >= MIN_AREA && area < bestArea) { best = c; bestArea = area; }
          break;
        }
      }
    }
    if (!best) return null;
    return { element: best, selector: "text-fallback", text: (best.innerText || "").toLowerCase(), stage: "text" };
  }

  function readLabel(el) {
    const label = (el.innerText || el.getAttribute("value") || el.getAttribute("aria-label") || "").trim();
    return label.replace(/\s+/g, " ");
  }

  function collectButtons(candidates, cap, found, onlyMissing) {
    const list = candidates.slice(0, cap);
    for (const el of list) {
      try {
        if (!isVisible(el)) continue;
        const label = readLabel(el);
        if (!label || label.length > 60) continue;
        let kind;
        if (REJECT_RE.test(label)) kind = "reject";
        else if (SETTINGS_RE.test(label)) kind = "settings";
        else if (ACCEPT_RE.test(label)) kind = "accept";
        else continue;
        if (onlyMissing && found[kind].length) continue;
        found[kind].push(label);
        if (kind === "accept" || kind === "reject") {
          if (!found.elements[kind]) found.elements[kind] = el;
        }
      } catch (e) { /* next */ }
    }
  }

  function clickableByCursor(container) {
    const ok = new Set();
    for (const e of deepAll("*", container)) {
      const t = (e.innerText || "").trim();
      if (t && t.length <= 60 && getComputedStyle(e).cursor === "pointer") ok.add(e);
    }
    const out = [];
    for (const e of ok) {
      if (!(e.parentElement && ok.has(e.parentElement))) out.push(e);
    }
    return out;
  }

  function scanButtons(container) {
    const found = { accept: [], reject: [], settings: [], elements: {} };
    collectButtons(
      deepAll("button, a, [role='button'], input[type='button'], input[type='submit']", container),
      30, found, false);
    if (found.accept.length && found.reject.length) return found;
    let marked;
    try { marked = clickableByCursor(container); } catch (e) { return found; }
    collectButtons(marked, 120, found, true);
    return found;
  }

  function parentContainer(container) {
    const p = container.parentElement;
    if (!p || p.tagName === "BODY" || p.tagName === "HTML") return null;
    return p;
  }

  function classifyButtons(banner) {
    let container = banner;
    let found = { accept: [], reject: [], settings: [], elements: {} };
    let broke = false;
    for (let i = 0; i < MAX_LEVELS_UP + 1; i++) {
      found = scanButtons(container);
      if (found.accept.length || found.reject.length || found.settings.length) { broke = true; break; }
      container = parentContainer(container);
      if (!container) return found;
    }
    if (!broke) return found;
    if (found.reject.length || !found.accept.length) return found;
    for (let i = 0; i < MAX_LEVELS_UP; i++) {
      container = parentContainer(container);
      if (!container) break;
      try {
        if ((container.innerText || "").length > WIDEN_MAX_TEXT) break;
      } catch (e) { break; }
      const wider = scanButtons(container);
      if (wider.accept.length && wider.reject.length) return wider;
    }
    return found;
  }

  function parseColour(css) {
    const nums = (css || "").match(/[\d.]+/g);
    if (!nums || nums.length < 3) return null;
    const alpha = nums.length > 3 ? parseFloat(nums[3]) : 1.0;
    return [parseFloat(nums[0]), parseFloat(nums[1]), parseFloat(nums[2]), alpha];
  }

  function luminance(c) {
    const ch = (v) => { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2]);
  }

  function contrast(c1, c2) {
    const l1 = luminance(c1), l2 = luminance(c2);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }

  const round = (v, n) => { const m = Math.pow(10, n); return Math.round(v * m) / m; };

  function measureRaw(e) {
    const s = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    const isClear = (c) => /rgba\(.*,\s*0\)$/.test(c) || c === "transparent";
    let anc = e.parentElement, ancBg = "rgb(255, 255, 255)";
    while (anc) {
      const c = getComputedStyle(anc).backgroundColor;
      if (!isClear(c)) { ancBg = c; break; }
      anc = anc.parentElement;
    }
    return {
      width: r.width, height: r.height, fontSize: parseFloat(s.fontSize),
      color: s.color, bg: s.backgroundColor, ancBg,
      border: parseFloat(s.borderTopWidth) || 0,
      tag: e.tagName.toLowerCase(),
      cls: String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className || "").slice(0, 80)
    };
  }

  function measureButton(el) {
    let d;
    try { d = measureRaw(el); } catch (e) { return null; }
    const text = parseColour(d.color), bg = parseColour(d.bg), anc = parseColour(d.ancBg);
    if (!text || !anc) return null;
    const ownBgVisible = bg !== null && bg[3] > 0.05;
    const effectiveBg = ownBgVisible ? bg : anc;
    const dist = ownBgVisible
      ? Math.sqrt([0, 1, 2].reduce((a, i) => a + Math.pow(bg[i] - anc[i], 2), 0)) : 0;
    let style;
    if (ownBgVisible && dist > FILLED_DISTANCE) style = "filled";
    else if (d.border > 0) style = "outlined";
    else style = "plain";
    return {
      area: Math.round(d.width * d.height),
      font_size: d.fontSize,
      contrast: round(contrast(text, effectiveBg), 2),
      style,
      debug: { tag: d.tag, cls: d.cls, bg: d.bg, ancBg: d.ancBg, color: d.color, border: d.border, dist: Math.round(dist) }
    };
  }

  function compareButtons(found) {
    const acc = found.elements.accept ? measureButton(found.elements.accept) : null;
    const rej = found.elements.reject ? measureButton(found.elements.reject) : null;
    const result = {
      accept: acc, reject: rej, size_ratio: null, contrast_diff: null,
      size_flag: false, contrast_flag: false, style_asymmetry_flag: false
    };
    if (acc && rej) {
      if (rej.area > 0) {
        result.size_ratio = round(acc.area / rej.area, 2);
        result.size_flag = result.size_ratio >= SIZE_RATIO;
      }
      result.contrast_diff = round(acc.contrast - rej.contrast, 2);
      result.contrast_flag = result.contrast_diff >= CONTRAST_DIFF;
      result.style_asymmetry_flag = acc.style === "filled" && rej.style !== "filled";
    }
    return result;
  }

  function countCheckboxes(banner) {
    let total = 0, prechecked = 0;
    for (const box of deepAll("input[type='checkbox']", banner).slice(0, 30)) {
      total += 1;
      if (box.checked && !box.disabled) prechecked += 1;
    }
    return { total, prechecked };
  }

  function wordingFlags(text, found) {
    const corpus = norm([text, ...found.accept, ...found.reject, ...found.settings].join(" "));
    const flags = {}, matches = [];
    for (const [name, patterns] of Object.entries(LEXICON_SRC)) {
      flags[name] = false;
      for (const p of patterns) {
        const m = corpus.match(p);
        if (m) { flags[name] = true; matches.push(name + ": " + m[0]); }
      }
    }
    return { flags, matches };
  }

  function firstLayerPattern(found) {
    const a = found.accept.length > 0, r = found.reject.length > 0, s = found.settings.length > 0;
    if (a && r) return "accept_reject";
    if (a && s) return "accept_settings";
    if (a) return "accept_only";
    return "other";
  }

  function analyse(hit, pollIndex) {
    const found = classifyButtons(hit.element);
    const v = compareButtons(found);
    const cb = countCheckboxes(hit.element);
    const w = wordingFlags(hit.text, found);
    return {
      stage: hit.stage,
      selector: hit.selector,
      pollIndex,
      detectedAt: Date.now(),
      frameUrlHost: location.hostname,
      pattern: firstLayerPattern(found),
      accept: found.accept, reject: found.reject, settings: found.settings,
      measures: { accept: v.accept, reject: v.reject },
      size_ratio: v.size_ratio, contrast_diff: v.contrast_diff,
      size_flag: v.size_flag, contrast_flag: v.contrast_flag,
      style_asymmetry_flag: v.style_asymmetry_flag,
      checkboxes_total: cb.total, checkboxes_prechecked: cb.prechecked,
      lang: w.flags, lang_matches: w.matches,
      text: norm(hit.text).slice(0, 2500)
    };
  }

  function findOnce() {
    return (IS_TOP ? findBySelectors() : null) || findIframeBody() || findByText();
  }

  function send(msg) {
    try { chrome.runtime.sendMessage(msg).catch(() => {}); } catch (e) { /* context gone */ }
  }

  async function run() {
    await sleep(SETTLE_MS);
    let waited = 0;
    for (;;) {
      let hit = null;
      try { hit = findOnce(); } catch (e) { hit = null; }
      if (hit) {
        let payload;
        try { payload = analyse(hit, waited / BANNER_POLL_MS); } catch (e) { payload = null; }
        if (payload) { send({ type: "candidate", payload }); return; }
      }
      if (waited >= BANNER_WAIT_EXTRA_MS) break;
      await sleep(BANNER_POLL_MS);
      waited += BANNER_POLL_MS;
    }
    send({ type: "frame-done", isTop: IS_TOP });
  }

  run();
})();