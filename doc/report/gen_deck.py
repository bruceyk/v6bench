#!/usr/bin/env python3
"""Build the 7-slide sharing deck from the report figures."""

import os

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
OUT = os.path.join(HERE, "v6bench-分享-7页.pptx")

FONT = "Noto Sans CJK SC"
INK = RGBColor(0x20, 0x21, 0x24)
SOFT = RGBColor(0x5F, 0x63, 0x68)
V4 = RGBColor(0x1F, 0x6F, 0xEB)
V6 = RGBColor(0x0F, 0x9D, 0x58)
NAT = RGBColor(0xE8, 0x71, 0x0A)
SIIT = RGBColor(0x7B, 0x3F, 0xE4)
RED = RGBColor(0xC5, 0x22, 0x1F)
BG = RGBColor(0xFF, 0xFF, 0xFF)

W, H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H
blank = prs.slide_layouts[6]


def new_slide():
    s = prs.slides.add_slide(blank)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return s


def txbox(slide, left, top, width, height, text, size=18, bold=False,
          color=INK, align=PP_ALIGN.LEFT, space_after=6, line_spacing=1.25):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = FONT
    return box


def bullets(slide, left, top, width, height, items, size=16, gap=10):
    """items: list of (text, level, color) tuples."""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for text, level, color in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.line_spacing = 1.2
        p.level = level
        r = p.add_run()
        r.text = ("• " if level == 0 else "– ") + text
        r.font.size = Pt(size if level == 0 else size - 2)
        r.font.color.rgb = color
        r.font.name = FONT
    return box


def rule(slide, color, top=Inches(1.28), height=Pt(3)):
    bar = slide.shapes.add_shape(1, Inches(0.7), top, Inches(1.1), height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False
    return bar


def heading(slide, text, kicker=None, color=V6):
    if kicker:
        txbox(slide, Inches(0.72), Inches(0.45), Inches(10), Inches(0.35),
              kicker, size=12, color=SOFT)
        txbox(slide, Inches(0.72), Inches(0.78), Inches(11.6), Inches(0.6),
              text, size=30, bold=True, color=INK)
        rule(slide, color, top=Inches(1.46))
    else:
        txbox(slide, Inches(0.72), Inches(0.55), Inches(11.6), Inches(0.8),
              text, size=30, bold=True, color=INK)
        rule(slide, color, top=Inches(1.3))


def pic(slide, name, top, max_h_in, left_in=None):
    from PIL import Image
    path = os.path.join(IMG, name)
    iw, ih = Image.open(path).size
    h = min(Inches(max_h_in), Inches(7.5) - top - Inches(0.4))
    w = Emu(int(h * iw / ih))
    left = Inches(left_in) if left_in is not None else Emu(int((W - w) / 2))
    slide.shapes.add_picture(path, left, top, width=w, height=h)
    return left, top, w, h


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ---------------------------------------------------------------- 1 封面
s = new_slide()
band = s.shapes.add_shape(1, Inches(0), Inches(0), W, Inches(0.28))
band.fill.solid()
band.fill.fore_color.rgb = V6
band.line.fill.background()
band.shadow.inherit = False

txbox(s, Inches(0.9), Inches(1.6), Inches(9.5), Inches(0.4), "IPv6 单栈部署 · 工具调研", 14, color=SOFT)
txbox(s, Inches(0.9), Inches(2.02), Inches(11), Inches(1.0), "V6Bench", 54, bold=True, color=INK)
txbox(s, Inches(0.9), Inches(3.22), Inches(11), Inches(0.8),
      "同一套接口用例，四种网络环境，十个测试场景", 26, color=V6, bold=True)
txbox(s, Inches(0.9), Inches(3.85), Inches(10.5), Inches(1.6),
      "被测服务一行代码不动，只换客户端的地址族能力、DNS 的回答方式、\n"
      "中间有没有翻译设备。断言只有一条：HTTP 状态码等于 spec 声明的成功码。",
      17, color=SOFT, line_spacing=1.4)
txbox(s, Inches(0.9), Inches(6.35), Inches(11), Inches(0.7),
      "工具出处：Sávyo de Morais（NIC.br）· RIPE 93 远程演示 2026-10-26\n"
      "本机复现 2026-11-03 ｜ 仓库 commit 628619f", 12, color=SOFT, line_spacing=1.3)
notes(s, "开场先划边界：这是一个地址族实验台，不验业务对不对，也不测性能。"
         "今天讲四件事：解决什么问题、什么原理、架构长什么样、对工作有什么参考。")

# ---------------------------------------------------------------- 2 为什么需要它
s = new_slide()
heading(s, "单栈上线前真正要回答的问题", "01 / 为什么需要它", V4)
bullets(s, Inches(0.85), Inches(1.75), Inches(5.6), Inches(4.6), [
    ("难点不在网络能否通 v6", 0, INK),
    ("而在业务能否仅靠 v6 正常运行", 1, SOFT),
    ("双栈环境下问题都被 IPv4 那一半掩盖", 0, INK),
    ("域名只有 A 记录，解析不到东西", 1, SOFT),
    ("服务端监听 0.0.0.0，v6 请求拒连", 1, SOFT),
    ("依赖 DNS64 合成，合成地址回不来", 1, SOFT),
    ("按 RFC 6724 选了 v6，那条路是黑洞", 1, SOFT),
], size=17)

card = s.shapes.add_shape(1, Inches(6.85), Inches(1.8), Inches(5.7), Inches(2.6))
card.fill.solid()
card.fill.fore_color.rgb = RGBColor(0xF6, 0xF9, 0xF7)
card.line.color.rgb = V6
card.shadow.inherit = False
txbox(s, Inches(7.1), Inches(2.0), Inches(5.2), Inches(0.4), "它回答的问题", 13, color=SOFT)
txbox(s, Inches(7.1), Inches(2.4), Inches(5.2), Inches(1.9),
      "同一批 API，\n当客户端只有 IPv6、\n当域名只解析出 IPv6、\n当服务端只有 IPv6 地址，\n状态码会不会变。",
      19, bold=True, color=INK, line_spacing=1.45)

bullets(s, Inches(6.85), Inches(4.75), Inches(5.7), Inches(1.9), [
    ("现有手段为什么不够", 0, INK),
    ("手工抓包靠个人经验，draft §4.5：最易出错", 1, SOFT),
    ("搭真环境成本高：要 root、要翻译设备、要能随时切回", 1, SOFT),
], size=15)
notes(s, "这一页是全篇的立论。难点不在网络能否通 v6，而在业务能否仅靠 v6 正常运行。"
         "右边那句话是题眼，后面所有架构都是为它服务的。左边四条是双栈环境测不出来的问题。")

# ---------------------------------------------------------------- 3 原理
s = new_slide()
heading(s, "核心机关：一个区，四个名字", "02 / 原理", V6)
bullets(s, Inches(0.85), Inches(1.75), Inches(11.6), Inches(3.2), [
    ("BIND9 里一个区四个名字，每个名字一套记录，客户端查哪个拿哪个", 0, INK),
    ("dual.lab.api.apis.guru → 真实 A + 真实 AAAA，等价服务端双栈", 1, SOFT),
    ("ipv4.lab.api.apis.guru → 只有真实 A，等价服务端只有 IPv4", 1, SOFT),
    ("ipv6.lab.api.apis.guru → 只有真实 AAAA，等价服务端只有 IPv6", 1, SOFT),
    ("siit.lab.api.apis.guru → 一条假 A = 192.168.46.1，等价服务端在 IPv6-only 机房", 1, SIIT),
], size=18)

box = s.shapes.add_shape(1, Inches(0.85), Inches(5.15), Inches(11.7), Inches(1.35))
box.fill.solid()
box.fill.fore_color.rgb = RGBColor(0xF6, 0xF9, 0xF7)
box.line.color.rgb = V6
box.shadow.inherit = False
txbox(s, Inches(1.1), Inches(5.3), Inches(11.2), Inches(1.1),
      "DNS64 同时开着，前缀 64:ff9b::/96：查 ipv4.lab.api.apis.guru 的 AAAA 会拿到由 A 合成的地址\n"
      "（172.66.157.227 合成 64:ff9b::ac42:9de3，按 RFC 6052 编码）。",
      15, color=INK, line_spacing=1.35)
notes(s, "这页是整套方法的核心。同一个域名四种答案，客户端查哪个名字就看到哪种部署形态。"
         "siit 那行最关键：不给 v6 地址而是给假 v4，让 SIIT 翻过去，IPv4 客户端访问 v6 服务才成立。")

# ---------------------------------------------------------------- 4 架构
s = new_slide()
heading(s, "八台设备与一个虚拟交换机", "03 / 架构", NAT)
pic(s, "fig2-topology.png", Inches(1.62), 5.6)
notes(s, "拓扑是一个扁平二层段，八台设备挂在同一条虚拟总线上，这条总线是 kathara 的 VDE 软交换机，不是容器。"
         "只有 gateway 有第二块网卡 eth1 接宿主 docker0，也只有它做转发和 NAT，其余七台默认路由都指向它。"
         "nat64 和 siit 要装内核模块，起整套环境需要 root。")

# ---------------------------------------------------------------- 5 数据流
s = new_slide()
heading(s, "四条路径，同一批用例", "04 / 数据流", NAT)
pic(s, "fig3-flows.png", Inches(1.62), 5.6)
notes(s, "逐条讲地址怎么变。v4 原生和 v6 原生是对照组，没有翻译设备。"
         "DNS64 加 NAT64 解决纯 v6 客户端访问 v4 服务，有状态，回包按会话表还原。"
         "SIIT 解决 v4 客户端访问 v6 服务，无状态，靠 EAMT 换地址。"
         "四条路共同点：服务端看到的都是宿主公网地址，源地址要过 gateway 和宿主两层 NAT。")

# ---------------------------------------------------------------- 6 测试场景
s = new_slide()
heading(s, "四类客户端，十个测试场景", "05 / 场景", V6)
pic(s, "fig1-matrix.png", Inches(1.62), 5.1)
txbox(s, Inches(0.85), Inches(6.72), Inches(11.6), Inches(0.5),
      "两两组合对应 draft-ietf-v6ops-ipv6-app-testing 表 1 的十个场景；"
      "场景 2、10 是客户端视角的 strict，场景 6 用 SIIT 实现。", 13, color=SOFT)
notes(s, "四类客户端能力不同，可执行的场景也不同。"
         "常见问题：行模拟的是客户端网络，真装出来的；列模拟的是服务端形态，靠 DNS 回答伪装，服务端本身不变。"
         "两个口径要说明：场景 2 和 10 只控制客户端看到的记录，外部服务器是否真单栈超出这套环境的控制范围；"
         "场景 6 在 draft 里指 IPv6-only 机房，这里用无状态翻译实现。"
         "地址选择按 RFC 6724，v6 先试 v4 兜底，只有 ULA 源地址时反过来。")

# ---------------------------------------------------------------- 7 参考价值
s = new_slide()
heading(s, "这套模拟能让人看见什么", "06 / 参考价值", V6)
bullets(s, Inches(0.85), Inches(1.75), Inches(11.6), Inches(2.6), [
    ("造环境的思路：四类客户端加四个名字，不用建四套机房就摆出四种部署形态", 0, INK),
    ("一服务一矩阵的验收口径：十份结果比「ping 通了」具体，能进回归", 0, INK),
    ("翻译路径的分工：DNS64+NAT64 管 v6 客户端到 v4 服务，SIIT 管反方向，配翻译设备前先想缺哪条", 0, INK),
], size=18)

box = s.shapes.add_shape(1, Inches(0.85), Inches(4.75), Inches(11.7), Inches(1.75))
box.fill.solid()
box.fill.fore_color.rgb = RGBColor(0xFD, 0xF3, 0xF2)
box.line.color.rgb = RED
box.shadow.inherit = False
txbox(s, Inches(1.1), Inches(4.9), Inches(11.2), Inches(1.5),
      "模拟不了的三件事：\n"
      "运营商网络的真实丢包、时延与 MTU；CDN 与中间设备的 SNI、证书策略；生产流量的规模与分布。",
      15, color=INK, line_spacing=1.35)
notes(s, "收尾给参考价值和边界。三条价值都是可迁移的方法，不是工具本身的功能。"
         "边界三条要说清楚，避免把 lab 里的绿当成生产环境的绿。")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
