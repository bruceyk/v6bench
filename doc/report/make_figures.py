#!/usr/bin/env python3
"""Generate report figures as SVG (then converted to PNG with rsvg-convert).

Includes a rough text-width estimator so overflow gets reported instead of guessed at:
CJK glyphs ~1.0em, latin ~0.55em.
"""

import os

OUT = "/home/kyu/workspace/v6bench/doc/report/img"
FONT = "Noto Sans CJK SC"

C_V4 = "#1f6feb"
C_V6 = "#0f9d58"
C_NAT = "#e8710a"
C_SIIT = "#7b3fe4"
C_GRAY = "#9aa0a6"
C_INK = "#202124"
C_SOFT = "#f1f3f4"
C_LINE = "#dadce0"

WARNINGS = []


def tw(s, size):
    w = 0.0
    for ch in s:
        w += size * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w


def check(s, size, avail, where):
    need = tw(s, size)
    if need > avail:
        WARNINGS.append(f"{where}: '{s}' needs {need:.0f}px, box allows {avail:.0f}px")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, s, size: float = 15, anchor="start", color=C_INK, weight="normal"):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>'
    )


def box(x, y, w, h, fill=C_SOFT, stroke=C_LINE, r=6, sw=1.4):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def arrow(x1: float, y1: float, x2: float, y2: float, color=C_GRAY, width: float = 2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{width}"{d} marker-end="url(#ah)"/>'
    )


def doc(w, h, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="{C_GRAY}"/></marker></defs>
<rect width="{w}" height="{h}" fill="#ffffff"/>
{body}
</svg>'''


# ---------------------------------------------------------------- figure 1
def fig_matrix():
    w, h = 1250, 740
    b = [text(60, 58, "同一套接口用例，四种 DNS 回答，四种客户端能力", 24, weight="bold")]
    b.append(text(60, 90, "矩阵里每一组是一次运行，十组组合对应 draft-ietf-v6ops-ipv6-app-testing 表 1 的十个测试场景", 14, color="#5f6368"))

    x0, y0 = 268, 182
    cw, ch = 236, 122
    cols = [
        ("dual.lab.api.apis.guru", "真实 A + 真实 AAAA", C_V6),
        ("ipv4.lab.api.apis.guru", "只有真实 A", C_V4),
        ("ipv6.lab.api.apis.guru", "只有真实 AAAA", C_V6),
        ("siit.lab.api.apis.guru", "只有 A 192.168.46.1", C_SIIT),
    ]
    rows = [
        ("dual_client", "双栈", ["2001:db8:1::10", "192.168.0.10"]),
        ("ipv4_client", "纯 v4（IPv6 已关）", ["（无 v6 地址）", "192.168.0.40"]),
        ("ipv6_strict_client", "纯 v6（封 NAT64）", ["2001:db8:1::60", "（无 v4 地址）"]),
        ("ipv6_nat64_client", "纯 v6（靠 NAT64）", ["2001:db8:1::664", "（无 v4 地址）"]),
    ]

    for i, (name, sub, color) in enumerate(cols):
        cx = x0 + i * cw
        b.append(box(cx, y0 - 78, cw - 16, 66, "#ffffff", color))
        b.append(text(cx + 12, y0 - 52, name, 14, weight="bold", color=color))
        b.append(text(cx + 12, y0 - 28, sub, 12, color="#5f6368"))
        check(name, 14, cw - 30, f"fig1 col{i}")

    cells = {
        (0, 0): ("场景 7", ["A+AAAA", "两端都双栈"], C_GRAY),
        (0, 1): ("场景 1", ["A", "客户端多一个地址族"], C_V4),
        (0, 2): ("场景 2", ["AAAA", "客户端多一个地址族"], C_V6),
        (1, 0): ("场景 3", ["A+AAAA", "服务端多一个地址族"], C_GRAY),
        (1, 1): ("场景 8", ["A", "纯 v4 两端"], C_V4),
        (1, 3): ("场景 6", ["192.168.46.1", "经 SIIT 到 v6 服务"], C_SIIT),
        (2, 0): ("场景 5", ["A+AAAA", "只能落到 v6 那半"], C_GRAY),
        (2, 2): ("场景 10", ["AAAA", "纯 v6 两端"], C_V6),
        (3, 1): ("场景 4", ["A → 64:ff9b::x", "经 NAT64"], C_NAT),
        (3, 2): ("场景 9", ["AAAA", "v6 直达"], C_V6),
    }

    for j, (name, who, addrs) in enumerate(rows):
        cy = y0 + j * ch
        b.append(box(60, cy - 22, 186, 94, "#ffffff", C_LINE))
        b.append(text(70, cy + 2, name, 13.5, weight="bold"))
        b.append(text(70, cy + 22, who, 11.5, color="#5f6368"))
        b.append(text(70, cy + 40, addrs[0], 11, color="#5f6368"))
        b.append(text(70, cy + 56, addrs[1], 11, color="#5f6368"))
        check(name, 13.5, 176, f"fig1 row{j}")

        for i in range(4):
            cx = x0 + i * cw
            cell = cells.get((j, i))
            if cell:
                tag, desc, color = cell
                b.append(box(cx, cy - 22, cw - 16, 94, "#ffffff", color, sw=1.8))
                b.append(text(cx + 12, cy, tag, 13.5, weight="bold", color=color))
                for li, line in enumerate(desc):
                    b.append(text(cx + 12, cy + 24 + li * 17, line, 11.5, color="#3c4043"))
                    check(line, 11.5, cw - 30, f"fig1 cell{j}{i}")
            else:
                b.append(box(cx, cy - 22, cw - 16, 94, "#fafafa", C_LINE))
                b.append(text(cx + (cw - 16) / 2, cy + 22, "不测", 12, anchor="middle", color="#bdc1c6"))

    b.append(text(60, 690, "每个客户端访问哪几个域名由 lab.conf 的 SDOMS 决定。空白格不是遗漏，是设计上本来就不测。", 13, color="#5f6368"))
    return doc(w, h, "".join(b))


# ---------------------------------------------------------------- figure 2
def fig_topology():
    w, h = 1320, 830
    b = [text(60, 58, "拓扑：8 台容器挂在同一条虚拟网线上", 24, weight="bold")]
    b.append(text(60, 90, "LAB 是一个碰撞域，相当于一根网线。v4 和 v6 是这条线上的两套栈，不是两张网。", 14, color="#5f6368"))

    b.append(box(440, 120, 420, 76, "#ffffff", C_LINE))
    b.append(text(650, 148, "宿主 eno1（公网 v4 + 原生 v6）", 14, anchor="middle", weight="bold"))
    b.append(text(650, 174, "218.241.114.3 / 2001:dc7:dd00:6400::40", 11.5, anchor="middle", color="#5f6368"))

    b.append(box(440, 222, 420, 64, "#ffffff", C_V6))
    b.append(text(650, 246, "docker0 桥", 14, anchor="middle", weight="bold", color=C_V6))
    b.append(text(650, 270, "172.17.0.1 / fd00:6b65::1（需手动开启）", 11.5, anchor="middle", color="#5f6368"))

    b.append(arrow(650, 196, 650, 220))
    b.append(arrow(438, 268, 300, 306, C_V6, 2))
    b.append(text(312, 262, "gateway 的 eth1 挂在这座桥上", 11.5, color=C_V6))

    b.append(box(96, 306, 200, 158, "#f8fbff", C_V4, r=8, sw=2))
    b.append(text(196, 332, "gateway", 16, anchor="middle", weight="bold", color=C_V4))
    b.append(text(196, 354, "唯一出口：转发 + 双栈 NAT", 11, anchor="middle", color="#5f6368"))
    b.append(text(196, 380, "eth0 2001:db8:1::1/64", 11, anchor="middle"))
    b.append(text(196, 398, "        192.168.0.1/24", 11, anchor="middle"))
    b.append(text(196, 430, "eth1 172.17.0.3", 11, anchor="middle"))
    b.append(text(196, 448, "（挂 docker0）", 11, anchor="middle"))

    b.append(f'<line x1="100" y1="492" x2="1222" y2="492" stroke="{C_INK}" stroke-width="3"/>')
    b.append(text(1230, 498, "LAB", 13, weight="bold"))
    b.append(f'<line x1="196" y1="464" x2="196" y2="492" stroke="{C_V4}" stroke-width="2"/>')

    row1 = [
        (350, "dns", C_NAT, ("2001:db8:1::53", "192.168.0.53"), "BIND9 权威区", "DNS64 64:ff9b::/96"),
        (580, "nat64", C_NAT, ("2001:db8:1::64", "192.168.0.64"), "Jool 有状态", "pool6 64:ff9b::/96"),
        (810, "siit", C_SIIT, ("2001:db8:1::46", "192.168.0.46"), "Jool 无状态", "2 条 EAMT 映射"),
    ]
    for x, name, color, addr, role, note in row1:
        b.append(box(x, 372, 210, 108, "#ffffff", color, r=8, sw=1.8))
        b.append(text(x + 105, 398, name, 15, anchor="middle", weight="bold", color=color))
        b.append(text(x + 105, 420, addr[0], 11, anchor="middle", color="#3c4043"))
        b.append(text(x + 105, 438, addr[1], 11, anchor="middle", color="#3c4043"))
        b.append(text(x + 105, 458, role, 10.5, anchor="middle", color="#5f6368"))
        b.append(text(x + 105, 474, note, 10.5, anchor="middle", color="#5f6368"))
        b.append(f'<line x1="{x + 105}" y1="480" x2="{x + 105}" y2="492" stroke="{color}" stroke-width="2"/>')
        check(role, 10.5, 196, f"fig2 {name} role")
        check(note, 10.5, 196, f"fig2 {name} note")

    row2 = [
        (350, "dual_client", C_V6, "2001:db8:1::10", "192.168.0.10", "双栈探针 · 3 个域名"),
        (580, "ipv4_client", C_V4, "（无 v6 地址）", "192.168.0.40", "纯 v4 探针 · 3 个域名"),
        (810, "ipv6_strict_client", C_V6, "2001:db8:1::60", "（无 v4 地址）", "纯 v6 · 封死 64:ff9b::/96"),
        (1040, "ipv6_nat64_client", C_NAT, "2001:db8:1::664", "（无 v4 地址）", "纯 v6 · 2 个域名"),
    ]
    for x, name, color, a6, a4, role in row2:
        b.append(box(x, 560, 190, 100, "#ffffff", color, r=8, sw=1.8))
        b.append(text(x + 95, 586, name, 13.5, anchor="middle", weight="bold", color=color))
        b.append(text(x + 95, 610, a6, 11, anchor="middle", color="#3c4043"))
        b.append(text(x + 95, 628, a4, 11, anchor="middle", color="#3c4043"))
        b.append(text(x + 95, 650, role, 10.5, anchor="middle", color="#5f6368"))
        b.append(f'<line x1="{x + 95}" y1="560" x2="{x + 95}" y2="492" stroke="{color}" stroke-width="2" stroke-dasharray="6 4"/>')
        check(name, 13.5, 180, f"fig2 {name}")
        check(role, 10.5, 180, f"fig2 role {name}")

    b.append(text(60, 712, "地址规律：v6 的 host 段就是 v4 的最后一段（::53/.53、::64/.64、::46/.46），只有两台纯 v6 探针例外", 13, color="#3c4043"))
    b.append(text(60, 738, "两组幻影地址不在网线上：64:ff9b::/96 是 NAT64 池；2001:db8:4::/120 与 192.168.46.0/24 是 SIIT 的映射", 13, color="#3c4043"))
    b.append(text(60, 782, "本机实测：宿主只有单个 /128、没有可下发的 /64，容器出公网 v6 只能靠 fd00 ULA + 宿主 NAT66 两层翻译", 13, color=C_SIIT))
    return doc(w, h, "".join(b))


# ---------------------------------------------------------------- figure 3
def fig_flows():
    w, h = 1280, 880
    b = [text(60, 58, "四条数据流：同一份用例，四种路径", 24, weight="bold")]
    b.append(text(60, 90, "★ 标在决定成败的那一跳上，方框下面的小字是服务端最终看到的源地址", 14, color="#5f6368"))

    panels = [
        (40, 118, "① v4 直达", C_V4, [
            ("dual_client / ipv4_client", C_V4),
            ("gateway 192.168.0.1 转发", C_V4),
            ("★ gateway MASQUERADE → 172.17.0.3", C_V4),
            ("宿主 SNAT → 公网 v4", C_V4),
        ], "服务端看到宿主公网 v4（218.241.114.3）", "场景 1 / 3 / 7 / 8"),
        (660, 118, "② v6 直达", C_V6, [
            ("dual_client / strict ::10 / ::60", C_V6),
            ("gateway 2001:db8:1::1 转发", C_V6),
            ("★ gateway MASQUERADE → fd00:6b65::x", C_V6),
            ("宿主 NAT66 → 公网 v6", C_V6),
        ], "服务端看到宿主原生 v6（2001:dc7:dd00:6400::40）", "场景 2 / 5 / 9 / 10"),
        (40, 500, "③ DNS64 + NAT64", C_NAT, [
            ("nat64_client ::664 发请求", C_NAT),
            ("dns 合成 AAAA = 64:ff9b::<v4>", C_NAT),
            ("★ nat64 翻译：源 → 192.168.0.64", C_NAT),
            ("gateway + 宿主两层 NAT → 公网 v4", C_V4),
        ], "服务端看到宿主公网 v4（218.241.114.3）", "场景 4"),
        (660, 500, "④ SIIT", C_SIIT, [
            ("ipv4_client .40 连 192.168.46.1", C_V4),
            ("gateway 路由到 siit .46", C_SIIT),
            ("★ EAMT：源 → 2001:db8:4::40，目的 → 目标真 v6", C_SIIT),
            ("gateway + 宿主两层 NAT → 公网 v6", C_SIIT),
        ], "服务端看到宿主原生 v6（2001:dc7:dd00:6400::40）", "场景 6（IPv6-only-DC）"),
    ]

    for px, py, title, color, steps, foot, tag in panels:
        b.append(box(px, py, 580, 348, "#ffffff", C_LINE, r=10))
        b.append(f'<rect x="{px}" y="{py}" width="580" height="8" rx="4" fill="{color}"/>')
        b.append(text(px + 24, py + 46, title, 17, weight="bold", color=color))
        b.append(text(px + 556, py + 46, tag, 12, anchor="end", color="#5f6368"))

        for i, (label, lc) in enumerate(steps):
            by = py + 70 + i * 54
            b.append(box(px + 24, by, 532, 38, "#ffffff", lc, r=6, sw=1.5))
            b.append(text(px + 38, by + 24, label, 12, color="#3c4043"))
            check(label, 12, 505, f"fig3 {title} step{i}")
            if i < len(steps) - 1:
                b.append(arrow(px + 290, by + 38, px + 290, by + 50, lc, 1.6))

        b.append(text(px + 24, py + 316, foot, 11.5, color="#5f6368"))
        check(foot, 11.5, 530, f"fig3 {title} foot")

    b.append(text(60, 858, "四条路径最后都要落到 gateway 的 eth1，再到 docker0。lab 内部怎么翻译，源地址都要过 gateway 和宿主两层 NAT 才变公网。", 13, color="#3c4043"))
    return doc(w, h, "".join(b))


os.makedirs(OUT, exist_ok=True)
for name, fn in [
    ("fig1-matrix", fig_matrix),
    ("fig2-topology", fig_topology),
    ("fig3-flows", fig_flows),
]:
    p = os.path.join(OUT, name + ".svg")
    with open(p, "w", encoding="utf-8") as f:
        f.write(fn())
    print("wrote", p)

print("\n-- overflow report --")
if WARNINGS:
    for wmsg in WARNINGS:
        print("WARN", wmsg)
else:
    print("all text fits the boxes (by estimate)")
