"""Short vertical 1080x1920 : personnage cartoon original (inspiré de la photo fournie),
scènes originales au format "playback flat", instru originale synthétisée.
Usage : python3 render.py OUT_DIR [--preview]"""
import cairo, math, random, sys, wave, subprocess, os
import numpy as np

W, H, FPS = 1080, 1920, 30
BPM = 120; BEAT = 60 / BPM; DUR = 34.0
NF = int(DUR * FPS)
OUT = sys.argv[1]
PREVIEW = "--preview" in sys.argv

# Sous-titres provisoires (originaux) : remplace-les par tes propres textes autorisés.
CAPTIONS = ["Minuit, la ville se tait", "Moi j'écris jusqu'à l'aube", "Un pas après l'autre",
            "Hier personne… ce soir la foule", "Le travail finit par payer", "À suivre…"]

# ---------------------------------------------------------------- helpers
def hx(h, a=1.0):
    h = h.lstrip('#'); return (int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255, a)
def col(c, h, a=1.0): c.set_source_rgba(*hx(h, a))
def rrect(c, x, y, w, h, r):
    r = min(r, w/2, h/2); c.new_sub_path()
    c.arc(x+w-r, y+r, r, -math.pi/2, 0); c.arc(x+w-r, y+h-r, r, 0, math.pi/2)
    c.arc(x+r, y+h-r, r, math.pi/2, math.pi); c.arc(x+r, y+r, r, math.pi, 1.5*math.pi); c.close_path()
def ell(c, cx, cy, rx, ry):
    c.save(); c.translate(cx, cy); c.scale(rx, ry); c.new_sub_path(); c.arc(0, 0, 1, 0, 2*math.pi); c.restore()
def sky(c, stops, y0=0, y1=H):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for o, h in stops: g.add_color_stop_rgba(o, *hx(h))
    c.set_source(g); c.paint()
def ease(t): t = max(0.0, min(1.0, t)); return t*t*(3-2*t)
def line(c, pts, w, h, a=1.0, cap=cairo.LINE_CAP_ROUND):
    c.set_line_width(w); c.set_line_cap(cap); c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    col(c, h, a); c.stroke()
def glow(c, x, y, r, h, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *hx(h, a)); g.add_color_stop_rgba(1, *hx(h, 0))
    c.set_source(g); c.arc(x, y, r, 0, 2*math.pi); c.fill()
def note(c, x, y, s, h, a):
    col(c, h, a); ell(c, x, y, 13*s, 9*s); c.fill()
    line(c, [(x+11*s, y), (x+11*s, y-42*s), (x+26*s, y-32*s)], 4*s, h, a)

# ---------------------------------------------------------------- audio (instru originale)
SR = 44100
def mf(m): return 440 * 2 ** ((m - 69) / 12)
def synth():
    n = int(DUR * SR); out = np.zeros(n); drums = np.zeros(n)
    rng = np.random.default_rng(7)
    def add(buf, sig, start, amp=1.0):
        i = int(start * SR)
        if i >= n: return
        j = min(n, i + len(sig)); buf[i:j] += amp * sig[:j-i]
    t = np.arange(int(0.45*SR))/SR
    kick = np.sin(2*np.pi*(48*t + 110/22*(1-np.exp(-22*t)))) * np.exp(-t*6)
    ts = np.arange(int(0.25*SR))/SR
    nz = np.diff(rng.standard_normal(len(ts)), prepend=0)
    snare = 0.5*nz*np.exp(-ts*16) + 0.6*np.sin(2*np.pi*190*ts)*np.exp(-ts*25)
    th = np.arange(int(0.06*SR))/SR
    hat = np.diff(np.diff(rng.standard_normal(len(th)), prepend=0), prepend=0)*np.exp(-th*70)*0.07
    chords = [[60, 63, 67], [56, 60, 63], [55, 58, 63], [58, 62, 65]]   # Cm Ab Eb Bb
    roots = [36, 32, 39, 34]
    bars = int(DUR / (4*BEAT))
    e8 = BEAT/2
    for b in range(bars):
        t0 = b*4*BEAT; ch = chords[b % 4]; rt = roots[b % 4]
        # pad
        tp = np.arange(int(4*BEAT*SR))/SR
        env = np.minimum(1, tp/0.3) * np.minimum(1, (4*BEAT - tp)/0.4)
        pad = sum(np.sin(2*np.pi*mf(m)*tp*d) + 0.25*np.sin(4*np.pi*mf(m)*tp*d)
                  for m in ch for d in (1.0, 1.004))
        add(out, pad*env, t0, 0.025)
        # cloche / arpège
        if b < bars - 1:
            for k, idx in enumerate([0, 2, 1, 2, 0, 2, 1, 0]):
                tb = np.arange(int(0.6*SR))/SR; f = mf(ch[idx] + 12)
                bell = np.sin(2*np.pi*f*tb)*np.exp(-tb*6) + 0.3*np.sin(2*np.pi*2.76*f*tb)*np.exp(-tb*10)
                add(out, bell, t0 + k*e8, 0.05)
        full = 1 <= b <= bars - 3
        if full or b == bars - 2:
            for k in (0, 3, 5): add(drums, kick, t0 + k*e8, 0.9)
        if full:
            for k in (2, 6): add(drums, snare, t0 + k*e8, 0.55)
            for k in range(8):
                if k == 7 and b % 2 == 1:
                    for r in range(3): add(drums, hat, t0 + k*e8 + r*e8/3, 1.0)
                else: add(drums, hat, t0 + k*e8, 1.0 if k % 2 == 0 else 0.6)
            for k in (0, 5):   # 808
                tb = np.arange(int(1.0*SR))/SR
                b8 = np.tanh(2.2*np.sin(2*np.pi*mf(rt)*tb))*np.exp(-tb*2.2)
                add(out, b8, t0 + k*e8, 0.28)
    mix = out + drums
    mix /= np.max(np.abs(mix)) / 0.89
    fade = int(1.2*SR); mix[-fade:] *= np.linspace(1, 0, fade)
    pcm = (np.clip(mix, -1, 1)*32767).astype(np.int16)
    with wave.open(os.path.join(OUT, "beat.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
    spf = SR // FPS
    envs = np.array([np.sqrt(np.mean(drums[f*spf:(f+1)*spf]**2) + 1e-9) for f in range(NF)])
    return envs / envs.max()

# ---------------------------------------------------------------- personnage
SKIN, SKIN_D, HAIR = '#6b4430', '#53331f', '#170e0a'
JACKET, JK_EDGE, SILVER = '#7a1630', '#4a0c1d', '#c4c8d0'
GOLD, ORANGE, CREAM = '#e2b84a', '#f08a2a', '#f3efe8'
def cuff(c, el, hd):
    dx, dy = hd[0]-el[0], hd[1]-el[1]
    for fr0, fr1, cc in ((0.62, 0.9, CREAM), (0.66, 0.70, ORANGE), (0.73, 0.76, '#5a0f22'), (0.79, 0.83, ORANGE)):
        line(c, [(el[0]+dx*fr0, el[1]+dy*fr0), (el[0]+dx*fr1, el[1]+dy*fr1)], 64, cc, 1, cairo.LINE_CAP_BUTT)
def zipstripe(c, p0, p1, sd):
    for o, cc in ((0, CREAM), (7, ORANGE), (14, CREAM), (21, '#5a0f22')):
        line(c, [(p0[0]+sd*o, p0[1]), (p1[0]+sd*o, p1[1])], 7, cc, 1, cairo.LINE_CAP_BUTT)

def staff(c, p0, p1, a=0.85):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; L = math.hypot(dx, dy) or 1
    ux, uy = dx/L, dy/L; nx, ny = -uy, ux
    for k in range(5):
        o = (k-2)*6
        a0 = (p0[0]+ux*L*0.12+nx*o, p0[1]+uy*L*0.12+ny*o)
        a1 = (p0[0]+ux*L*0.88+nx*o, p0[1]+uy*L*0.88+ny*o)
        line(c, [a0, a1], 1.6, SILVER, a*0.8, cairo.LINE_CAP_BUTT)
    for j, (fr, o) in enumerate([(0.3, -6), (0.5, 3), (0.7, -3)]):
        x, y = p0[0]+ux*L*fr+nx*o, p0[1]+uy*L*fr+ny*o
        col(c, SILVER, a); ell(c, x, y, 4.5, 3.5); c.fill()
        line(c, [(x+4, y), (x+4+nx*-14, y+ny*-14)], 1.6, SILVER, a)

def rapper(c, x, y, s, pose='idle', t=0.0, talk=0.0, phones=False, walk=0.0, nod=0.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    col(c, '#000000', 0.28); ell(c, 0, 4, 160, 22); c.fill()
    bob = 7*nod
    # jambes + baskets
    sw = math.sin(walk*2*math.pi)
    if pose == 'walk':
        fl = (-55+30*sw, -max(0, 26*sw)); fr = (55-30*sw, -max(0, -26*sw)); bob = 8*abs(sw)
    else:
        fl, fr = (-58, 0), (58, 0)
    for hip, f, sd in (((-48, -265+bob), fl, -1), ((48, -265+bob), fr, 1)):
        knee = ((hip[0]+f[0])/2 + 6*sd, (hip[1]+f[1])/2)
        line(c, [hip, knee, (f[0], f[1]-30)], 78, '#0c0c10')
        line(c, [hip, knee, (f[0], f[1]-30)], 72, '#15151b')
        col(c, '#f4f4f6'); rrect(c, f[0]-52, f[1]-36, 104, 38, 17); c.fill()
        col(c, '#cfd2d8'); rrect(c, f[0]-52, f[1]-12, 104, 13, 6); c.fill()
        line(c, [(f[0]-18*sd, f[1]-26), (f[0]+20*sd, f[1]-18)], 4, '#9aa0aa')
    c.save(); c.translate(0, bob)
    # buste : bomber
    c.move_to(-138, -448); c.line_to(138, -448)
    c.curve_to(154, -380, 144, -300, 124, -258); c.line_to(-124, -258)
    c.curve_to(-144, -300, -154, -380, -138, -448); c.close_path()
    col(c, JACKET); c.fill_preserve(); col(c, JK_EDGE); c.set_line_width(4); c.stroke()
    col(c, '#9a2442', 0.6); ell(c, -82, -385, 22, 46); c.fill()
    # t-shirt noir + chaîne en or
    c.move_to(-50, -454); c.line_to(50, -454); c.line_to(42, -262); c.line_to(-42, -262); c.close_path()
    col(c, '#0b0b0d'); c.fill()
    for sd in (-1, 1): zipstripe(c, (sd*52, -452), (sd*44, -262), sd)
    c.move_to(-40, -456); c.curve_to(-34, -380, 34, -380, 40, -456)
    c.set_line_width(7); col(c, '#9c7a24'); c.stroke()
    c.set_dash([7, 4]); c.move_to(-40, -456); c.curve_to(-34, -380, 34, -380, 40, -456)
    c.set_line_width(5); col(c, GOLD); c.stroke(); c.set_dash([])
    col(c, '#5a0f22'); rrect(c, -126, -288, 252, 32, 9); c.fill()
    for yy, cc in ((-283, CREAM), (-276, ORANGE), (-269, CREAM)):
        line(c, [(-122, yy), (122, yy)], 4, cc, 1, cairo.LINE_CAP_BUTT)
    # bras
    talkw = math.sin(t*9)
    pos = {}
    for sd in (-1, 1):
        sh = (sd*130, -432)
        el, hd = (sd*152, -348), (sd*142, -262 + 4*math.sin(t*2 + sd))
        if pose == 'walk': el, hd = (sd*150, -348), (sd*140, -262 + 16*sw*sd)
        if pose == 'listen' and sd == -1: el, hd = (-200, -500), (-118, -590)
        if pose == 'rap' and sd == 1: el, hd = (192, -372), (150 + 8*talkw, -470 - 22*nod)
        if pose == 'peace': el, hd = (sd*205, -380), (sd*118, -470)
        if pose == 'raise' and sd == 1: el, hd = (196, -560), (182 + 6*math.sin(t*5), -690)
        pos[sd] = (sh, el, hd)
    for sd in (-1, 1):
        sh, el, hd = pos[sd]
        line(c, [sh, el, hd], 68, JK_EDGE); line(c, [sh, el, hd], 62, JACKET)
        cuff(c, el, hd)
        hy = hd[1] - (8 if hd[1] < -400 else -8)
        if pose == 'peace':
            for fx in (-14, 12): line(c, [(hd[0], hy), (hd[0] + fx - sd*22, hy - 70)], 14, SKIN)
        col(c, SKIN); c.arc(hd[0], hy, 25, 0, 2*math.pi); c.fill()
        col(c, GOLD); c.set_line_width(5); c.arc(hd[0] - 6*sd, hy - 14, 8, 0, 2*math.pi); c.stroke()
        if sd < 0: col(c, '#2a4fd0'); c.arc(hd[0] + 6, hy - 18, 5, 0, 2*math.pi); c.fill()
    # col rayé
    col(c, '#5a0f22'); rrect(c, -66, -468, 132, 26, 12); c.fill()
    for yy, cc in ((-462, CREAM), (-455, ORANGE), (-448, CREAM)):
        line(c, [(-58, yy), (58, yy)], 4, cc)
    # tête
    c.save(); c.translate(0, -470); c.rotate(0.035*math.sin(t*1.3)); c.translate(0, 470 + 8*nod)
    c.translate(0, 0)
    col(c, SKIN_D); rrect(c, -31, -510, 62, 58, 12); c.fill()
    for sd in (-1, 1):
        col(c, SKIN); ell(c, sd*90, -572, 16, 24); c.fill()
        col(c, SKIN_D); ell(c, sd*92, -572, 7, 13); c.fill()
    col(c, SKIN); ell(c, 0, -578, 97, 104); c.fill()
    col(c, SKIN_D, 0.45); ell(c, 0, -500, 62, 18); c.fill()
    # casquette beige à motif générique
    c.save(); c.translate(0, -610); c.rotate(-0.07)
    c.save(); c.move_to(-104, 2); c.curve_to(-104, -120, 104, -120, 104, 2); c.close_path(); c.clip()
    col(c, '#cdb38c'); c.paint()
    for yy in range(-110, 10, 18):
        for xx in range(-110, 112, 22):
            ox = 11 if (yy//18) % 2 else 0
            col(c, '#9b7f58', 0.75); c.move_to(xx+ox, yy-6); c.line_to(xx+ox+6, yy); c.line_to(xx+ox, yy+6); c.line_to(xx+ox-6, yy); c.close_path(); c.fill()
    line(c, [(0, -95), (0, 2)], 3, '#a88d63')
    c.restore()
    col(c, '#b89a70'); c.arc(0, -92, 7, 0, 2*math.pi); c.fill()
    col(c, '#000000', 0.25); ell(c, 0, 16, 98, 12); c.fill()
    col(c, '#c2a67d'); ell(c, 0, 4, 116, 20); c.fill()
    col(c, '#a88d63'); c.set_line_width(3); ell(c, 0, 4, 116, 20); c.stroke()
    c.restore()
    # lunettes de soleil octogonales dorées
    for sd in (-1, 1):
        cx, cy = sd*43, -580
        pts = [(-24, -27), (24, -27), (37, -12), (37, 12), (24, 25), (-24, 25), (-37, 12), (-37, -12)]
        c.move_to(cx+pts[0][0], cy+pts[0][1])
        for px, py in pts[1:]: c.line_to(cx+px, cy+py)
        c.close_path()
        g = cairo.LinearGradient(0, cy-27, 0, cy+25)
        g.add_color_stop_rgba(0, *hx('#16161d')); g.add_color_stop_rgba(0.55, *hx('#3a3c4a'))
        g.add_color_stop_rgba(1, *hx('#8e93a8'))
        c.set_source(g); c.fill_preserve(); c.set_line_width(5); col(c, GOLD); c.stroke()
        c.move_to(cx-22, cy+4); c.curve_to(cx-10, cy-6, cx+10, cy-6, cx+24, cy+6)
        c.set_line_width(4); col(c, '#ffffff', 0.55); c.stroke()
        line(c, [(sd*80, -590), (sd*98, -582)], 4, GOLD)
    line(c, [(-6, -596), (6, -596)], 4, GOLD); line(c, [(-8, -586), (8, -586)], 3, GOLD)
    col(c, SKIN_D); ell(c, 0, -547, 22, 12); c.fill()
    for sd in (-1, 1): col(c, '#2a170e'); ell(c, sd*9, -543, 5, 3); c.fill()
    c.move_to(-26, -528); c.curve_to(-10, -533, 10, -533, 26, -528)
    c.set_line_width(4); col(c, HAIR, 0.7); c.stroke()
    col(c, '#5a3324'); ell(c, 0, -517, 29, 8); c.fill()
    if talk > 0.05:
        col(c, '#2a0f0a'); ell(c, 0, -511, 18, 3 + talk*8); c.fill()
    col(c, '#8a5240'); ell(c, 0, -504 + talk*5, 28, 11); c.fill()
    col(c, HAIR, 0.55); c.move_to(-18, -488); c.curve_to(-20, -470, 20, -470, 18, -488)
    c.curve_to(8, -484, -8, -484, -18, -488); c.close_path(); c.fill()
    if phones:
        c.new_sub_path(); c.arc(0, -586, 116, math.pi*1.06, math.pi*1.94)
        c.set_line_width(16); col(c, '#e8e8ee'); c.stroke()
        for sd in (-1, 1):
            col(c, '#f5f5f7'); rrect(c, sd*108-18, -620, 36, 72, 16); c.fill()
            col(c, '#4fc3f7'); rrect(c, sd*108-18 + (0 if sd < 0 else 22), -610, 14, 52, 7); c.fill()
    c.restore(); c.restore(); c.restore()

# ---------------------------------------------------------------- décors
def make_city(seed, x0, x1, hmin, hmax, wmin, wmax):
    r = random.Random(seed); out = []; x = x0
    while x < x1:
        w = r.randint(wmin, wmax); out.append((x, w, r.randint(hmin, hmax), r.random())); x += w + r.randint(0, 12)
    return out
def draw_city(c, city, base, fill, win, prob, scroll=0.0, period=None):
    for (x, w, h, sd) in city:
        xx = x - scroll
        if period: xx = ((xx + 400) % period) - 400
        if xx > W or xx + w < 0: continue
        col(c, fill); c.rectangle(xx, base-h, w, h+2); c.fill()
        r = random.Random(int(sd*1e6))
        for yy in range(int(base-h+18), int(base-20), 34):
            for wx in range(int(xx+12), int(xx+w-18), 26):
                if r.random() < prob: col(c, win, 0.85); c.rectangle(wx, yy, 12, 16); c.fill()

CITY_FAR = make_city(1, -400, 1500, 300, 650, 90, 170)
CITY_NEAR = make_city(2, -400, 1500, 150, 420, 110, 200)
CITY_W1 = make_city(3, -400, 1800, 350, 700, 100, 180)
CITY_W2 = make_city(4, -400, 1800, 250, 520, 140, 240)
rs = random.Random(9)
STARS = [(rs.uniform(0, W), rs.uniform(0, 1000), rs.uniform(1.5, 3.5)) for _ in range(90)]
CONF = [(rs.uniform(0, W), rs.uniform(0, 2000), rs.uniform(250, 520), rs.choice(['#ffd54a', '#ff5fa2', '#4fc3f7', '#ffffff', '#7c5cff']), rs.uniform(0, 6), rs.uniform(-6, 6)) for _ in range(140)]
CROWD = [(rs.uniform(-40, 1120), rs.uniform(0, 1), rs.random() < 0.45, rs.uniform(0.8, 1.15)) for _ in range(26)]

def sc_roof(c, lt, gt, I, sunrise=False):
    z = 1 + 0.05*(lt/6)
    c.save(); c.translate(540, 1200); c.scale(z, z); c.translate(-540, -1200)
    if sunrise:
        sky(c, [(0, '#2a2f78'), (0.45, '#c86a8e'), (0.72, '#ffb27a'), (1, '#ffd9a0')])
        sy = 1250 - 330*ease(lt/3.5); glow(c, 300, sy, 330, '#ffe3a0', 0.6)
        col(c, '#fff0c0'); c.arc(300, sy, 110, 0, 2*math.pi); c.fill()
        far, near, roof = '#7a4a7e', '#4b2c5c', '#3a2a4f'
    else:
        sky(c, [(0, '#070a22'), (0.55, '#231b55'), (1, '#5a3a86')])
        for i, (sx, sy, sr) in enumerate(STARS):
            col(c, '#ffffff', 0.35 + 0.6*abs(math.sin(gt*1.7 + i))); c.arc(sx, sy, sr, 0, 2*math.pi); c.fill()
        glow(c, 860, 650, 220, '#f4f0d8', 0.35)
        col(c, '#f4f0d8'); c.arc(860, 650, 70, 0, 2*math.pi); c.fill()
        col(c, '#dcd6bc'); c.arc(838, 632, 14, 0, 2*math.pi); c.fill(); c.arc(880, 672, 9, 0, 2*math.pi); c.fill()
        far, near, roof = '#2a2150', '#18132f', '#1e1a33'
    draw_city(c, CITY_FAR, 1360, far, '#ffd76a', 0.2)
    draw_city(c, CITY_NEAR, 1450, near, '#ffc35a', 0.3)
    col(c, roof); c.rectangle(-100, 1440, W+200, 600); c.fill()
    col(c, '#2d2850' if not sunrise else '#5a4070'); c.rectangle(-100, 1440, W+200, 36); c.fill()
    # château d'eau + antenne
    col(c, '#141026' if not sunrise else '#2f2040')
    rrect(c, 840, 1190, 150, 170, 20); c.fill(); c.rectangle(860, 1360, 14, 80); c.fill(); c.rectangle(956, 1360, 14, 80); c.fill()
    line(c, [(150, 1440), (150, 1180)], 8, '#141026'); line(c, [(110, 1250), (190, 1250)], 6, '#141026')
    col(c, '#ff4a4a', 0.5 + 0.5*math.sin(gt*4)); c.arc(150, 1175, 8, 0, 2*math.pi); c.fill()
    rapper(c, 540, 1470, 1.4, 'listen' if not sunrise else 'peace', gt, 0, not sunrise, nod=I['nod']*0.6)
    if not sunrise:
        for i in range(7):
            ph = (gt*0.33 + i/7) % 1; sd = 1 if i % 2 else -1
            note(c, 540 + sd*(230 + 50*math.sin(gt + i)), 900 - ph*520, 1.3, '#9fd8ff', math.sin(math.pi*ph))
    c.restore()

def sc_studio(c, lt, gt, I):
    col(c, '#1a1730'); c.paint()
    for gy, y in enumerate(range(160, 1440, 90)):
        for gx, x in enumerate(range(0, W, 90)):
            a, b = ('#221e3c', '#14122a') if (gx+gy) % 2 else ('#14122a', '#221e3c')
            col(c, a); c.move_to(x, y); c.line_to(x+90, y); c.line_to(x, y+90); c.fill()
            col(c, b); c.move_to(x+90, y); c.line_to(x+90, y+90); c.line_to(x, y+90); c.fill()
    col(c, '#0f0d1c'); c.rectangle(0, 1420, W, 600); c.fill()
    col(c, '#2b1f3f'); ell(c, 600, 1470, 330, 60); c.fill()
    # écran waveform
    col(c, '#06050e'); rrect(c, 80, 560, 420, 250, 18); c.fill()
    col(c, '#3a3460'); c.set_line_width(5); rrect(c, 80, 560, 420, 250, 18); c.stroke()
    for i in range(24):
        h = 16 + I['env']*170*(0.35 + 0.65*abs(math.sin(i*1.7 + gt*9)))
        g = cairo.LinearGradient(0, 685-h/2, 0, 685+h/2)
        g.add_color_stop_rgba(0, *hx('#4fc3f7')); g.add_color_stop_rgba(1, *hx('#7c5cff'))
        c.set_source(g); rrect(c, 104 + i*16.5, 685-h/2, 10, h, 5); c.fill()
    # néon
    for w_, a in ((22, 0.12), (12, 0.25), (5, 1.0)):
        c.set_line_width(w_); col(c, '#ff4fa3', a); rrect(c, 640, 560, 330, 150, 40); c.stroke()
    for i in range(3):
        note(c, 720 + i*80, 660 - 15*math.sin(gt*4 + i), 1.4, '#ff8ac6', 0.95)
    col(c, '#ff3b3b', 0.35 + 0.65*I['nod']); c.arc(940, 470, 18, 0, 2*math.pi); c.fill()
    talk = min(1, I['env']*1.4)*abs(math.sin(gt*13))
    rapper(c, 640, 1460, 1.35, 'rap', gt, talk, False, nod=I['nod'])
    # micro sur pied, devant
    line(c, [(420, 1460), (430, 900), (520, 812)], 10, '#2a2a33')
    for dx in (-60, 60): line(c, [(430, 1400), (430+dx, 1462)], 8, '#2a2a33')
    c.save(); c.translate(522, 800); c.rotate(-0.45)
    col(c, '#b9bec8'); rrect(c, -28, -78, 56, 116, 28); c.fill()
    for k in range(-60, 20, 12): line(c, [(-22, k), (22, k)], 2, '#7d828c')
    c.restore()
    col(c, '#ffffff', 0.12); c.arc(575, 790, 48, 0, 2*math.pi); c.fill()
    col(c, '#ffffff', 0.35); c.set_line_width(4); c.arc(575, 790, 48, 0, 2*math.pi); c.stroke()

def sc_walk(c, lt, gt, I):
    sky(c, [(0, '#4a2a7a'), (0.5, '#d9607a'), (0.78, '#ffb070'), (1, '#ffd29a')], 0, 1400)
    glow(c, 760, 1060, 330, '#ffe1a0', 0.55)
    col(c, '#ffe7b0'); c.arc(760, 1060, 125, 0, 2*math.pi); c.fill()
    draw_city(c, CITY_W1, 1300, '#7a3f78', '#ffd27a', 0.12, lt*60, 2200)
    draw_city(c, CITY_W2, 1400, '#3a1e4c', '#ffc35a', 0.28, lt*190, 2200)
    col(c, '#2a2038'); c.rectangle(0, 1380, W, 600); c.fill()
    col(c, '#3d3050'); c.rectangle(0, 1380, W, 22); c.fill()
    for k in range(-1, 9):
        xx = (k*170 - lt*330) % (170*8) - 170
        line(c, [(xx, 1402), (xx - 120, 1920)], 4, '#3a2e4c')
    for k in range(4):
        xx = (k*560 - lt*330) % (560*3) - 300
        line(c, [(xx, 1390), (xx, 800), (xx+70, 770)], 14, '#1b1428')
        glow(c, xx+80, 790, 200, '#ffe08a', 0.35)
        col(c, '#ffe9a8'); ell(c, xx+80, 782, 30, 12); c.fill()
    rapper(c, 540, 1500, 1.3, 'walk', gt, 0, False, walk=gt/(2*BEAT))

def sc_stage(c, lt, gt, I):
    col(c, '#0c0918'); c.paint()
    for gy, y in enumerate(range(120, 1300, 44)):
        for gx, x in enumerate(range(20, W, 44)):
            lit = (math.sin(gx*0.5 + gy*0.3 + gt*3) > 0.6)
            col(c, '#7c5cff' if lit else '#231a40', (0.3 + 0.7*I['env']) if lit else 1)
            c.arc(x, y, 8, 0, 2*math.pi); c.fill()
    col(c, '#1a1430'); c.rectangle(0, 1300, W, 700); c.fill()
    col(c, '#2a2048'); c.rectangle(0, 1300, W, 22); c.fill()
    glow(c, 540, 1330, 320, '#fff3c4', 0.35)
    for i, sx in enumerate((160, 540, 920)):
        ang = 0.35*math.sin(gt*1.1 + i*2)
        tx = 540 + math.sin(ang)*900
        g = cairo.LinearGradient(sx, -40, tx, 1330)
        g.add_color_stop_rgba(0, *hx('#fff3c4', 0.35)); g.add_color_stop_rgba(1, *hx('#fff3c4', 0.0))
        c.set_source(g); c.move_to(sx-20, -40); c.line_to(sx+20, -40); c.line_to(tx+170, 1330); c.line_to(tx-170, 1330); c.fill()
    pose = 'rap' if lt < 3 else 'peace'
    talk = min(1, I['env']*1.4)*abs(math.sin(gt*13)) if pose == 'rap' else 0.3
    rapper(c, 540, 1330, 1.25, pose, gt, talk, False, nod=I['nod'])
    for (x, ph, up, s) in CROWD:
        b = 14*I['nod']*(0.6 + 0.4*math.sin(ph*6.28))
        y = 1560 + 120*ph - b
        col(c, '#06050c'); c.arc(x, y, 52*s, 0, 2*math.pi); c.fill()
        rrect(c, x-80*s, y+40*s, 160*s, 400, 50*s); c.fill()
        if up:
            hx_, hy = x + 40*s, y - 210*s - b
            line(c, [(x+50*s, y+60*s), (x+70*s, y-60*s), (hx_, hy)], 34*s, '#06050c')
            glow(c, hx_, hy-30*s, 70*s, '#ffffff', 0.35)
            col(c, '#f6f6ff'); rrect(c, hx_-14*s, hy-56*s, 28*s, 48*s, 6*s); c.fill()

def sc_gold(c, lt, gt, I):
    g = cairo.RadialGradient(540, 760, 50, 540, 760, 1300)
    g.add_color_stop_rgba(0, *hx('#4a2580')); g.add_color_stop_rgba(1, *hx('#120a28'))
    c.set_source(g); c.paint()
    c.save(); c.translate(320, 760); c.rotate(gt*0.25)
    for k in range(18):
        a0 = k*2*math.pi/18
        c.move_to(0, 0); c.arc(0, 0, 1800, a0, a0 + math.pi/18); c.close_path()
        col(c, '#ffcc4a', 0.07); c.fill()
    c.restore()
    col(c, '#1c1238'); c.rectangle(0, 1440, W, 600); c.fill()
    # cadre disque
    k = ease(lt/0.9); py = -500 + k*1260 + 18*math.sin(min(lt, 1.6)*10)*max(0, 1.6-lt)
    c.save(); c.translate(300, py)
    col(c, '#000000', 0.35); rrect(c, -150+10, -195+14, 300, 390, 16); c.fill()
    col(c, '#121018'); rrect(c, -150, -195, 300, 390, 16); c.fill()
    col(c, '#d4a64a'); c.set_line_width(10); rrect(c, -150, -195, 300, 390, 16); c.stroke()
    dg = cairo.RadialGradient(-30, -60, 10, 0, -30, 130)
    dg.add_color_stop_rgba(0, *hx('#fff1a8')); dg.add_color_stop_rgba(1, *hx('#c8901f'))
    c.set_source(dg); c.arc(0, -30, 120, 0, 2*math.pi); c.fill()
    for r in range(55, 120, 9): col(c, '#8a5f10', 0.3); c.set_line_width(1.5); c.arc(0, -30, r, 0, 2*math.pi); c.stroke()
    col(c, '#7c5cff'); c.arc(0, -30, 40, 0, 2*math.pi); c.fill()
    col(c, '#121018'); c.arc(0, -30, 6, 0, 2*math.pi); c.fill()
    col(c, '#d4a64a'); rrect(c, -90, 125, 180, 34, 6); c.fill()
    c.restore()
    rapper(c, 650, 1460, 1.25, 'raise' if lt > 0.8 else 'idle', gt, 0.25, False, nod=I['nod'])
    if lt > 0.6:
        for (x, y0, sp, cc, r0, rv) in CONF:
            y = (y0 + (lt-0.6)*sp) % 2100 - 100
            if y0 + (lt-0.6)*sp < 2000 + 0*y:
                pass
            c.save(); c.translate(x + 30*math.sin(lt*2 + r0), y); c.rotate(r0 + lt*rv)
            col(c, cc, 0.9); c.rectangle(-9, -5, 18, 10); c.fill(); c.restore()

SCENES = [(0, 6, sc_roof), (6, 12, sc_studio), (12, 18, sc_walk), (18, 24, sc_stage), (24, 30, sc_gold),
          (30, 34, lambda c, lt, gt, I: sc_roof(c, lt, gt, I, True))]

def caption(c, text, a, sc):
    if a <= 0: return
    c.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    fs = 58
    while True:
        c.set_font_size(fs); ext = c.text_extents(text)
        if ext.x_advance < 900 or fs < 30: break
        fs -= 2
    w, h = ext.x_advance + 70, fs + 46
    c.save(); c.translate(540, 330); c.scale(sc, sc)
    col(c, '#000000', 0.25*a); rrect(c, -w/2 + 6, -h/2 + 8, w, h, 26); c.fill()
    col(c, '#ffffff', 0.95*a); rrect(c, -w/2, -h/2, w, h, 26); c.fill()
    col(c, '#111111', a); c.move_to(-ext.x_advance/2, fs*0.36); c.show_text(text)
    c.restore()

def render_frame(c, f, envs):
    gt = f / FPS
    i = max(k for k, s in enumerate(SCENES) if gt >= s[0])
    s0, s1, fn = SCENES[i]; lt = gt - s0
    bp = (gt % BEAT) / BEAT
    I = {'nod': math.exp(-bp*5), 'env': float(envs[min(f, len(envs)-1)])}
    col(c, '#000000'); c.paint()
    c.save()
    if i > 0 and lt < 0.25:
        z = 1.12 - 0.12*ease(lt/0.25); c.translate(540, 960); c.scale(z, z); c.translate(-540, -960)
    fn(c, lt, gt, I)
    c.restore()
    if i > 0 and lt < 0.25: col(c, '#ffffff', 0.7*(1 - lt/0.25)); c.paint()
    a = ease((lt-0.15)/0.2) * (1 - ease((lt-((s1-s0)-0.2))/0.18))
    caption(c, CAPTIONS[i], a, 0.8 + 0.2*ease((lt-0.15)/0.25) + 0.05*math.sin(min(1, max(0, (lt-0.15)/0.35))*math.pi))
    if gt > DUR - 0.8: col(c, '#000000', ease((gt-(DUR-0.8))/0.8)); c.paint()

def main():
    os.makedirs(OUT, exist_ok=True)
    envs = synth()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    if PREVIEW:
        for f in [45, 220, 430, 600, 790, 960]:
            render_frame(c, f, envs); surf.write_to_png(os.path.join(OUT, f"prev_{f:04d}.png"))
        return
    mp4 = os.path.join(OUT, "short_cartoon_1080x1920.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "beat.wav"),
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4],
                         stdin=subprocess.PIPE)
    for f in range(NF):
        render_frame(c, f, envs); surf.flush(); p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); p.wait()
    print("ok", mp4)

main()
