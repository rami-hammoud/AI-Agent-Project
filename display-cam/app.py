HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Display Cam</title>
    <style>
      :root { color-scheme: dark; }
      body { margin:0; background:#0b0b0b; color:#eee; font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial; }
      header { padding:12px 16px; border-bottom:1px solid #222; display:flex; align-items:center; gap:12px;}
      .badge { font-size:12px; padding:2px 8px; background:#222; border-radius:999px; }
      .funny-box { margin:20px auto; max-width:640px; background:#222; padding:16px; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,.5); text-align:center; }
      .funny-box h2 { margin-top:0; color:#ffcc66; }
      .funny-box img { max-width:100%; border-radius:12px; margin:12px 0; }
      .wrap { display:flex; justify-content:center; align-items:center; height: calc(100vh - 300px); }
      img.stream { max-width:100%; max-height:100%; display:block; }
      footer { position:fixed; bottom:8px; left:16px; opacity:.6; font-size:12px;}
      a { color:#9cf; text-decoration:none; }
    </style>
  </head>
  <body>
    <header>
      <div><strong>Display Cam</strong></div>
      <div class="badge">localhost</div>
      <div style="margin-left:auto; font-size:14px">
        <a href="/snapshot">snapshot</a>
      </div>
    </header>

    <div class="funny-box">
      <h2>Meet Lara Hammoud 🎉</h2>
      <img src="/static/lara.jpg" alt="Funny Lara">
      <p>
        Lara Hammoud, the youngest Hammoud sibling, is officially the family’s
        Chief Mischief Officer™. Known for her sharp one-liners, random dance
        breaks, and ability to steal snacks without witnesses, Lara has a PhD in
        Making Everyone Laugh. She firmly believes that serious faces are
        overrated, and if life gives you lemons, you should probably juggle them
        in front of your siblings until they beg you to stop. 🍋🤹‍♀️
      </p>
    </div>

    <div class="wrap">
      <img class="stream" src="/stream" alt="camera stream" />
    </div>

    <footer>
      /stream (MJPEG) • /snapshot (JPEG) • /healthz
    </footer>
  </body>
</html>
"""
