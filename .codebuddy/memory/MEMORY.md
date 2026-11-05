# 长期记忆（v6bench）

## 仓库约定
- 提交信息风格：`<scope>: <小写英文动词开头的一句话>`，例如 `dns: add a sample four-view zone file`、`test_runner.sh: wait up to 300s for SIIT/NAT64 and skip the sdom on timeout`。
- Markdown 文档中的 shell 代码块统一用 ` ```bash ` 围栏；正文里的 `{域名}`、`lab.{域名}` 是占位写法，保留花括号不会被解析成代码。
- `doc/report/` 是调研报告交付目录：`v6bench-调研报告.md` 为唯一源，PDF/DOCX 由 pandoc 导出，PPTX 由 `gen_deck.py` 生成，配图由 `make_figures.py` 生成 SVG 再 `rsvg-convert` 转 PNG。改一处数字要同步 md/pdf/pptx（README 末尾有同一套数字的说明）。
- Word 版（`.docx`）按用户要求不入库。

## 易踩的坑
- 根目录 `scanapi.yaml` 是 `v6bench/scanapi_conversor.sh` 的输入模板，脚本运行时会 `mv` 到 `v6bench/kathara/shared/shared_data/scanapi.yaml`（该路径被 `.gitignore` 的 `*.yaml` 忽略）。所以跑完脚本后 `git status` 会出现「删除 scanapi.yaml」，这是副作用而非改动，**不要提交该删除**，否则脚本在新克隆的仓库里跑不起来。
- `.gitignore` 里 `*.yaml` 是全局规则，新加的 yaml 文件默认不入库，需要显式 `git add -f`。
- `zonefile_creator.py` 生成的 `db.lab` / `named.conf.lab-zones` 落在 `v6bench/kathara/dns/etc/bindfiles/`，而 `.gitignore` 里写的是旧路径 `v6bench/kathara/bind/...`（分析笔记 D-5），跑一次生成脚本会让仓库变脏。
- 本机环境限制（已实测）：host 无 IPv6 默认路由，所有依赖原生 IPv6 出网的场景必然失败；Docker 需用 `docker.1ms.run` + skopeo 逐 blob 重试拉镜像；Kathará 3.8.3 需打补丁绕过 docker 版本号 `dev` 的解析崩溃。详见 `doc/v6bench_analysis.md` 的 C 区。
