import os, sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[2]
W, H = 1080, 1350
FD = '/usr/share/fonts/opentype/noto/'
def F(w, s): return ImageFont.truetype(FD + f'NotoSansCJK-{w}.ttc', s, index=1)

BG = (14, 17, 30)
CARD = (27, 32, 52)
FG = (240, 242, 248)
MUTED = (150, 158, 184)
ACCENT = (198, 244, 50)

def wrap(d, text, font, maxw):
    lines = []
    for para in text.split('\n'):
        words = para.split(' ')
        cur = ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=font) <= maxw:
                cur = t
            else:
                if cur: lines.append(cur)
                # hard-break long words
                while d.textlength(w, font=font) > maxw:
                    i = len(w)
                    while d.textlength(w[:i], font=font) > maxw: i -= 1
                    lines.append(w[:i]); w = w[i:]
                cur = w
        lines.append(cur)
    return lines

def draw_lines(d, xy, lines, font, fill, gap):
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=font, fill=fill)
        y += font.size + gap
    return y

def footer(d, idx, total, series):
    d.text((80, H - 90), series, font=F('Medium', 26), fill=MUTED)
    s = f'{idx} / {total}'
    f = F('Medium', 26)
    d.text((W - 80 - d.textlength(s, font=f), H - 90), s, font=f, fill=MUTED)

def cover(post, total):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((80, 120, 80 + d.textlength(post['tag'], font=F('Bold', 34)) + 48, 186), 33, fill=ACCENT)
    d.text((104, 126), post['tag'], font=F('Bold', 34), fill=BG)
    y = 300
    y = draw_lines(d, (80, y), wrap(d, post['title'], F('Black', 92), W - 160), F('Black', 92), FG, 26)
    y += 30
    d.rectangle((80, y, 200, y + 10), fill=ACCENT)
    y += 60
    draw_lines(d, (80, y), wrap(d, post['sub'], F('Regular', 40), W - 160), F('Regular', 40), MUTED, 16)
    f = F('Bold', 38)
    t = '넘겨서 보기  →'
    d.text((W - 80 - d.textlength(t, font=f), H - 200), t, font=f, fill=ACCENT)
    footer(d, 1, total, post['series'])
    return im

def tip(post, i, t, total):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.text((80, 100), f'{i:02d}', font=F('Black', 150), fill=ACCENT)
    y = 300
    y = draw_lines(d, (80, y), wrap(d, t['head'], F('Black', 64), W - 160), F('Black', 64), FG, 18)
    y += 36
    y = draw_lines(d, (80, y), wrap(d, t['body'], F('Regular', 38), W - 160), F('Regular', 38), MUTED, 18)
    y += 50
    fe = F('Medium', 36)
    ex = wrap(d, t['ex'], fe, W - 160 - 80)
    box_h = 70 + len(ex) * (fe.size + 18) + 40
    d.rounded_rectangle((80, y, W - 80, y + box_h), 28, fill=CARD)
    d.text((120, y + 30), t.get('label', '이렇게 써보세요'), font=F('Bold', 28), fill=ACCENT)
    draw_lines(d, (120, y + 82), ex, fe, FG, 18)
    footer(d, i + 1, total, post['series'])
    return im

def cta(post, total):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    y = 330
    y = draw_lines(d, (80, y), wrap(d, post['cta'], F('Black', 76), W - 160), F('Black', 76), FG, 22)
    y += 60
    for label, txt in [('저장', '필요할 때 다시 꺼내 보기'), ('공유', '이거 필요한 친구에게 보내기'), ('팔로우', '매일 AI 꿀팁 받아보기')]:
        d.rounded_rectangle((80, y, W - 80, y + 120), 26, fill=CARD)
        d.text((120, y + 34), label, font=F('Bold', 40), fill=ACCENT)
        d.text((320, y + 36), txt, font=F('Regular', 38), fill=FG)
        y += 150
    if post.get('note'):
        y += 20
        draw_lines(d, (80, y), wrap(d, post['note'], F('Regular', 32), W - 160), F('Regular', 32), MUTED, 14)
    footer(d, total, total, post['series'])
    return im

import json
POSTS = json.load(open(sys.argv[1], encoding='utf-8'))
os.makedirs(OUT, exist_ok=True)
for p in POSTS:
    p.setdefault('series', 'AI 활용 팁')
    total = len(p['tips']) + 2
    imgs = [cover(p, total)] + [tip(p, i + 1, t, total) for i, t in enumerate(p['tips'])] + [cta(p, total)]
    for n, im in enumerate(imgs, 1):
        im.quantize(colors=16, method=Image.Quantize.MEDIANCUT).save(os.path.join(OUT, f"{p['slug']}_{n:02d}.png"), optimize=True)
    th = [im.resize((270, 338)) for im in imgs]
    strip = Image.new('RGB', (280 * len(th) - 10, 338), (255, 255, 255))
    for k, t in enumerate(th): strip.paste(t, (k * 280, 0))
    strip.save(os.path.join(OUT, f"preview_{p['slug']}.jpg"), quality=80)
print('ok')
