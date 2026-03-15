import hashlib

def _hash(text: str, mod: int) -> int:
    return int(hashlib.md5(text.encode()).hexdigest(), 16) % mod

def generate_cyberpunk_svg(project_name: str, width: int = 800, height: int = 300) -> str:
    seed = project_name.lower()
    accent_hues = [180, 300, 120, 200, 340, 60, 270, 160]
    h1 = accent_hues[_hash(seed, len(accent_hues))]
    h2 = accent_hues[_hash(seed + "b", len(accent_hues))]
    accent1 = "hsl({}, 100%, 60%)".format(h1)
    accent2 = "hsl({}, 100%, 55%)".format(h2)
    glow1   = "hsl({}, 100%, 70%)".format(h1)

    n_buildings = 14 + _hash(seed + "n", 8)
    buildings_bg, buildings_mg, buildings_fg = [], [], []
    w_step = width / n_buildings

    for i in range(n_buildings):
        bw    = int(w_step * (0.55 + _hash("{}bw{}".format(seed,i), 60) / 100))
        bx    = int(i * w_step + _hash("{}bx{}".format(seed,i), int(w_step * 0.4)))
        bh_bg = int(height * (0.35 + _hash("{}bbg{}".format(seed,i), 40) / 100))
        bh_mg = int(height * (0.45 + _hash("{}bmg{}".format(seed,i), 35) / 100))
        bh_fg = int(height * (0.20 + _hash("{}bfg{}".format(seed,i), 30) / 100))
        buildings_bg.append((bx, bw, bh_bg))
        buildings_mg.append((bx, bw, bh_mg))
        buildings_fg.append((bx, bw, bh_fg))

    def windows(bx, bw, bh, base_y, seed_extra, lit_color):
        rows = max(2, bh // 14)
        cols = max(1, bw // 9)
        rects = []
        for r in range(rows):
            for c in range(cols):
                wx  = bx + 3 + c * 9
                wy  = base_y + r * 13 + 4
                lit = _hash("{}{}{}{}".format(seed,seed_extra,r,c), 5) < 3
                col = lit_color if lit else "#0a0a0a"
                opa = 0.7 + _hash("{}op{}{}{}".format(seed,seed_extra,r,c), 30) / 100 if lit else 0.3
                rects.append('<rect x="{}" y="{}" width="5" height="8" fill="{}" opacity="{:.2f}"/>'.format(wx,wy,col,opa))
        return "\n".join(rects)

    parts = []
    # sky
    parts.append('<rect width="{}" height="{}" fill="url(#sky)"/>'.format(width, height))
    # stars
    for i in range(40):
        cx  = _hash("{}star{}".format(seed,i),  width)
        cy  = _hash("{}stary{}".format(seed,i), height // 2)
        opa = 0.2 + _hash("{}staro{}".format(seed,i), 50) / 100
        parts.append('<circle cx="{}" cy="{}" r="0.8" fill="white" opacity="{:.2f}"/>'.format(cx,cy,opa))
    # bg buildings
    for bx, bw, bh in buildings_bg:
        parts.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#0c0c14" opacity="0.8"/>'.format(bx,height-bh,bw,bh))
    for i,(bx,bw,bh) in enumerate(buildings_bg):
        parts.append(windows(bx,bw,bh,height-bh,"bg{}".format(i),"hsl({},60%,55%)".format(h1)))
    # mg buildings
    for bx, bw, bh in buildings_mg:
        parts.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#080810" opacity="0.95"/>'.format(bx,height-bh,bw,bh))
    for i,(bx,bw,bh) in enumerate(buildings_mg):
        parts.append(windows(bx,bw,bh,height-bh,"mg{}".format(i),"hsl({},70%,60%)".format(h2)))
    # neon lines
    for i,(bx,bw,bh) in enumerate(buildings_mg):
        if _hash("{}neon{}".format(seed,i), 3) == 0:
            col = accent1 if i%2==0 else accent2
            parts.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="1.5" opacity="0.7" filter="url(#glow)"/>'.format(bx,height-bh,bx+bw,height-bh,col))
    # rain
    for i in range(60):
        rx = _hash("{}rx{}".format(seed,i), width)
        ry = _hash("{}ry{}".format(seed,i), height)
        rl = 8 + _hash("{}rl{}".format(seed,i), 18)
        parts.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#{:02x}ccff" stroke-width="0.5" opacity="0.18"/>'.format(rx,ry,rx-2,ry+rl,h1))
    # signs
    sign_texts = [project_name[:10].upper(), "CORP", "NET", "SYS", "DATA", "AI", "NEXUS", "GRID"]
    for i in range(4):
        sx    = int(width  * (0.05 + i*0.22 + _hash("{}sx{}".format(seed,i), 10)/100))
        sy    = int(height * (0.20  + _hash("{}sy{}".format(seed,i), 30)/100))
        txt   = sign_texts[i % len(sign_texts)]
        col   = accent1 if i%2==0 else accent2
        fsize = 9 + _hash("{}sf{}".format(seed,i), 6)
        parts.append('<text x="{}" y="{}" font-family="monospace" font-size="{}" fill="{}" opacity="0.9" filter="url(#glow)">{}</text>'.format(sx,sy,fsize,col,txt))
    # ground
    parts.append('<rect x="0" y="{}" width="{}" height="20" fill="#020208" opacity="0.95"/>'.format(height-20, width))
    # reflections
    for i in range(8):
        rlx = _hash("{}refl{}".format(seed,i), width)
        rw  = _hash("{}rw{}".format(seed,i),   80) - 40
        rth = 0.5 + _hash("{}rth{}".format(seed,i), 15)/10
        parts.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="{:.1f}" opacity="0.25"/>'.format(rlx,height,rlx+rw,height-12,glow1,rth))
    # fog
    parts.append('<rect x="0" y="{}" width="{}" height="30" fill="url(#sky)" opacity="0.5"/>'.format(height-30, width))
    # fg buildings
    for bx,bw,bh in buildings_fg:
        parts.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#040408"/>'.format(bx,height-bh,bw,bh))
    # project tag
    tag_w = min(len(project_name)*8+20, 220)
    pname_upper = project_name.upper()[:24]
    parts.append('<rect x="12" y="{}" width="{}" height="22" fill="#000" opacity="0.8" rx="3"/>'.format(height-36, tag_w))
    parts.append('<text x="22" y="{}" font-family="monospace" font-size="11" fill="{}" opacity="0.9" filter="url(#glow)">{}</text>'.format(height-20, glow1, pname_upper))

    inner = "\n  ".join(parts)
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="border-radius:10px;display:block">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#020408"/>
      <stop offset="60%" stop-color="#04080f"/>
      <stop offset="100%" stop-color="#060210"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  {inner}
</svg>""".format(w=width, h=height, inner=inner)
