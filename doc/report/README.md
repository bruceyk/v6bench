# 交付物索引（V6Bench 调研）

四件事：工具解决什么问题、什么原理、架构长什么样、对工作有什么参考。只讲原理，不列实测耗时和踩坑记录。

| 文件 | 用途 | 备注 |
|---|---|---|
| `v6bench-调研报告.md` | 主文档，配 4 张图 | 唯一源，能独立读懂 |
| `v6bench-调研报告.pdf` | PDF 版（图已内嵌） | pandoc 从 md 导出 |
| `v6bench-调研报告.docx` | Word 版（图已内嵌） | pandoc 从 md 导出；本地生成，不入库 |
| `v6bench-分享-7页.pptx` | 投影版，7 页，每页备注栏有讲解提示 | 16:9，中文字体 Noto Sans CJK SC |
| `img/fig0-concept.png` | 设计草图：四类客户端、DNS、两台翻译设备与一个服务端 | 主文档第 0 节 |
| `img/fig1-matrix.png` | 客户端 × 域名矩阵 | 十组组合对应 draft 表 1 的十个测试场景 |
| `img/fig2-topology.png` | 八台设备拓扑与地址 | 单段 LAB + 唯一出口 + VDE 软交换机 |
| `img/fig3-flows.png` | 四条数据流 | v4 原生 / v6 原生 / DNS64+NAT64 / SIIT |
| `make_figures.py` | 生成 SVG 与文字溢出检查 | 重跑会打印超框警告 |
| `gen_deck.py` | 生成 PPTX | 改文字后重跑 |

改图流程：改 `make_figures.py` 里的数据，重跑脚本，再 `rsvg-convert -w 2200 -o img/figN.png img/figN.svg`。
改幻灯片：改 `gen_deck.py`，重跑。改文档：直接编辑 .md，然后
`pandoc v6bench-调研报告.md -o v6bench-调研报告.docx --resource-path=.`。

文档和幻灯片的数字是同一套：DNS64 合成值 `64:ff9b::ac42:9de3`（对应 A 记录 172.66.157.227）、
拓扑地址（::53 / ::64 / ::46 / ::10 / ::60 / ::664）。改一处记得对另一处。
