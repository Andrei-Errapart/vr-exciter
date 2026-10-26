"""Build a dimension drawing (SVG) of the SimpleFOC Mini v1.0 from its Gerber outline + drill file."""
import re, sys, math
gko, drl, out = sys.argv[1:4]

# --- outline: FSLAX45Y45, mm; segments (G01) and CCW arcs (G03, I/J relative to start)
segs = []          # ('L', x0,y0,x1,y1) or ('A', cx,cy,r,a0,a1)  (y flipped so +y is down in SVG later)
cur = None; mode = 'G01'
for line in open(gko):
    line = line.strip()
    if line.startswith('G01'): mode = 'G01'; continue
    if line.startswith('G03'): mode = 'G03'
    m = re.match(r'(?:G0[13])?X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D0([12])\*', line)
    if not m: continue
    x, y = int(m[1]) / 1e5, int(m[2]) / 1e5
    if m[5] == '2': cur = (x, y); continue
    if mode == 'G03' and m[3] is not None:
        cx, cy = cur[0] + int(m[3]) / 1e5, cur[1] + int(m[4]) / 1e5
        r = math.hypot(cur[0] - cx, cur[1] - cy)
        a0 = math.atan2(cur[1] - cy, cur[0] - cx); a1 = math.atan2(y - cy, x - cx)
        while a1 <= a0: a1 += 2 * math.pi
        segs.append(('A', cx, cy, r, a0, a1))
    else:
        segs.append(('L', cur[0], cur[1], x, y))
    cur = (x, y)

pts = []
for s in segs:
    if s[0] == 'L': pts += [(s[1], s[2]), (s[3], s[4])]
    else:
        _, cx, cy, r, a0, a1 = s
        pts += [(cx + r * math.cos(a0 + (a1 - a0) * k / 64), cy + r * math.sin(a0 + (a1 - a0) * k / 64)) for k in range(65)]
xmin = min(p[0] for p in pts); xmax = max(p[0] for p in pts)
ymin = min(p[1] for p in pts); ymax = max(p[1] for p in pts)

# --- drill: METRIC 3:3
holes = []; tools = {}; t = None
for line in open(drl):
    line = line.strip()
    m = re.match(r'T(\d+)C([\d.]+)', line)
    if m: tools[m[1]] = float(m[2]); continue
    m = re.match(r'T(\d+)$', line)
    if m: t = m[1]; continue
    m = re.match(r'X(-?\d+)Y(-?\d+)', line)
    if m and t: holes.append((int(m[1]) / 1e3, int(m[2]) / 1e3, tools[t]))
holes = [h for h in holes if h[2] > 0.5]   # skip vias

# board frame: origin = bottom-left of bounding box, +x right, +y up
def B(x, y): return (x - xmin, y - ymin)
W, H = xmax - xmin, ymax - ymin
mount = sorted([B(x, y) for x, y, d in holes if d >= 1.9])
hdr = sorted([B(x, y) for x, y, d in holes if abs(d - 1.101) < 0.01 and x < 12])
pwr = sorted([B(x, y) for x, y, d in holes if abs(d - 1.101) < 0.01 and x > 12], key=lambda p: -p[1])
mot = sorted([B(x, y) for x, y, d in holes if abs(d - 1.021) < 0.01])
print(f'outline bbox {W:.2f} x {H:.2f} mm')
print('mounting holes (d=2.0):', [(round(x, 2), round(y, 2)) for x, y in mount])
print('2x5 header:', [(round(x, 2), round(y, 2)) for x, y in hdr])
print('power +/-:', [(round(x, 2), round(y, 2)) for x, y in pwr])
print('motor M1..M3:', [(round(x, 2), round(y, 2)) for x, y in mot])

# --- SVG (1 mm = 20 px), y flipped
S = 20; M = 70
def P(x, y): return (M + x * S, M + (H - y) * S)
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*S+2*M+300:.0f}" height="{H*S+2*M+60:.0f}" font-family="Helvetica,Arial,sans-serif" font-size="13">',
     '<rect width="100%" height="100%" fill="white"/>']
for s in segs:
    if s[0] == 'L':
        a, b = P(*B(s[1], s[2])), P(*B(s[3], s[4]))
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="black" stroke-width="2"/>')
    else:
        _, cx, cy, r, a0, a1 = s
        p = [P(*B(cx + r * math.cos(a0 + (a1 - a0) * k / 32), cy + r * math.sin(a0 + (a1 - a0) * k / 32))) for k in range(33)]
        o.append('<polyline fill="none" stroke="black" stroke-width="2" points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in p) + '"/>')
def circ(x, y, d, col):
    c = P(x, y); o.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{d/2*S:.1f}" fill="none" stroke="{col}" stroke-width="1.5"/>')
def text(x, y, s, anchor='middle', col='black', size=13):
    o.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{col}" font-size="{size}">{s}</text>')
for x, y in mount: circ(x, y, 2.0, 'black')
hdr_labels = {}
top = [p for p in hdr if p[1] > sum(q[1] for q in hdr) / len(hdr)]; bot = [p for p in hdr if p not in top]
for (x, y), n in zip(sorted(top), ['EN', 'IN3', 'IN2', 'IN1', 'GND']):
    circ(x, y, 1.1, '#1565c0'); c = P(x, y); text(c[0], c[1] - 18, n, col='#1565c0', size=11)
for (x, y), n in zip(sorted(bot), ['nFT', 'nSP', 'nRT', 'GND', '3V3']):
    circ(x, y, 1.1, '#c62828'); c = P(x, y); text(c[0], c[1] + 28, n, col='#c62828', size=11)
for (x, y), n in zip(pwr, ['−', '+']):
    circ(x, y, 1.1, '#2e7d32'); c = P(x, y); text(c[0] - 22, c[1] + 5, n, col='#2e7d32', size=16)
for (x, y), n in zip(sorted(mot), ['M1', 'M2', 'M3']):
    circ(x, y, 1.0, '#6a1b9a'); c = P(x, y); text(c[0], c[1] - 16, n, col='#6a1b9a', size=11)
# square pad marker: GND (H1 pin 1) is the right-hand pin of the top row
gx, gy = P(*sorted(top)[-1]); o.append(f'<rect x="{gx-12:.1f}" y="{gy-12:.1f}" width="24" height="24" fill="none" stroke="#1565c0"/>')
# dimensions
def dim_h(x0, x1, yy, label):
    a, b = P(x0, 0), P(x1, 0)
    o.append(f'<line x1="{a[0]:.1f}" y1="{yy}" x2="{b[0]:.1f}" y2="{yy}" stroke="#555" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    text((a[0] + b[0]) / 2, yy - 6, label)
def dim_v(y0, y1, xx, label):
    a, b = P(0, y0), P(0, y1)
    o.append(f'<line x1="{xx}" y1="{a[1]:.1f}" x2="{xx}" y2="{b[1]:.1f}" stroke="#555" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    o.append(f'<text x="{xx+8}" y="{(a[1]+b[1])/2+4:.1f}" font-size="13">{label}</text>')
o.insert(2, '<defs><marker id="ar" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,2 L10,5 L0,8 z" fill="#555"/></marker></defs>')
ml = [p for p in mount if p[0] < W / 2]; mr = [p for p in mount if p[0] > W / 2]
dim_h(0, W, M - 40, f'{W:.2f} mm overall')
dim_h(ml[0][0], mr[0][0], M + H * S + 30, f'{mr[0][0]-ml[0][0]:.2f} mm hole spacing')
dim_v(0, H, M + W * S + 20, f'{H:.2f} mm')
dim_v(min(p[1] for p in mr), max(p[1] for p in mr), M + W * S + 110, f'{max(p[1] for p in mr)-min(p[1] for p in mr):.2f} (right)')
dim_v(min(p[1] for p in ml), max(p[1] for p in ml), M + W * S + 190, f'{max(p[1] for p in ml)-min(p[1] for p in ml):.2f} (left)')
text(M, M + H * S + 60, 'SimpleFOC Mini v1.0, top view (component side). Generated from Gerber_BoardOutlineLayer.GKO + Drill_PTH_Through.DRL.', anchor='start', size=11)
text(M, M + H * S + 76, 'Holes: mounting Ø2.0 (for M2), header and power Ø1.1, motor Ø1.0; header pitch 2.54 mm. Square pad = H1 pin 1 (GND).', anchor='start', size=11)
o.append('</svg>')
open(out, 'w').write('\n'.join(o))
