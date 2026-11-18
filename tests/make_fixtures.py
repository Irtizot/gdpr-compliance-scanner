from pathlib import Path

FX = Path(__file__).resolve().parent / "fx"
FX.mkdir(exist_ok=True)

LOREM = "".join(
    f"<p>Lorem ipsum article paragraph {i} about travel and shopping deals for everyone.</p>"
    for i in range(40)
)
FOOTER = (
    '<footer><a href="#">Cookie policy</a> <a href="#">Privacy</a> '
    "<div>Intellectual Property - Privacy Policy - Cookie Preferences and more links here</div></footer>"
)

PAGES = {
    "trackers": """<!doctype html><html><head><title>t</title></head><body>
<p>Plain page with early third-party activity.</p>
<img src="https://doubleclick.net:8766/p.gif" width="1" height="1">
<img src="https://example-cdn.test:8766/x.gif" width="1" height="1">
<div id="cookie-banner" style="position:fixed;bottom:0;left:0;right:0;background:#fff;padding:20px;border:1px solid #ccc">
 <p>We use cookies to improve your experience. By continuing to use this site you agree to our cookie policy. You must accept to continue.</p>
 <label><input type="checkbox" checked> Marketing</label> <label><input type="checkbox" checked disabled> Necessary</label>
 <button style="background:#0a7d2c;color:#fff;border:0;padding:14px 40px;font-size:18px">Accept all</button>
 <a href="#" style="color:#999;font-size:11px">Reject all</a>
</div></body></html>
""",
    "normal_button": "<html><body>" + LOREM
    + "<div id='x' style='position:fixed;bottom:0;width:900px;height:80px;background:#eee'>"
    "<p>This site uses cookies and similar technologies for analytics.</p>"
    "<button>Reject all</button><button>Accept all</button><button>Manage preferences</button></div>"
    + FOOTER + "</body></html>",
    "overlay_div": "<html><body>" + LOREM + FOOTER
    + "<div style='position:fixed;inset:0;background:#0008'>"
    "<div style='background:#fff;margin:100px auto;width:600px;height:200px'>"
    "<p>Eloboss uses cookies! By using our website you agree to our Privacy Policy.</p>"
    "<div style='cursor:pointer;padding:6px'><span>Got it</span></div></div></div></body></html>",
    "late_div": "<html><body>" + LOREM + FOOTER
    + "<script>setTimeout(()=>{document.body.insertAdjacentHTML('beforeend',"
    "`<div style='position:fixed;bottom:0;left:0;width:900px;height:90px;background:#fff'>"
    "<span>We use cookies to improve your experience. By using our website you agree.</span>"
    "<div style='cursor:pointer;display:inline-block;padding:8px;border:1px solid'>Reject cookies</div>"
    "<div style='cursor:pointer;display:inline-block;padding:8px;background:#06c;color:#fff'>Accept cookies</div>"
    "</div>`)},6000)</script></body></html>",
    "shadow": "<html><body><div id=h></div><script>"
    "const s=document.getElementById('h').attachShadow({mode:'open'});"
    's.innerHTML="<div style=\'position:fixed;bottom:0;width:700px;height:100px;background:#fff\'>'
    "<p>We use cookies to improve your experience and measure traffic.</p>"
    "<div style=\'cursor:pointer;padding:6px\'>Accept all</div></div>\";</script></body></html>",
    "iframe_host": '<!doctype html><html><head><title>t</title></head><body><h1>Page with iframe banner</h1>\n'
    '<iframe src="/iframe_inner.html" style="position:fixed;bottom:0;left:0;width:100%;height:160px;border:0">'
    "</iframe></body></html>\n",
    "iframe_inner": '<!doctype html><html><body style="margin:0;font-family:sans-serif">\n'
    '<div style="padding:16px"><p>This site uses cookies and privacy settings. Choose an option.</p>\n'
    '<button style="background:#2255cc;color:#fff;padding:10px 20px;border:0">Accept all</button>\n'
    '<button style="background:#fff;color:#222;padding:10px 20px;border:1px solid #222">Reject all</button>'
    "</div></body></html>\n",
    "footer_only": "<html><body>" + LOREM
    + "<button style='padding:10px;width:80px'>OK</button>" + FOOTER + "</body></html>",
    "nobanner": "<!doctype html><html><head><title>t</title></head><body><h1>Nothing here</h1>"
    "<p>Just a page about gardening.</p></body></html>\n",
}

for name, html in PAGES.items():
    (FX / f"{name}.html").write_text(html, encoding="utf-8", newline="")
    print("wrote", name)