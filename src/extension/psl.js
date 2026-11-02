(function (g) {
  const TWO_LEVEL = new Set([
    "co.uk","org.uk","ac.uk","gov.uk","me.uk","ltd.uk","plc.uk","net.uk","sch.uk","nhs.uk","police.uk",
    "com.au","net.au","org.au","edu.au","gov.au","co.nz","org.nz","net.nz","govt.nz","ac.nz",
    "co.jp","ne.jp","or.jp","ac.jp","go.jp","co.kr","or.kr","ac.kr","go.kr",
    "com.br","net.br","org.br","gov.br","com.cn","net.cn","org.cn","gov.cn","edu.cn",
    "co.in","net.in","org.in","gov.in","ac.in","co.za","org.za","gov.za","ac.za",
    "com.mx","org.mx","gob.mx","com.tr","org.tr","gov.tr","edu.tr","com.sg","edu.sg","gov.sg",
    "com.hk","org.hk","edu.hk","gov.hk","com.tw","org.tw","edu.tw","gov.tw","com.my","gov.my",
    "co.id","or.id","go.id","ac.id","com.ar","gob.ar","com.co","com.pe","com.ve","com.ec",
    "com.ua","org.ua","co.il","org.il","ac.il","gov.il","com.ph","com.vn","com.pk","com.ng",
    "co.ke","co.th","co.ae","com.sa","com.eg","com.pl","com.pt","com.es","com.ru","co.ie"
  ]);
  function registeredDomain(host) {
    host = String(host || "").toLowerCase().replace(/\.$/, "");
    if (!host || /^[\d.]+$/.test(host) || host.includes(":")) return host;
    const parts = host.split(".");
    if (parts.length <= 2) return host;
    const last2 = parts.slice(-2).join(".");
    if (TWO_LEVEL.has(last2)) return parts.slice(-3).join(".");
    return parts.slice(-2).join(".");
  }
  g.registeredDomain = registeredDomain;
})(typeof self !== "undefined" ? self : this);
