"""Tiện ích SVG và chữ vector cho bảng mẫu, tem in của logo đã chọn."""
from html import escape
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen


class OutlineFont:
    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.units = self.font['head'].unitsPerEm

    def text(self, value, x, y, size, color='#101C40', tracking=0, anchor='start'):
        scale = size / self.units
        cursor, paths = 0, []
        for char in value:
            glyph = self.cmap.get(ord(char))
            if glyph is None:
                raise ValueError(f'Missing glyph {char!r}')
            pen = SVGPathPen(self.glyphs)
            self.glyphs[glyph].draw(pen)
            if pen.getCommands():
                paths.append(f'<path transform="translate({cursor:.3f} 0)" d="{pen.getCommands()}"/>')
            cursor += self.font['hmtx'][glyph][0] + tracking / scale
        width = cursor * scale - tracking if value else 0
        if anchor == 'middle':
            x -= width / 2
        elif anchor == 'end':
            x -= width
        return (f'<g aria-label="{escape(value)}" fill="{color}" '
                f'transform="translate({x:.3f} {y:.3f}) scale({scale:.6f} {-scale:.6f})">'
                f'{"".join(paths)}</g>')


BODY = OutlineFont(Path('C:/Windows/Fonts/segoeui.ttf'))
BOLD = OutlineFont(Path('C:/Windows/Fonts/seguisb.ttf'))


def rect(x, y, w, h, color, radius=0, stroke=None):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}"'
            + (f' stroke="{stroke}"' if stroke else '') + '/>')


def svg(width, height, body, title, physical=None):
    dimensions = (f'width="{physical[0]}mm" height="{physical[1]}mm"' if physical
                  else f'width="{width}" height="{height}"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" {dimensions} '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">'
            f'<title id="title">{escape(title)}</title>{body}</svg>\n')
