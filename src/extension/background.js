importScripts("psl.js");

const OBSERVE_AFTER_DCL_MS = 4000;
const MAX_HOSTS = 2000;
const MAX_COOKIES = 500;

let trackerSet = null;
let ready = null;
const tabs = new Map();

async function loadTrackers() {
  if (trackerSet) return trackerSet;
  const res = await fetch(chrome.runtime.getURL("trackers.json"));
  trackerSet = new Set(await res.json());
  return trackerSet;
}

async function loadState() {
  try {
    const all = await chrome.storage.session.get(null);
    for (const [k, v] of Object.entries(all)) {
      if (k.startsWith("tab:")) tabs.set(Number(k.slice(4)), v);
    }
  } catch (e) { /* storage.session unavailable */ }
}

ready = loadState();

const pending = new Map();
function persist(tabId) {
  if (pending.has(tabId)) return;
  pending.set(tabId, setTimeout(async () => {
    pending.delete(tabId);
    const s = tabs.get(tabId);
    try {
      if (s) await chrome.storage.session.set({ ["tab:" + tabId]: s });
      else await chrome.storage.session.remove("tab:" + tabId);
    } catch (e) { /* ignore */ }
  }, 400));
}

function newState(url) {
  return {
    url, navStart: Date.now(), windowEnd: null, hosts: {}, cookies: [],
    candidates: [], framesDone: 0, topDone: false
  };
}

function hostOf(url) {
  try { return new URL(url).hostname.toLowerCase(); } catch (e) { return ""; }
}

function inWindow(s) {
  return s.windowEnd === null || Date.now() <= s.windowEnd;
}

chrome.webNavigation.onBeforeNavigate.addListener(async (d) => {
  if (d.frameId !== 0 || !/^https?:/.test(d.url)) return;
  await ready;
  tabs.set(d.tabId, newState(d.url));
  persist(d.tabId);
});

chrome.webNavigation.onCommitted.addListener(async (d) => {
  if (d.frameId !== 0 || !/^https?:/.test(d.url)) return;
  await ready;
  let s = tabs.get(d.tabId);
  if (!s) { s = newState(d.url); tabs.set(d.tabId, s); }
  s.url = d.url;
  persist(d.tabId);
});

chrome.webNavigation.onDOMContentLoaded.addListener(async (d) => {
  if (d.frameId !== 0) return;
  await ready;
  const s = tabs.get(d.tabId);
  if (!s) return;
  s.windowEnd = Date.now() + OBSERVE_AFTER_DCL_MS;
  persist(d.tabId);
});

chrome.webRequest.onBeforeRequest.addListener((d) => {
  if (d.tabId < 0) return;
  ready.then(() => {
    const s = tabs.get(d.tabId);
    if (!s || !inWindow(s)) return;
    if (!/^https?:/.test(d.url)) return;
    const h = hostOf(d.url);
    if (h && !(h in s.hosts) && Object.keys(s.hosts).length < MAX_HOSTS) {
      s.hosts[h] = 1;
      persist(d.tabId);
    }
  });
}, { urls: ["http://*/*", "https://*/*"] });

chrome.webRequest.onHeadersReceived.addListener((d) => {
  if (d.tabId < 0 || !d.responseHeaders) return;
  const sets = d.responseHeaders.filter((h) => h.name.toLowerCase() === "set-cookie");
  if (!sets.length) return;
  ready.then(() => {
    const s = tabs.get(d.tabId);
    if (!s || !inWindow(s)) return;
    const reqHost = hostOf(d.url);
    for (const h of sets) {
      for (const line of String(h.value || "").split("\n")) {
        const name = line.split("=")[0].trim();
        if (!name) continue;
        const m = line.match(/;\s*domain=([^;]+)/i);
        const domain = (m ? m[1].trim() : reqHost).replace(/^\./, "").toLowerCase();
        const pm = line.match(/;\s*path=([^;]+)/i);
        const path = pm ? pm[1].trim() : "/";
        const age = line.match(/;\s*max-age=(-?\d+)/i);
        const exp = line.match(/;\s*expires=([^;]+)/i);
        const expired = (age && Number(age[1]) <= 0) || (!age && exp && Date.parse(exp[1]) < Date.now());
        const idx = s.cookies.findIndex((c) => c.name === name && c.domain === domain && c.path === path);
        if (expired) { if (idx >= 0) s.cookies.splice(idx, 1); continue; }
        if (idx >= 0) continue;
        if (s.cookies.length < MAX_COOKIES) s.cookies.push({ name, domain, path });
      }
    }
    persist(d.tabId);
  });
}, { urls: ["http://*/*", "https://*/*"] }, ["responseHeaders", "extraHeaders"]);

chrome.tabs.onRemoved.addListener(async (tabId) => {
  await ready;
  tabs.delete(tabId);
  persist(tabId);
});

function isKnownTracker(host, set) {
  const parts = String(host || "").toLowerCase().split(".");
  for (let i = 0; i < parts.length - 1; i++) {
    if (set.has(parts.slice(i).join("."))) return true;
  }
  return false;
}

function summariseTracking(s, set) {
  const siteDomain = registeredDomain(hostOf(s.url));
  const hosts = Object.keys(s.hosts);
  const third = hosts.filter((h) => h && registeredDomain(h) !== siteDomain).sort();
  const trackers = third.filter((h) => isKnownTracker(h, set));
  const thirdCookies = s.cookies.filter((c) => registeredDomain(c.domain) !== siteDomain);
  return {
    third_party_domains: new Set(third.map(registeredDomain)).size,
    known_trackers: [...new Set(trackers.map(registeredDomain))].sort(),
    cookies_total: s.cookies.length,
    third_party_cookies: thirdCookies.length,
    third_party_cookie_domains: [...new Set(thirdCookies.map((c) => registeredDomain(c.domain)))].sort()
  };
}

const STAGE_PRIORITY = { selector: 0, iframe: 1, text: 2 };

function pickCandidate(s) {
  if (!s.candidates.length) return null;
  const bin = (c) => Math.max(0, Math.floor((c.detectedAt - s.navStart - 4000) / 2000));
  return [...s.candidates].sort((a, b) =>
    bin(a) - bin(b) || STAGE_PRIORITY[a.stage] - STAGE_PRIORITY[b.stage] || a.detectedAt - b.detectedAt)[0];
}

function indicator(state, value) { return { state, value }; }

function computeIndicators(c, t) {
  const out = {};
  const has = !!c;
  const measured = has && c.measures.accept && c.measures.reject;
  out.no_reject_option = !has ? indicator("no_banner")
    : !c.accept.length ? indicator("not_measurable")
    : indicator(c.reject.length ? "not_observed" : "observed");
  out.prechecked_box = !has ? indicator("no_banner")
    : indicator(c.checkboxes_prechecked > 0 ? "observed" : "not_observed", c.checkboxes_prechecked);
  out.filled_vs_link = !has ? indicator("no_banner")
    : !measured ? indicator("not_measurable") : indicator(c.style_asymmetry_flag ? "observed" : "not_observed");
  out.accept_more_contrast = !has ? indicator("no_banner")
    : !measured ? indicator("not_measurable") : indicator(c.contrast_flag ? "observed" : "not_observed", c.contrast_diff);
  out.accept_much_larger = !has ? indicator("no_banner")
    : !measured ? indicator("not_measurable") : indicator(c.size_flag ? "observed" : "not_observed", c.size_ratio);
  for (const k of ["confirmshaming", "implied_consent", "vague_purpose", "pressure"]) {
    out[k] = !has ? indicator("no_banner") : indicator(c.lang[k] ? "observed" : "not_observed");
  }
  out.known_trackers = indicator(t.known_trackers.length ? "observed" : "not_observed", t.known_trackers.length);
  out.third_party_cookies = indicator(t.third_party_cookies ? "observed" : "not_observed", t.third_party_cookies);
  return out;
}

async function buildReport(tabId) {
  await ready;
  const set = await loadTrackers();
  const s = tabs.get(tabId);
  if (!s) return { error: "no_data" };
  const c = pickCandidate(s);
  const t = summariseTracking(s, set);
  const now = Date.now();
  const scanning = !c && !s.topDone && now - s.navStart < 4000 + 14000 + 6000;
  return {
    url: s.url,
    host: hostOf(s.url),
    observationOpen: s.windowEnd === null || now <= s.windowEnd,
    scanning,
    bannerFound: !!c,
    banner: c,
    tracking: t,
    thirdPartyHosts: Object.keys(s.hosts).filter((h) => registeredDomain(h) !== registeredDomain(hostOf(s.url))).sort(),
    indicators: computeIndicators(c, t),
    generatedAt: new Date().toISOString()
  };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "candidate" && sender.tab) {
    ready.then(() => {
      const s = tabs.get(sender.tab.id);
      if (!s) return;
      s.candidates.push(msg.payload);
      persist(sender.tab.id);
    });
    return false;
  }
  if (msg && msg.type === "frame-done" && sender.tab) {
    ready.then(() => {
      const s = tabs.get(sender.tab.id);
      if (!s) return;
      s.framesDone += 1;
      if (msg.isTop) s.topDone = true;
      persist(sender.tab.id);
    });
    return false;
  }
  if (msg && msg.type === "getReport") {
    buildReport(msg.tabId).then(sendResponse);
    return true;
  }
  return false;
});