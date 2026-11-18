FIXTURES = ["trackers", "normal_button", "overlay_div", "late_div", "shadow", "iframe_host", "footer_only", "nobanner"]
BASE = "http://localhost:8765/"
ARGS = ["--ignore-certificate-errors", "--no-proxy-server",
        "--host-resolver-rules=MAP localhost 127.0.0.1, MAP doubleclick.net 127.0.0.1, MAP example-cdn.test 127.0.0.1"]