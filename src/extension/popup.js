const $ = (id) => document.getElementById(id);
let lastReport = null;

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v; else e.setAttribute(k, v);
  }
  for (const kid of kids) {
    if (kid == null) continue;
    e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}

function chip(state) {
  if (state === "observed") return el("span", { class: "chip observed" }, "Signal observed");
  if (state === "not_observed") return el("span", { class: "chip not_observed" }, "Not observed");
  if (state === "no_banner") return el("span", { class: "chip na" }, "No banner found");
  return el("span", { class: "chip na" }, "Could not measure");
}

function detail(report, key, ind) {
  const b = report.banner;
  const items = [];
  if (!b) return items;
  const m = b.measures || {};
  if (key === "no_reject_option") {
    items.push("Accept labels: " + (b.accept.join("; ") || "none"));
    items.push("Reject labels: " + (b.reject.join("; ") || "none"));
    items.push("Settings labels: " + (b.settings.join("; ") || "none"));
  } else if (key === "prechecked_box") {
    items.push("Checkboxes in banner: " + b.checkboxes_total + ", pre-ticked and enabled: " + b.checkboxes_prechecked);
  } else if (key === "filled_vs_link") {
    if (m.accept) items.push("Accept style: " + m.accept.style);
    if (m.reject) items.push("Reject style: " + m.reject.style);
  } else if (key === "accept_more_contrast") {
    if (m.accept && m.reject) items.push("Contrast ratio, accept " + m.accept.contrast + " and reject " + m.reject.contrast + " (difference " + b.contrast_diff + ")");
  } else if (key === "accept_much_larger") {
    if (m.accept && m.reject) items.push("Area, accept " + m.accept.area + " px and reject " + m.reject.area + " px (ratio " + b.size_ratio + ")");
  } else if (["confirmshaming", "implied_consent", "vague_purpose", "pressure"].includes(key)) {
    const hits = (b.lang_matches || []).filter((x) => x.startsWith(key + ":"));
    if (hits.length) items.push("Matched: " + hits.map((x) => x.slice(key.length + 2)).join("; "));
  }
  return items;
}

function trackingDetail(report, key) {
  const t = report.tracking;
  if (key === "known_trackers") {
    return t.known_trackers.length ? ["Domains: " + t.known_trackers.join(", ")] : [];
  }
  if (key === "third_party_cookies") {
    return ["Cookies set by responses: " + t.cookies_total + ", third-party: " + t.third_party_cookies]
      .concat(t.third_party_cookie_domains.length ? ["Domains: " + t.third_party_cookie_domains.join(", ")] : []);
  }
  return [];
}

function card(map, key, report) {
  const m = map.indicators[key];
  const ind = report.indicators[key];
  const isNet = key === "known_trackers" || key === "third_party_cookies";
  const state = ind.state;
  const signalText = state === "observed" ? m.observed
    : state === "not_observed" ? m.not_observed
    : state === "no_banner" ? "No banner was found, so this wording or design signal could not be checked."
    : "The needed buttons could not be measured.";
  const extras = isNet ? trackingDetail(report, key) : detail(report, key, ind);
  const c = el("div", { class: "card" },
    el("div", { class: "row" }, el("h2", {}, m.title), chip(state)),
    el("p", {}, signalText));
  if (extras.length) {
    const ul = el("ul", {});
    extras.forEach((x) => ul.append(el("li", {}, x)));
    c.append(ul);
  }
  const d = el("details", {},
    el("summary", {}, "Why it may matter and caution"),
    el("div", { class: "label" }, "Why it may matter"), el("p", {}, m.why),
    el("div", { class: "label" }, "Caution"), el("p", {}, m.caution),
    el("div", { class: "label" }, "Related sources"));
  const ul = el("ul", {});
  m.refs.forEach((r) => ul.append(el("li", {}, map.refs[r])));
  d.append(ul);
  c.append(d);
  return c;
}

function render(map, report) {
  const main = $("main");
  main.replaceChildren();
  if (!report || report.error) {
    main.append(el("p", { class: "muted" }, "No data for this tab yet. Open a normal web page, wait a few seconds, then reopen this popup."));
    return;
  }
  $("site").textContent = report.host;
  if (report.scanning) {
    main.append(el("div", { class: "card" }, el("p", {}, "Still looking for a banner. Reopen this popup in a few seconds.")));
  }
  const summary = report.bannerFound
    ? "Banner found (" + report.banner.stage + (report.banner.stage === "text" ? " fallback" : "") + "). First-layer pattern: " + ({accept_reject:"accept and reject", accept_settings:"accept and settings", accept_only:"accept only", other:"other"})[report.banner.pattern] + "."
    : "No cookie banner was found on this page load.";
  main.append(el("div", { class: "card" }, el("h2", {}, "Summary"), el("p", {}, summary),
    el("p", { class: "muted small" }, "Third-party domains contacted early: " + report.tracking.third_party_domains)));
  for (const key of map.order) main.append(card(map, key, report));
  if (report.bannerFound) {
    const dl = el("dl", { class: "evidence" },
      el("dt", {}, "Banner text (first 600 characters)"), el("dd", {}, report.banner.text.slice(0, 600)));
    main.append(el("details", { class: "card" }, el("summary", {}, "Evidence"), dl));
  }
  $("note").textContent = map.general_note;
}

async function init() {
  const map = await (await fetch(chrome.runtime.getURL("mapping.json"))).json();
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !/^https?:/.test(tab.url || "")) {
    $("main").replaceChildren(el("p", { class: "muted" }, "Open a normal web page to see its signals."));
    $("note").textContent = map.general_note;
    return;
  }
  const report = await chrome.runtime.sendMessage({ type: "getReport", tabId: tab.id });
  lastReport = report;
  render(map, report);
  $("rescan").onclick = () => { chrome.tabs.reload(tab.id); window.close(); };
  $("copy").onclick = async () => {
    try { await navigator.clipboard.writeText(JSON.stringify(lastReport, null, 2)); $("copy").textContent = "Copied"; }
    catch (e) { $("copy").textContent = "Copy failed"; }
  };
}

init();
