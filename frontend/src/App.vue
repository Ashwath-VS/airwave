<template>
  <router-view />
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

:root {
  --bg:         #0a0a0a;
  --surface:    #111111;
  --surface-2:  #161616;
  --border:     #1e1e1e;
  --border-2:   #2a2a2a;
  --txt:        #e8e8e8;
  --txt-dim:    #666;
  --txt-faint:  #333;
  --acc:        #00acc1;      /* travel-tech teal */
  --acc-dim:    rgba(0, 172, 193, 0.15);
  --acc-glow:   rgba(0, 172, 193, 0.35);
  --warn:       #ff9100;      /* macro engine orange */
  --warn-dim:   rgba(255, 145, 0, 0.15);
  --pos:        #00e676;      /* positive / raise */
  --neg:        #ff3b30;      /* negative / drop */
  --mono:       'JetBrains Mono', 'SF Mono', Consolas, monospace;
  --radius:     4px;
  --radius-lg:  8px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body, #app {
  height: 100%;
  background: var(--bg);
  color: var(--txt);
  font-family: var(--mono);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--txt-faint); }

button { font-family: inherit; cursor: pointer; }
input  { font-family: inherit; }

/* Dot-matrix background */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
  z-index: 0;
}
#app { position: relative; z-index: 1; }
</style>
