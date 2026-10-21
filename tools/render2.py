"""Card news renderer v2 — 'popular info-account' style.

Usage: python3 tools/render2.py posts/xxx.json OUT_DIR

Per post JSON fields:
  slug, theme (ai|money|home|talk), series, tag, emoji,
  title  (use [단어] to highlight), sub,
  hook   {"q": "공감 질문", "a": "[강조] 포함 답"}   -> slide 2
  tips   [{emoji, head, body, ex, label?}] x 3~6  -> one slide each
  share_to  e.g. "신입 동료"                        -> last slide
  follow, note (optional)
Slides: cover, hook, tips..., checklist, share  (max 10)
"""
import os, sys, json, re
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
M = 84  # side margin
FD = '/usr/share/fonts/opentype/noto/'
EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
_fc = {}
def F(w, s):
    k = (w, s)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FD + f'NotoSansCJK-{w}.ttc', s, index=1)
    return _fc[k]

THEMES = {
  'ai':    dict(BG=(14,17,30),   CARD=(29,34,56),   FG=(244,245,250), MUTED=(150,158,184), ACCENT=(198,244,50), ON=(14,17,30)),
  'money': dict(BG=(12,30,26),   CARD=(24,50,44),   FG=(242,247,244), MUTED=(150,178,168), ACCENT=(242,193,78), ON=(12,30,26)),
  'home':  dict(BG=(255,248,238),CARD=(246,233,215),FG=(40,35,31),    MUTED=(118,106,94),  ACCENT=(232,98,64),  ON=(255,255,255)),
  'talk':  dict(BG=(28,24,48),   CARD=(46,40,76),   FG=(246,242,252), MUTED=(170,162,192), ACCENT=(247,168,196),ON=(28,24,48)),
}
T = THEMES['ai']

# ---------- emoji ----------
def emoji_img(ch, size):
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        tmp = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((8, 8), ch, font=f, embedded_color=True)
        bb = tmp.getbbox()
        if not bb: return None
        tmp = tmp.crop(bb)
        r = size / max(tmp.size)
        return tmp.resize((max(1, int(tmp.width * r)), max(1, int(tmp.height * r))), Image.LANCZOS)
    except Exception:
        return None

def paste_emoji(im, ch, xy, size):
    e = emoji_img(ch, size) if ch else None
    if e: im.paste(e, xy, e)

# ---------- rich text: [highlight] ----------
def tokens(text):
    """-> [(word, highlighted, glued_to_previous)]"""
    out = []; prev_part = ''
    for part in re.split(r'(\[[^\]]*\])', text):
        if not part: continue
        hl = part.startswith('[') and part.endswith(']')
        body = part[1:-1] if hl else part
        glue = bool(out) and not prev_part.endswith(' ') and not body.startswith(' ')
        for k, w in enumerate(body.split(' ')):
            if w:
                out.append((w, hl, glue and k == 0 and len([x for x in body.split(' ')[:k] if x]) == 0))
        prev_part = body
    return out

def _layout(d, ln, font):
    """Return list of (x_offset, word, hl) and total width, with extra room around highlights."""
    pad = int(font.size * 0.22); sp = d.textlength(' ', font=font)
    out = []; x = 0; prev_hl = False
    for k, (w, hl, glue) in enumerate(ln):
        if k and not glue: x += sp
        if hl and not prev_hl and k: x += pad
        if not hl and prev_hl: x += pad
        if hl and not prev_hl and k == 0: x += pad
        out.append((x, w, hl)); x += d.textlength(w, font=font); prev_hl = hl
    if prev_hl: x += pad
    return out, x

def rich_wrap(d, text, font, maxw):
    lines = []
    for para in text.split('\n'):
        cur = []
        for tk in tokens(para):
            trial = cur + [tk]
            if cur and _layout(d, trial, font)[1] > maxw:
                lines.append(cur); cur = [(tk[0], tk[1], False)]
            else:
                cur = trial
        lines.append(cur)
    return lines

def rich_draw(d, x, y, lines, font, fill, gap, center=False):
    pad = int(font.size * 0.16)
    for ln in lines:
        lay, lw = _layout(d, ln, font)
        cx = x + ((W - 2 * M) - lw) / 2 if center else x
        i = 0
        while i < len(lay):
            if lay[i][2]:
                j = i
                while j + 1 < len(lay) and lay[j + 1][2]: j += 1
                x0 = cx + lay[i][0]
                seg = ' '.join(w for _, w, _ in lay[i:j + 1])
                bb = d.textbbox((x0, y), seg, font=font)
                d.rounded_rectangle((bb[0] - pad, y + font.size * 0.12, bb[2] + pad, max(bb[3], y + font.size * 1.18) + pad * 0.6),
                                    int(font.size * 0.18), fill=T['ACCENT'])
                i = j + 1
            else:
                i += 1
        for ox, w, hl in lay:
            d.text((cx + ox, y), w, font=font, fill=T['ON'] if hl else fill)
        y += font.size + gap
    return y

def text_h(lines, font, gap):
    return len(lines) * (font.size + gap) - gap

# ---------- chrome (header/footer on every slide) ----------
def chrome(d, idx, total, series, right_text):
    d.text((M, 64), series, font=F('Bold', 28), fill=T['MUTED'])
    # progress bar
    bw = 220; x0 = W - M - bw
    d.rounded_rectangle((x0, 76, x0 + bw, 84), 4, fill=T['CARD'])
    d.rounded_rectangle((x0, 76, x0 + int(bw * idx / total), 84), 4, fill=T['ACCENT'])
    f = F('Bold', 30)
    d.text((W - M - d.textlength(right_text, font=f), H - 104), right_text, font=f, fill=T['ACCENT'])
    d.text((M, H - 104), f'{idx}/{total}', font=F('Medium', 28), fill=T['MUTED'])

def new():
    im = Image.new('RGB', (W, H), T['BG'])
    return im, ImageDraw.Draw(im)

# ---------- slides ----------
def cover(p, idx, total):
    im, d = new()
    f = F('Bold', 34); ft = F('Black', 96); fs = F('Medium', 42)
    lines = rich_wrap(d, p['title'], ft, W - 2 * M)
    sl = rich_wrap(d, p['sub'], fs, W - 2 * M)
    block = 190 + 50 + 66 + 44 + text_h(lines, ft, 30) + 40 + text_h(sl, fs, 16)
    y0 = int(max(150, (H - block) / 2))
    paste_emoji(im, p.get('emoji'), (M, y0), 190)
    ty = y0 + 240
    tw = d.textlength(p['tag'], font=f)
    d.rounded_rectangle((M, ty, M + tw + 52, ty + 66), 33, outline=T['ACCENT'], width=3)
    d.text((M + 26, ty + 6), p['tag'], font=f, fill=T['ACCENT'])
    y = rich_draw(d, M, ty + 110, lines, ft, T['FG'], 30) + 40
    rich_draw(d, M, y, sl, fs, T['MUTED'], 16)
    chrome(d, idx, total, p['series'], '넘겨서 확인 →')
    return im

def hook(p, idx, total, next_head):
    im, d = new()
    h = p.get('hook') or {'q': '이거 나만 몰랐나?', 'a': '다들 하는 실수, [지금 바로] 고쳐봐요'}
    fq = F('Black', 78); fa = F('Medium', 46)
    ql = rich_wrap(d, '“' + h['q'] + '”', fq, W - 2 * M)
    al = rich_wrap(d, h['a'], fa, W - 2 * M)
    total_h = text_h(ql, fq, 24) + 70 + text_h(al, fa, 20)
    y = (H - total_h) / 2 - 40
    y = rich_draw(d, M, y, ql, fq, T['FG'], 24)
    d.rectangle((M, y + 28, M + 90, y + 36), fill=T['ACCENT'])
    rich_draw(d, M, y + 70, al, fa, T['MUTED'], 20)
    chrome(d, idx, total, p['series'], f'다음: {next_head} →' if len(next_head) <= 12 else '다음 장 →')
    return im

def tip(p, n, t, idx, total, next_label):
    im, d = new()
    fh = F('Black', 82); fb = F('Regular', 44); fe = F('Medium', 42); fl = F('Bold', 30)
    hl = rich_wrap(d, t['head'], fh, W - 2 * M)
    bl = rich_wrap(d, t['body'], fb, W - 2 * M)
    el = rich_wrap(d, t['ex'], fe, W - 2 * M - 96)
    box_h = 64 + 30 + 22 + text_h(el, fe, 18) + 56
    block = 150 + text_h(hl, fh, 22) + 36 + text_h(bl, fb, 18) + 56 + box_h
    y = max(150, (H - block) / 2 - 10)
    # number + emoji
    d.text((M, y), f'{n:02d}', font=F('Black', 120), fill=T['ACCENT'])
    paste_emoji(im, t.get('emoji'), (W - M - 130, int(y) + 6), 130)
    y += 150
    y = rich_draw(d, M, y, hl, fh, T['FG'], 22) + 36
    y = rich_draw(d, M, y, bl, fb, T['MUTED'], 18) + 56
    d.rounded_rectangle((M, y, W - M, y + box_h), 30, fill=T['CARD'])
    d.text((M + 48, y + 42), t.get('label', '이렇게 해보세요'), font=fl, fill=T['ACCENT'])
    rich_draw(d, M + 48, y + 42 + 30 + 22, el, fe, T['FG'], 18)
    chrome(d, idx, total, p['series'], next_label)
    return im

def checklist(p, idx, total):
    im, d = new()
    ft = F('Black', 76); fr = F('Bold', 44)
    rows = [t['head'].replace('[', '').replace(']', '') for t in p['tips']]
    y = 200
    y = rich_draw(d, M, y, rich_wrap(d, '[한눈에] 정리', ft, W - 2 * M), ft, T['FG'], 20) + 20
    d.text((M, y), '저장해두고 필요할 때 꺼내 보세요', font=F('Medium', 38), fill=T['MUTED'])
    y += 100
    rh = 128
    for i, r in enumerate(rows):
        d.rounded_rectangle((M, y, W - M, y + rh - 20), 26, fill=T['CARD'])
        d.rounded_rectangle((M + 36, y + 30, M + 84, y + 78), 12, fill=T['ACCENT'])
        d.line((M + 47, y + 55, M + 57, y + 66, M + 74, y + 42), fill=T['ON'], width=7)
        txt = r if d.textlength(r, font=fr) < W - 2 * M - 160 else r[:16] + '…'
        d.text((M + 120, y + 26), txt, font=fr, fill=T['FG'])
        y += rh
    chrome(d, idx, total, p['series'], '저장 필수')
    return im

def share(p, idx, total):
    im, d = new()
    to = p.get('share_to', '친구')
    ft = F('Black', 80)
    y = 170
    paste_emoji(im, '💌', (M, y), 110)
    y += 150
    y = rich_draw(d, M, y, rich_wrap(d, f'이 글이 필요한\n[{to}]에게\n보내주세요', ft, W - 2 * M), ft, T['FG'], 24) + 50
    f1 = F('Bold', 40); f2 = F('Regular', 38)
    for label, txt in [('저장', '필요할 때 다시 꺼내 보기'), ('공유', f'{to}에게 DM으로 보내기'), ('팔로우', p.get('follow', '매일 하나씩 받아보기'))]:
        d.rounded_rectangle((M, y, W - M, y + 112), 26, fill=T['CARD'])
        d.text((M + 40, y + 30), label, font=f1, fill=T['ACCENT'])
        d.text((M + 230, y + 32), txt, font=f2, fill=T['FG'])
        y += 128
    if p.get('note'):
        fn = F('Regular', 30)
        rich_draw(d, M, y + 16, rich_wrap(d, p['note'], fn, W - 2 * M), fn, T['MUTED'], 12)
    chrome(d, idx, total, p['series'], '')
    return im

def render(p):
    global T
    T = THEMES[p.get('theme', 'ai')]
    p.setdefault('series', 'AI 활용 팁')
    tips = p['tips']
    total = 2 + len(tips) + 2
    heads = [t['head'].replace('[', '').replace(']', '') for t in tips]
    imgs = [cover(p, 1, total), hook(p, 2, total, heads[0])]
    for i, t in enumerate(tips):
        nxt = heads[i + 1] if i + 1 < len(heads) else '한눈에 정리'
        label = f'다음: {nxt} →' if len(nxt) <= 11 else '다음 장 →'
        imgs.append(tip(p, i + 1, t, 3 + i, total, label))
    imgs.append(checklist(p, total - 1, total))
    imgs.append(share(p, total, total))
    return imgs

if __name__ == '__main__':
    posts = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    for p in posts:
        imgs = render(p)
        for n, im in enumerate(imgs, 1):
            im.quantize(colors=48, method=Image.Quantize.MEDIANCUT).save(
                os.path.join(out, f"{p['slug']}_{n:02d}.png"), optimize=True)
        th = [im.resize((216, 270)) for im in imgs]
        strip = Image.new('RGB', (226 * len(th) - 10, 270), (255, 255, 255))
        for k, t in enumerate(th): strip.paste(t, (k * 226, 0))
        strip.save(os.path.join(out, f"preview_{p['slug']}.jpg"), quality=82)
    print('ok')
