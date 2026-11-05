"""Dựng vector mẫu 02 đã chọn; xuất web, favicon và tem in.

Các đường Bézier được dựng từ hướng thiết kế đã duyệt, không nhúng ảnh raster.
Chạy từ repo: .venv/Scripts/python.exe docs/brand/asd-ease/build_selected_logo.py
"""
from pathlib import Path
import shutil
import subprocess
import zipfile

from PIL import Image
from svg_helpers import BODY, BOLD, rect, svg

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = ROOT / 'tt-signal'
BLUE, MINT, NAVY = '#0638D8', '#20E78D', '#101C40'

# Tọa độ gốc 480 x 368, có khoảng thở quanh biểu tượng.
TOP = ('M12 114L40 59C57 25 89 8 127 8H340L321 48'
       'C309 74 291 84 264 84C219 84 184 94 159 113'
       'C145 124 139 138 139 154C139 176 159 190 184 202'
       'C204 212 220 219 220 233C220 253 194 260 162 260'
       'C109 260 67 262 34 285L105 114Z')
BOTTOM = ('M264 112H463L443 153C432 178 409 192 378 192H362'
          'L314 309C302 338 285 354 254 354H186L217 281'
          'C250 273 273 253 273 225C273 202 255 188 230 177'
          'C207 167 187 159 187 145C187 123 223 112 264 112Z')
CAP_TOP = ('M382 8H470L453 40C439 66 414 80 382 80H325'
           'L351 29C357 16 366 8 382 8Z')
CAP_BOTTOM = ('M108 286H174L151 337C146 348 140 354 125 354H7'
              'L24 329C43 300 72 286 108 286Z')


def mark(x=0, y=0, width=480, primary=BLUE, accent=MINT):
    return (f'<g transform="translate({x} {y}) scale({width / 480})">'
            f'<path fill="{primary}" d="{TOP}"/><path fill="{primary}" d="{BOTTOM}"/>'
            f'<path fill="{accent}" d="{CAP_TOP}"/><path fill="{accent}" d="{CAP_BOTTOM}"/></g>')


def wordmark(x=0, y=0, width=548, color=BLUE):
    # Chữ vẽ riêng theo mẫu 02, không phụ thuộc font cài trên máy.
    shapes = {
        'A': 'M7 61L29 9Q32 3 35 9L58 61',
        'S': 'M53 8H25C4 8 4 33 25 33H36C58 33 58 60 36 60H10',
        'D': 'M10 60V8H28C65 8 65 60 28 60Z',
        'E': 'M54 8H27Q10 8 10 25V43Q10 60 27 60H54M10 33H49',
        '-': 'M7 34H25',
    }
    cursor, parts = 0, []
    for char in 'ASD-EASE':
        parts.append(f'<path transform="translate({cursor} 0)" d="{shapes[char]}"/>')
        cursor += 43 if char == '-' else 72
    return (f'<g transform="translate({x} {y}) scale({width / 548})" '
            f'fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round" '
            f'stroke-linejoin="round">{"".join(parts)}</g>')


def horizontal(primary=BLUE, accent=MINT):
    return mark(8, 15, 170, primary, accent) + wordmark(202, 43, 548, primary)


def stacked(primary=BLUE, accent=MINT):
    return mark(40, 16, 480, primary, accent) + wordmark(13, 417, 534, primary)


def favicon():
    # Nền trắng giữ khoảng âm trên cả tab sáng/tối; một màu ở cỡ nhỏ.
    return rect(0, 0, 128, 128, '#FFFFFF', 25) + mark(5, 19, 118, BLUE, BLUE)


def save(name, content):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')
    return path


def render(source, target, width=None, fmt='png'):
    converter = shutil.which('rsvg-convert') or 'C:/msys64/ucrt64/bin/rsvg-convert.exe'
    args = [converter, '--format', fmt, '--output', str(target)]
    if width:
        args += ['--width', str(width)]
    subprocess.run(args + [str(source)], check=True)


def preview():
    p = [rect(0, 0, 1500, 1120, '#F6F7FA'),
         BOLD.text('ASD-EASE', 64, 68, 28, NAVY),
         BODY.text('02 / TT SIGNAL', 1436, 68, 19, NAVY, anchor='end'),
         BOLD.text('Hai chữ T. Một nhịp kết nối.', 64, 137, 43, NAVY),
         BODY.text('Trung + Tân trong một biểu tượng, đường cong S nối liền hai phía.', 64, 177, 23, '#566078'),
         rect(64, 218, 824, 490, '#FFFFFF', 28),
         mark(270, 246, 410), wordmark(209, 605, 534),
         rect(912, 218, 524, 490, NAVY, 28),
         mark(1010, 267, 328, '#FFFFFF', MINT),
         wordmark(970, 593, 408, '#FFFFFF'),
         BODY.text('BẢN TRÊN NỀN TỐI', 1174, 671, 16, '#B8C5E6', anchor='middle'),
         rect(64, 732, 824, 288, '#FFFFFF', 28),
         BODY.text('WEB / BROWSER', 94, 777, 17, '#566078', tracking=1),
         '<g transform="translate(94 794) scale(.84)">' + horizontal() + '</g>',
         BODY.text('Favicon', 97, 982, 18, '#566078')]
    for x, size in [(204, 16), (260, 32), (332, 48)]:
        p += [f'<g transform="translate({x} {970-size}) scale({size/128})">{favicon()}</g>',
              BODY.text(f'{size}px', x + size + 8, 977, 14, '#566078')]
    p += [rect(912, 732, 524, 288, '#FFFFFF', 28),
          BODY.text('TEM / BẢN MỘT MÀU', 944, 777, 17, '#566078', tracking=1),
          mark(952, 815, 168, '#111111', '#111111'),
          rect(1175, 806, 186, 154, NAVY, 22),
          mark(1184, 819, 168, '#FFFFFF', '#FFFFFF'),
          BODY.text('SVG vector · PNG trong suốt · ICO · PDF in A4', 64, 1070, 21, '#566078'),
          rect(1126, 1050, 32, 24, BLUE, 6),
          BODY.text(BLUE, 1168, 1070, 15, '#566078'),
          rect(1278, 1050, 32, 24, MINT, 6),
          BODY.text(MINT, 1320, 1070, 15, '#566078')]
    return svg(1500, 1120, ''.join(p), 'ASD-EASE - Mẫu 02 TT Signal đã chọn')


def print_sheet(mono=False):
    primary, accent = ('#000000', '#000000') if mono else (BLUE, MINT)
    p = [rect(0, 0, 210, 297, '#FFFFFF'),
         BOLD.text('ASD-EASE / TT SIGNAL', 16, 22, 7, '#111111'),
         BODY.text(('Bản một màu' if mono else 'Bản màu') + ' / A4 / In Actual size - 100%', 16, 32, 3.6, '#444444'),
         BODY.text('Tem tròn 20 mm. Đường xám là đường cắt, không thuộc logo.', 16, 48, 3.3, '#444444')]
    for y in [68, 101, 134]:
        for x in [28, 66, 104, 142, 180]:
            p += [f'<circle cx="{x}" cy="{y}" r="10" fill="white" stroke="#BBBBBB" stroke-width=".12"/>',
                  mark(x - 7.5, y - 5.75, 15, primary, accent)]
    p += [BODY.text('Tem ngang 50 x 18 mm. Logo vector, không cần cài font.', 16, 162, 3.3, '#444444')]
    for y in [174, 202, 230]:
        for x in [17, 80, 143]:
            p += [f'<rect x="{x}" y="{y}" width="50" height="18" rx="3" fill="white" stroke="#BBBBBB" stroke-width=".12"/>',
                  f'<g transform="translate({x+3} {y+4.368}) scale({44/760})">{horizontal(primary, accent)}</g>']
    p += ['<path d="M16 268H66M16 266V270M66 266V270" fill="none" stroke="black" stroke-width=".25"/>',
          BODY.text('Thước kiểm tra: 50 mm', 16, 278, 3.3, '#333333'),
          BODY.text('Không chọn Fit to page. Chọn lại kích thước tem theo vỏ thiết bị thực tế.', 16, 288, 3, '#555555')]
    return svg(210, 297, ''.join(p), 'Tem thử ASD-EASE mẫu 02 - A4', (210, 297))


def main():
    for suffix, primary, accent in [('', BLUE, MINT), ('-black', '#000000', '#000000'),
                                    ('-white', '#FFFFFF', '#FFFFFF'), ('-reverse', '#FFFFFF', MINT)]:
        save(f'mark{suffix}.svg', svg(480, 368, mark(primary=primary, accent=accent), 'ASD-EASE TT Signal'))
        save(f'logo-horizontal{suffix}.svg', svg(760, 160, horizontal(primary, accent), 'ASD-EASE'))
        save(f'logo-stacked{suffix}.svg', svg(560, 512, stacked(primary, accent), 'ASD-EASE'))
    save('wordmark.svg', svg(548, 72, wordmark(), 'ASD-EASE'))
    icon = save('favicon.svg', svg(128, 128, favicon(), 'ASD-EASE'))
    app = save('app-icon.svg', svg(512, 512, rect(0, 0, 512, 512, '#FFFFFF') + mark(48, 97, 416), 'ASD-EASE'))
    for name, width in [('mark', 2400), ('mark-black', 2400), ('mark-white', 2400),
                        ('logo-horizontal', 2280), ('logo-stacked', 1680)]:
        render(OUT / f'{name}.svg', OUT / f'{name}.png', width)
    render(app, OUT / 'app-icon-512.png', 512)
    render(app, OUT / 'apple-touch-icon.png', 180)
    for size in [16, 32, 48, 64]:
        render(icon, OUT / f'favicon-{size}.png', size)
    with Image.open(OUT / 'favicon-64.png') as image:
        smaller = [Image.open(OUT / f'favicon-{s}.png') for s in [16, 32, 48]]
        image.save(OUT / 'favicon.ico', sizes=[(s, s) for s in [16, 32, 48, 64]], append_images=smaller)
        for item in smaller:
            item.close()
    board = save('preview.svg', preview())
    render(board, OUT / 'preview.png')
    pdf_dir = REPO / 'output/pdf'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for suffix, mono in [('', False), ('-mono', True)]:
        source = save(f'stickers-a4{suffix}.svg', print_sheet(mono))
        render(source, pdf_dir / f'asd-ease-logo-02-stickers-a4{suffix}.pdf', fmt='pdf')
    public = REPO / 'frontend/public'
    (public / 'brand').mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / 'logo-horizontal.svg', public / 'brand/asd-ease-logo.svg')
    shutil.copy2(OUT / 'mark.svg', public / 'brand/asd-ease-mark.svg')
    for name in ['favicon.svg', 'favicon.ico', 'apple-touch-icon.png']:
        shutil.copy2(OUT / name, public / name)
    archive = REPO / 'output/brand/asd-ease-logo-02.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                bundle.write(path, path.name)
        for path in sorted(pdf_dir.glob('asd-ease-logo-02-*.pdf')):
            bundle.write(path, 'print/' + path.name)
    print('Đã xuất TT Signal: vector, PNG, favicon, PDF in và asset frontend.')


if __name__ == '__main__':
    main()
