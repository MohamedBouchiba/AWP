"""Presentation for the OAuth onboarding wizard + developer dashboard.

Pure HTML/CSS templates for app.py's owner-facing and dev-facing pages. The CSS
lives in assets/css/onboarding.css and is inlined at import time (identical output
to the previous inline <style> block). To restyle these pages, edit that .css file.
"""
import os
from html import escape as esc

_CSS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "css")


def _load_css(name):
    with open(os.path.join(_CSS_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


# --- Generic info/error page ---
def render_info(title: str, message: str, detail: str | None = None) -> str:
    detail_html = f'<pre class="out">{esc(detail)}</pre>' if detail else ""
    html = INFO_HTML.replace("__FONTS__", FONTS).replace("__STYLE__", STYLE)
    html = html.replace("__TITLE__", esc(title))
    html = html.replace("__MSG__", esc(message))
    html = html.replace("__DETAIL__", detail_html)
    return html


# ===========================================================================
#  Presentation -- fonts, shared stylesheet, and HTML templates.
#  Templates are plain strings with __PLACEHOLDER__ tokens (no f-strings) so
#  CSS braces don't need escaping.
# ===========================================================================

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,650&'
    'family=Hanken+Grotesk:wght@400;500;600;700&'
    'family=JetBrains+Mono:wght@400;500&display=swap">'
)

STYLE = "<style>" + _load_css("onboarding.css") + "</style>"

WIZARD_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connect your Teamleader account</title>
__FONTS__
__STYLE__
</head><body>
<div class="page"><main class="card">
  <header class="card__head">
    <div class="brand"><span class="brand__mark">T</span><span class="brand__name">Teamleader Access</span></div>
    <div class="pill" id="pill" data-state="waiting">
      <span class="pill__dot"></span><span class="pill__txt">Waiting to connect</span>
    </div>
  </header>

  <div class="hero">
    <h1 class="title">Let&rsquo;s connect your Teamleader account</h1>
    <p class="lede">Three quick steps, about two minutes. No technical skills needed. You sign in
      on Teamleader&rsquo;s own page &mdash; we never see your password. At the end, we run a real
      check and confirm everything works.</p>
  </div>

  <ol class="stepper" id="stepper">
    <li class="stepper__item" data-for="1"><span class="stepper__num">1</span><span class="stepper__label">Authorize&nbsp;URL</span></li>
    <li class="stepper__item" data-for="2"><span class="stepper__num">2</span><span class="stepper__label">Connect</span></li>
    <li class="stepper__item" data-for="3"><span class="stepper__num">3</span><span class="stepper__label">Verify</span></li>
  </ol>

  <div class="banner banner--danger" id="misconfig" hidden>
    <strong>The connection isn&rsquo;t ready yet.</strong> This page hasn&rsquo;t been fully
    set up by your developer. Please let them know before continuing.
  </div>

  <div class="banner banner--warn" id="attempted" hidden>
    <strong>It looks like the last attempt didn&rsquo;t finish.</strong> The most common reason is
    that the address from <strong>Step&nbsp;1</strong> isn&rsquo;t authorized in Teamleader yet, or
    has a small typo. Please re-check Step&nbsp;1, then try Step&nbsp;2 again.
  </div>

  <!-- Step 1 -->
  <section class="step" data-step="1">
    <h2 class="step__title">Step 1 &mdash; Authorize the return address</h2>
    <p class="step__text">When you connect, Teamleader needs to know which address to send you back
      to. For your security, it only allows addresses that were approved in advance. <strong>Copy</strong>
      the address below and add it once in your Teamleader settings.</p>
    <div class="urlbox">
      <code class="urlbox__value" id="redirect-uri">__REDIRECT_URI__</code>
      <button class="urlbox__copy" type="button" data-copy="#redirect-uri">Copy</button>
    </div>
    <ol class="howto">
      <li>Open the <strong>Teamleader Marketplace</strong> and open your integration.</li>
      <li>Go to the <strong>Build</strong> tab.</li>
      <li>Find the <strong>Redirect URIs</strong> field.</li>
      <li><strong>Paste</strong> the address, add it, then click <strong>Save</strong>.</li>
    </ol>
    <a class="btn btn--ghost" href="__MARKETPLACE_URL__" target="_blank" rel="noopener">Open Teamleader Marketplace &#8599;</a>
    <div class="vnote"><span class="vnote__icon">&#9432;</span><span>There&rsquo;s no checkmark to show here &mdash; this setting lives inside Teamleader. We confirm it
      <strong>automatically</strong> the instant you connect in Step&nbsp;2, and if anything is off we&rsquo;ll
      tell you exactly what to fix.</span></div>
    <div class="step__actions">
      <button class="btn btn--primary" type="button" onclick="goStep(2)">I&rsquo;ve added it &rarr; Step 2</button>
    </div>
  </section>

  <!-- Step 2 -->
  <section class="step" data-step="2">
    <h2 class="step__title">Step 2 &mdash; Connect your account</h2>
    <p class="step__text">Click the button below. You&rsquo;ll sign in on Teamleader&rsquo;s own secure
      page (we never see your password), then click <strong>Authorize</strong>. We&rsquo;ll bring you
      straight back here.</p>
    <div class="vnote"><span class="vnote__icon">&#9432;</span><span>The moment you authorize, we run a <strong>live test query</strong> on your account. You&rsquo;ll
      get a clear &ldquo;verified&rdquo; confirmation &mdash; or an exact error if something needs fixing.</span></div>
    <div class="step__actions">
      <a class="btn btn--primary btn--lg" id="connectBtn" href="/connect">Connect my Teamleader account</a>
      <button class="btn btn--ghost" type="button" onclick="goStep(1)">&larr; Back to Step 1</button>
    </div>
    <details class="note note--help"><summary>The Teamleader screen shows an error (invalid_redirect_uri)?</summary>
      <p>That means the address from Step 1 hasn&rsquo;t been added yet, or it has a typo. Here it
        is again:</p>
      <div class="urlbox urlbox--sm">
        <code class="urlbox__value" id="redirect-uri-2">__REDIRECT_URI__</code>
        <button class="urlbox__copy" type="button" data-copy="#redirect-uri-2">Copy</button>
      </div>
      <p>Make sure it matches <strong>exactly</strong> (starts with https, no extra slash at the
        end), save, wait a few seconds, and try again.
        <a class="link" href="#" onclick="goStep(1);return false;">&larr; Back to Step 1</a></p>
    </details>
  </section>

  <!-- Step 3 -->
  <section class="step" data-step="3">
    <div class="verify-state" id="verify-pending">
      <div class="spinner"></div>
      <h2 class="step__title">Almost there &mdash; verifying&hellip;</h2>
      <p class="step__text">We&rsquo;re running a real test query against your Teamleader account to
        make sure your data can actually be read. This only takes a few seconds.</p>
    </div>
    <div class="verify-state" id="verify-ok" hidden>
      <div class="done__check">&#10003;</div>
      <h2 class="step__title">You&rsquo;re all set &mdash; and we&rsquo;ve checked it works!</h2>
      <p class="step__text">We connected to your Teamleader account and successfully ran a live test
        query (<span class="verify-name" id="verify-name">your account</span>). Your developer now has
        everything needed to access your data. You can safely close this page &mdash; there&rsquo;s
        nothing else to do.</p>
      <a class="btn btn--ghost" href="/connect">Connect a different account</a>
    </div>
    <div class="verify-state" id="verify-err" hidden>
      <div class="done__check done__check--warn">!</div>
      <h2 class="step__title">Connected &mdash; but we couldn&rsquo;t read your data yet</h2>
      <p class="step__text" id="verify-errmsg">&hellip;</p>
      <a class="btn btn--primary" href="/connect">Try connecting again</a>
    </div>
  </section>

  <footer class="card__foot">Secured with OAuth&nbsp;2.0 &middot; Teamleader Focus</footer>
</main></div>

<script>
var CLIENT_OK = ("__CLIENT_OK__" === "1");
var INITIAL_CONNECTED = ("__INITIAL_CONNECTED__" === "1");
var ATTEMPTED = ("__ATTEMPTED__" === "1");
var pollTimer = null;
var verified = false;

function goStep(n){
  document.querySelectorAll(".step").forEach(function(s){
    s.classList.toggle("is-active", Number(s.dataset.step) === n);
  });
  document.querySelectorAll(".stepper__item").forEach(function(it){
    var i = Number(it.dataset.for);
    it.classList.toggle("is-active", i === n);
    it.classList.toggle("is-done", i < n);
  });
  document.getElementById("stepper").style.setProperty("--progress", String((n-1)/2*100));
  window.scrollTo({top:0, behavior:"smooth"});
}

function setPill(state){
  var p = document.getElementById("pill");
  var txt = p.querySelector(".pill__txt");
  if(state === "verified"){ p.dataset.state = "connected"; txt.textContent = "Connected & verified"; }
  else if(state === "verifying"){ p.dataset.state = "waiting"; txt.textContent = "Verifying\\u2026"; }
  else { p.dataset.state = "waiting"; txt.textContent = "Waiting to connect"; }
}

function showVerify(which){
  ["pending","ok","err"].forEach(function(k){
    var el = document.getElementById("verify-" + k);
    if(el){ el.hidden = (k !== which); }
  });
}

function runVerify(){
  showVerify("pending"); setPill("verifying");
  fetch("/verify", {cache:"no-store"})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(d && d.ok){
        verified = true;
        document.getElementById("verify-name").textContent =
          d.name ? ("signed in as " + d.name) : "test query successful";
        showVerify("ok"); setPill("verified");
      } else {
        document.getElementById("verify-errmsg").textContent =
          (d && d.message) ? d.message
            : "We connected, but couldn't read your data. Please try reconnecting.";
        showVerify("err"); setPill("waiting");
      }
    })
    .catch(function(){
      document.getElementById("verify-errmsg").textContent =
        "Network problem while verifying. Please refresh the page.";
      showVerify("err");
    });
}

function onConnected(){
  if(pollTimer){ clearInterval(pollTimer); pollTimer = null; }
  goStep(3);
  runVerify();
}

function checkStatus(){
  fetch("/status", {cache:"no-store"})
    .then(function(r){ return r.json(); })
    .then(function(d){ if(d && d.connected){ onConnected(); } })
    .catch(function(){});
}

function fallbackCopy(text, cb){
  var ta = document.createElement("textarea");
  ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.focus(); ta.select();
  try{ document.execCommand("copy"); }catch(e){}
  document.body.removeChild(ta); if(cb){ cb(); }
}

document.addEventListener("click", function(e){
  var b = e.target.closest("[data-copy]");
  if(!b) return;
  var el = document.querySelector(b.dataset.copy);
  if(!el) return;
  var text = el.textContent.trim();
  var done = function(){
    var orig = b.textContent;
    b.textContent = "Copied \\u2713"; b.classList.add("is-copied");
    setTimeout(function(){ b.textContent = orig; b.classList.remove("is-copied"); }, 1500);
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){ fallbackCopy(text, done); });
  } else { fallbackCopy(text, done); }
});

(function init(){
  if(!CLIENT_OK){
    document.getElementById("misconfig").hidden = false;
    var c = document.getElementById("connectBtn");
    if(c){ c.classList.add("is-disabled"); c.setAttribute("aria-disabled","true");
      c.addEventListener("click", function(e){ e.preventDefault(); }); }
  }
  if(ATTEMPTED){
    var a = document.getElementById("attempted");
    if(a){ a.hidden = false; }
  }
  if(INITIAL_CONNECTED){ goStep(3); runVerify(); }
  else { goStep(1); pollTimer = setInterval(checkStatus, 3000); }
})();
</script>
</body></html>"""

INFO_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
__FONTS__
__STYLE__
</head><body>
<div class="page"><main class="card">
  <header class="card__head">
    <div class="brand"><span class="brand__mark">T</span><span class="brand__name">Teamleader Access</span></div>
  </header>
  <h1 class="title" style="font-size:1.7rem">__TITLE__</h1>
  <p class="lede" style="margin-bottom:18px">__MSG__</p>
  __DETAIL__
  <div class="step__actions"><a class="btn btn--primary" href="/">&larr; Back to start</a></div>
</main></div>
</body></html>"""

DEV_LOGIN_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Developer access</title>
__FONTS__
__STYLE__
</head><body>
<div class="page"><main class="card">
  <header class="card__head">
    <div class="brand"><span class="brand__mark">T</span><span class="brand__name">Teamleader Access &middot; Dev</span></div>
  </header>
  <h1 class="title" style="font-size:1.6rem">Developer access</h1>
  <p class="lede">Enter your developer key to open the verification dashboard.</p>
  __NOTE__
  <form class="form" method="get" action="/dev">
    <input type="password" name="key" placeholder="DEV_API_KEY" autofocus autocomplete="off">
    <button class="btn btn--primary" type="submit">Open</button>
  </form>
</main></div>
</body></html>"""

DEV_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Developer dashboard</title>
__FONTS__
__STYLE__
</head><body>
<div class="page"><main class="card dev">
  <header class="card__head">
    <div class="brand"><span class="brand__mark">T</span><span class="brand__name">Teamleader Access &middot; Dev</span></div>
    <a class="pill" href="/" style="text-decoration:none;color:var(--ink-soft)">Owner page &#8599;</a>
  </header>
  <h1 class="title">Developer dashboard</h1>
  __MISMATCH__
  __STATUS__

  <h2>Configuration</h2>
  <ul class="check-list">__CHECKS__</ul>

  <h2>Redirect URI (whitelist this in Teamleader)</h2>
  <div class="urlbox urlbox--sm">
    <code class="urlbox__value" id="redirect-uri">__REDIRECT_URI__</code>
    <button class="urlbox__copy" type="button" data-copy="#redirect-uri">Copy</button>
  </div>

  <h2>Test a live query</h2>
  <div class="testbar">
    <button class="btn btn--primary" type="button" onclick="runTest('users.me', {})">users.me</button>
    <button class="btn btn--ghost" type="button" onclick="runTest('contacts.list', {page:{size:3}})">contacts.list</button>
    <span class="chip" id="chip" style="display:none"></span>
  </div>
  <pre class="out" id="out">No query run yet.</pre>

  <footer class="card__foot">Keep your DEV key private. Rotate it if it leaks.</footer>
</main></div>

<script>
var DEV_KEY = __DEV_KEY_JSON__;

// Auto-run a real query on load so the developer instantly sees API access works.
window.addEventListener("load", function(){ runTest("users.me", {}); });

function runTest(endpoint, body){
  var out = document.getElementById("out");
  var chip = document.getElementById("chip");
  out.textContent = "Running " + endpoint + " ...";
  chip.style.display = "none";
  fetch("/api/" + endpoint, {
    method:"POST",
    headers:{"X-Dev-Key":DEV_KEY, "Content-Type":"application/json"},
    body: JSON.stringify(body || {})
  }).then(function(r){
    return r.text().then(function(txt){
      var pretty = txt;
      try{ pretty = JSON.stringify(JSON.parse(txt), null, 2); }catch(e){}
      chip.style.display = "";
      chip.textContent = "HTTP " + r.status;
      chip.className = "chip " + (r.ok ? "chip--ok" : "chip--err");
      out.textContent = pretty;
    });
  }).catch(function(e){ out.textContent = "Error: " + e; });
}

document.addEventListener("click", function(e){
  var b = e.target.closest("[data-copy]");
  if(!b) return;
  var el = document.querySelector(b.dataset.copy);
  if(!el) return;
  var text = el.textContent.trim();
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text);
  }
  var orig = b.textContent; b.textContent = "Copied \\u2713"; b.classList.add("is-copied");
  setTimeout(function(){ b.textContent = orig; b.classList.remove("is-copied"); }, 1500);
});
</script>
</body></html>"""
