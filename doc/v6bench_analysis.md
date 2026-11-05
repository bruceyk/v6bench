# V6Bench 拆解笔记（Kathará 拓扑 + draft 映射 + 环境就绪）

生成时间：2026-11-02 19:10 CST
仓库：/home/kyu/workspace/v6bench（commit 628619f，main，clean）
draft 版本：draft-ietf-v6ops-ipv6-app-testing-06（2026-10-26）

结论先说三句
1. 拓扑本身是"单段扁平 LAN + 一个 bridged 出海口"，不是路由器分隔的多网段结构；DNS64 / NAT64(Jool) / SIIT(Jool) / 客户端全部挂在同一个 L2 段上。
2. 它实现的是 draft Table 1 里 10 个场景中的 6 个（5 个 base 里覆盖 4 个），"IPv4-only → IPv6-only-with-NAT64(IPv6-only-DC)" 用 SIIT 代替且把一个 Google 地址硬编码进去了。
3. 这台机器上拓扑**已经起来了并验证过**：8 个设备全起，DNS/DNS64（真的合成出 64:ff9b::） / Jool NAT64（纯 v6 客户端能打 IPv4 出网）/ SIIT EAMT / strict 客户端的 NAT64 隔离，全部实测通过；
   但 host 没有 IPv6 默认路由（无 ::/0），所以所有走原生 IPv6 出网的场景（strict 客户端实测 V6_FAIL、dual 的 v6 分支 V6_FAIL、SIIT 场景 SIIT_FAIL）必然失败。

────────────────────────────────────────────────────────────
PART A　Kathará 拓扑拆解
────────────────────────────────────────────────────────────

A1. 设备清单（v6bench/kathara/lab.conf）

  设备              镜像            LAB 段地址(v6 / v4)          entrypoint                          作用
  gateway           kathara/base    2001:db8:1::1  192.168.0.1   shared_data/srv_entrypoint.sh + gateway.startup   路由器+NAT 出海口，额外 bridged 一块 eth1
  dns               kathara/bind    2001:db8:1::53 192.168.0.53  srv_entrypoint.sh + dns.startup                  BIND9 权威 + DNS64
  nat64             kathara/base    2001:db8:1::64 192.168.0.64  srv_entrypoint.sh + nat64.startup                Jool NAT64（stateful）
  siit              kathara/base    2001:db8:1::46 192.168.0.46  srv_entrypoint.sh + siit.startup                 Jool SIIT（stateless + EAMT）
  dual_client       kathara/base    2001:db8:1::10 192.168.0.10  test_runner.sh                                  双栈客户端
  ipv4_client       kathara/base    无 v6          192.168.0.40  test_runner.sh                                  纯 IPv4 客户端（lab.conf 里 [ipv6]="false"）
  ipv6_strict_client kathara/base   2001:db8:1::60 无 v4         test_runner.sh + ipv6_strict_client.startup      IPv6-only-strict（主动封掉 NAT64）
  ipv6_nat64_client kathara/base    2001:db8:1::664 无 v4        test_runner.sh                                  IPv6-only + DNS64/NAT64 客户端

  注意：只有 gateway 是 [bridged]="true"（多一块 eth1 接 docker0）；nat64 / siit 都没有第二个接口，
  它们的出网完全靠 gateway 转发 + NAT。

A2. 网络与地址规划
  · 只有一个碰撞域 "LAB"（lab.conf 里所有设备都是 [0]="LAB"）。v4 段 192.168.0.0/24 和 v6 段 2001:db8:1::/64
    共用同一块 eth0，没有路由器边界——所以"谁转发"完全由 /etc/hosts 无关的路由表决定：
    所有非 gateway 设备的默认路由都指向 2001:db8:1::1 / 192.168.0.1（shared.startup 里写死）。
  · 地址里的"语义编号"是给人看的：::53=dns、::64=nat64、::46=siit、::664=nat64 客户端。

A3. 启动顺序（lab.dep）
  dns: gateway
  nat64: dns
  siit: dns
  dual_client: dns
  ipv4_client: siit
  ipv6_strict_client: dns
  ipv6_nat64_client: nat64
  → gateway 先起（否则 dns 拿不到默认路由），dns 起来后 nat64/siit/客户端才起；
    ipv4_client 特意排在 siit 之后，ipv6_nat64_client 排在 nat64 之后。

A4. 每个节点到底跑什么（逐脚本）

  shared.startup（所有节点共用，Kathará 先跑 .startup 再跑 entrypoint）
    - 清空 /etc/resolv.conf，然后按 lab.conf 注入的 IPv6_ADDR / IPv4_ADDR 加地址、写 nameserver
      （有 v6 → 2001:db8:1::53；有 v4 → 192.168.0.53），非 gateway 设备补默认路由。最后 ip link set eth0 up。
    - 结果：v6-only 客户端拿到的是**只有 v6 地址的 resolver 条目**，v4 客户端只有 v4 条目，dual 两条都有。
      这是"客户端地址族决定 DNS 走哪条路"的实现基础。

  gateway.startup
    - net.ipv4.ip_forward=1 + net.ipv6.conf.all.forwarding=1
    - ip -6 route add 64:ff9b::/96 via 2001:db8:1::64   → 把预置前缀 64:ff9b::/96 全部指向 NAT64
    - ip route add 192.168.46.0/24 via 192.168.0.46     → SIIT 的 v4 侧地址段
    - ip -6 route add 2001:db8:4::/120 via 2001:db8:1::46 → SIIT 的 v6 侧地址段
    - iptables/ip6tables -t nat POSTROUTING -o eth1 -j MASQUERADE → 对 docker0 侧做双栈出网 NAT

  dns（镜像 kathara/bind，跑真 BIND9）
    - dns.startup：mv /etc/bindfiles/* /etc/bind/ → exec named -c /etc/bind/named.conf
    - named.conf 依次 include options / local / default-zones / **lab-zones**（lab-zones 是 zonefile_creator.py 生成的，
      没有它 named 直接起不来，这是"必须先跑 zonefile_creator"的原因）
    - named.conf.options 关键两行：
        dnssec-validation false;
        dns64 64:ff9b::/96 { clients { any; }; };     ← DNS64 对**所有**客户端生效
    - 没有配置 forwarders，所以 lab 之外的域名靠 named 自己递归（要经过 gateway 出网）。

  nat64（stateful NAT64，Jool 4.1.15）
    - apt update && apt install /jool_debfiles/jool-*（deb 直接放进仓库，不依赖外部源）
    - 开双栈转发 → modprobe jool → jool instance add "nat64" --netfilter --pool6 64:ff9b::/96
    - --netfilter 模式：由 Jool 自己往 iptables 里装 nat64 规则（不是 TUN 模式），IPv6 包按 pool6 前缀抽 v4 出来。

  siit（stateless SIIT，Jool SIIT 4.1.15）
    - 同样装 deb、开转发
    - BASE_IPV6="$(dig "${BASE_DOMAIN}" @8.8.8.8 aaaa ...)"   ← 算了但**从未使用**（见 D 区第 2 条）
    - modprobe jool_siit → jool_siit instance add "siit" --netfilter
    - eamt add 2001:db8:4::/120 192.168.0.0/24          （整段 lab v4 映射到 2001:db8:4::/120）
    - eamt add 2a00:1450:4001:c21::8b/128 192.168.46.1/32 （单个外部 v6 端点 ↔ 192.168.46.1）
    - 也就是说 "IPv4 客户端访问 IPv6-only 服务器" 这一路，目标 v6 地址是**硬编码的一个 Google 地址**。

  ipv6_strict_client.startup
    - ip -6 route add unreachable 64:ff9b::/96
    - ip6tables -A OUTPUT -d 64:ff9b::/96 -j REJECT
    - 目的：即使 DNS 给了合成 AAAA，也让它完全不可达 → 真正的 IPv6-only-strict（无任何 IPv4 能力、无 NAT64 逃生口）。

  客户端 test_runner.sh（四个客户端共用）
    1. source /shared/env/test_vars.env（BASE_DOMAIN / BASE_PROTO / 各变量）+ credentials.env（可选）
    2. 等 DNS：until nslookup ${BASE_DOMAIN} 成功（60s 超时）
    3. pip install "curlify2<2.0.0,>=1.0.1" + scanapi==2.13.2（--break-system-packages --no-cache-dir）
       ← 每个客户端容器**每次运行都要联网装一遍**（这就是对出网/镜像自带包的现实依赖）
    4. 若 sdom=siit：先 nc -z 192.168.46.1 <80|443> 等 SIIT 起来（60s）
       若 hostname=ipv6_nat64_client 且 sdom=ipv4：先 ping -c1 64:ff9b::192.168.0.64 等 NAT64 起来（60s）
    5. 对 Sdoms 里的每个 sdom：
         export BASE_URL="${BASE_PROTO}://${sdom}.lab.${BASE_DOMAIN}"
         scanapi run -o /shared/results/${HOSTNAME}-${sdom}-report.csv \
                     -t /shared/shared_data/csv_template.jinja /shared/shared_data/scanapi.yaml \
                     > /shared/results/logs/${HOSTNAME}-${sdom}.log 2>&1
         sed -i 给 CSV 每行行首插 "\"${HOSTNAME}\","      ← client_name 列（commit 6f7c899 加的）
    6. 脚本结束 → 容器退出（没有 set -e，任何一步失败都继续往下跑）

  srv_entrypoint.sh（gateway/dns/nat64/siit 四台共用，是"收工"机制）
    - sleep 30，然后对 4 个客户端 IP 逐个 `while ping -c1 -W1 <ip>; do sleep 1; done` —— 等到 ping 不通（容器已停）
    - 四个都离线后 exit → 容器停 → run_lab.sh 里阻塞着的 `kathara exec gateway sleep infinity` 返回 → lclean
    - 即：**测试结束的判据是"客户端容器全停"，用 ping 存活来探测**。

A5. 编排（run_lab.sh）
    kathara linfo | grep "No Devices Found" ?  : kathara lclean      # 先清残留
    sudo kathara lstart --noterminals -d kathara/                     # 起拓扑（不开终端窗口）
    kathara exec -d kathara/ gateway sleep infinity                   # 阻塞，直到 gateway 容器消失
    kathara lclean                                                    # 收尾

A6. 架构图（ASCII）

                        外部世界 (Internet)
                    ┌───────────┴───────────┐
                    │  gateway.eth1 (bridged → docker0)  │  MASQUERADE 双栈
                    │  gateway = 2001:db8:1::1 / 192.168.0.1
                    └───────────┬───────────┘
   ═════════════════════════════╪═════════════════════════════════════════════════════
        LAB 单段（2001:db8:1::/64 + 192.168.0.0/24，全部设备同一块 eth0）
   ═════════════════════════════╪═════════════════════════════════════════════════════
        │                │                │                 │
   ┌────┴────┐    ┌──────┴──────┐  ┌──────┴──────┐   ┌──────┴───────────────┐
   │ dns     │    │ nat64       │  │ siit        │   │ 4 个客户端           │
   │ ::53    │    │ ::64        │  │ ::46        │   │ dual  ::10 / .10     │
   │ 192.0.53│    │ 192.168.0.64│  │ 192.168.0.46│   │ ipv4  .40            │
   │ BIND9   │    │ Jool NAT64  │  │ Jool SIIT   │   │ strict ::60 (+开火墙)│
   │ +DNS64  │    │ pool6       │  │ EAMT ×2     │   │ nat64 ::664          │
   └─────────┘    └─────────────┘  └─────────────┘   └──────────────────────┘
         │              │                │                    │
         │              │                └─ 2a00:1450:...::8b ← 硬编码外部 v6
         │              └─ 192.168.0.0/24 (v4 服务) ←── 外部 v4
         └─ 权威区 lab.<DOMAIN>：dual/ipv4/ipv6/siit/ns

   客户端 Sdoms（决定了每个客户端打哪几个域名）：
     dual_client        : dual  ipv4  ipv6      (v4+v6 都有)
     ipv4_client        : dual  ipv4  siit      (只有 v4)
     ipv6_strict_client : dual  ipv6            (只有 v6，且封 64:ff9b::/96)
     ipv6_nat64_client  : ipv4  ipv6            (只有 v6，靠 DNS64+NAT64)

A7. 四条数据流（DNS 名 → 实际路径）

  (1) dual / ipv4 域名       客户端 → (v4 或 v6) 真实服务器（区内 A/AAAA 直接抄外部域名的记录）
  (2) dual_client 走 v6 分支 客户端 → gateway → docker0 → 外部（需要 host 有 v6 出网）
  (3) ipv4.lab.X + nat64 客户端
       客户端只发 DNS A 查询 → BIND 无 AAAA → DNS64 合成 64:ff9b::<A 的 v4> 
       → 客户端路由表把 64:ff9b::/96 丢给 gateway → gateway 转给 nat64 → Jool 抽出 v4 → 前往 192.168.0.x
  (4) siit.lab.X + ipv4 客户端
       区内记录 siit.lab.X → A 192.168.46.1 → gateway（192.168.46.0/24 via siit）→ siit EAMT
       → 2a00:1450:4001:c21::8b → siit 的 v6 默认路由 → gateway → 外部（同样需要 host v6 出网）

────────────────────────────────────────────────────────────
PART B　draft-ietf-v6ops-ipv6-app-testing 与本仓库的映射
────────────────────────────────────────────────────────────

B1. draft §3.1 Table 1 原表（client × server）

   #   Client                 Server                 分类
   1   Dual-stack             IPv4-only              base
   2   Dual-stack             IPv6-only-strict       base
   3   IPv4-only              Dual-stack             base
   4   IPv6-only with NAT64   IPv4-only              base
   5   IPv6-only-strict       Dual-stack             base
   6   IPv4-only              IPv6-only with NAT64   IPv6-only-DC
   7   Dual-stack             Dual-stack             extended
   8   IPv4-only              IPv4-only              extended
   9   IPv6-only with NAT64   IPv6-only-strict       extended
   10  IPv6-only-strict       IPv6-only-strict       extended

B2. V6Bench 实际跑出来的 12 个 (客户端 × 域名) 组合

  客户端（=draft 的 client 角色）   sdom      区内记录    实际路径        落到的 draft 场景
  dual_client      (v4+v6)        dual      A+AAAA      v4 或 v6          #7  Dual→Dual            (extended)
  dual_client                     ipv4      A only      v4                #1  Dual→IPv4-only        (base) ✓
  dual_client                     ipv6      AAAA only   v6                #2  Dual→IPv6-only-strict  (base, 近似)
  ipv4_client      (v4)           dual      A+AAAA      v4（只取 A）      #3  IPv4-only→Dual        (base) ✓
  ipv4_client                     ipv4      A only      v4                #8  IPv4-only→IPv4-only    (extended)
  ipv4_client                     siit      A=192.168.46.1 → SIIT → v6       #6  IPv4-only→v6-only(NAT64 侧) (IPv6-only-DC)
  ipv6_strict      (v6)           dual      A+AAAA      v6                #5  v6-only-strict→Dual    (base) ✓
  ipv6_strict                     ipv6      AAAA only   v6                #10 v6-only-strict→v6-only-strict (extended)
  ipv6_nat64       (v6+DNS64)     ipv4      A only      DNS64→NAT64→v4     #4  v6-only+NAT64→IPv4-only (base) ✓
  ipv6_nat64                      ipv6      AAAA only   ���生 v6            #9  v6-only+NAT64→v6-only-strict  (extended)

B3. 结论性映射表（draft 场景 → 实现状态）

  场景                                        状态      说明
  1  Dual→IPv4-only                            已实现    dual_client 打 ipv4.lab.X，区内只有 A
  2  Dual→IPv6-only-strict                     近似      "服务器 strict" 只是"客户端只看到 AAAA"，
                                                         服务器本身仍可能有 IPv4（lab 无法约束外部服务器）
  3  IPv4-only→Dual                            已实现    ipv4_client 打 dual.lab.X，只取 A
  4  IPv6-only+NAT64→IPv4-only                 已实现    ipv6_nat64_client 打 ipv4.lab.X，DNS64 合成 + Jool NAT64
  5  IPv6-only-strict→Dual                     已实现    ipv6_strict_client 打 dual.lab.X，取 AAAA，且已封 64:ff9b::/96
  6  IPv4-only→IPv6-only(NAT64) / IPv6-only-DC 部分     用 **SIIT(EAMT)** 而不是 stateful NAT64 实现，且目标 v6 地址硬编码
                                                         (2a00:1450:4001:c21::8b)。nat64 节点没有再被 v4 侧客户端使用过。
  7  Dual→Dual                                 已实现    dual_client 打 dual.lab.X（extended）
  8  IPv4-only→IPv4-only                       已实现    ipv4_client 打 ipv4.lab.X（extended）
  9  v6-only+NAT64→v6-only-strict              已实现    ipv6_nat64_client 打 ipv6.lab.X（走原生 v6，没走 NAT64）
  10 v6-only-strict→v6-only-strict             已实现    ipv6_strict_client 打 ipv6.lab.X（extended；同 #2 的"strict"保留意见）

  → 5 个 base 场景：4 个完整实现（#1/#3/#4/#5），#2 为"服务器侧 strict"的近似。
  → IPv6-only-DC(#6) 是唯一有实质替代实现（SIIT）的场景。
  → extended 4 个全部有对应。

B4. draft 其他章节的覆盖情况

  §3.2 中间盒/代理（Proxy / TURN / MASQUE）        未实现。拓扑里没有代理节点，scanapi 也不发 CONNECT。
  §3.3.1 缺失 DNS 记录                              半可做：改 db.lab 删掉 A 或 AAAA 即可，但没有内置开关/生成入口。
  §3.3.2 错误 DNS 记录（指向别处、IPv4-mapped AAAA） 未实现（同样可手改区文件模拟）。
  §3.3.3 DNS 委派问题（RFC10001）                   部分：区内自带 NS 记录，但 DEFAULT_NS 的 v6 地址与实际不符（见 D-1）；
                                                   没做 "v6-only-strict resolver 能否解析" 的显式用例。
  §3.3.4 IP 字面量（RFC4291 各种表示 + RFC9844 zone id） 未实现：测试 URL 一律是 {dual,ipv4,ipv6,siit}.lab.<DOMAIN>。
  §3.3.5 link-local 名字（.local / RFC6763）        未实现。
  §3.4 半残连接 / MTU / 分片                        部分：只模拟了"v6-only 客户端没有 NAT64 可达性"（REJECT+unreachable），
                                                   没有 MTU/黑洞/单族丢包/"TCP 通但 TLS 挂" 的模拟。
  §3.5 去掉 127.0.0.0/8 回环                          未实现。ipv6_strict_client 只是没有 v4 地址，容器内 127.0.0.1 仍在。
  §3.6 生命周期（安装/UI/管理/更新）                  仅"正常运行"（scanapi 打 API）。安装面唯一的痕迹是每个客户端
                                                   容器里 pip install scanapi —— 但这不是被测应用的生命周期测试。
  §3.7 复杂云应用 / 逐条数据流                        未实现（单端点 API 打点）。
  §3.8 Web 应用（含第三方资源、Selenium）             未实现（ScanAPI 只打 OpenAPI 里的接口，不加载页面资源）。
  §3.9 地址作为数据（日志/管理里的 IPv6 表示）        未实现（报告 CSV 只记录 URL 和成功率，不校验地址表示）。

────────────────────────────────────────────────────────────
PART C　这台机器上的环境就绪状态（已实测）
────────────────────────────────────────────────────────────

结论：拓扑**能起来**，8 个设备全起来了，lab 内部的 DNS / DNS64 / NAT64 / SIIT / 路由 / 地址族隔离全部验证通过；
但"出网"只通了 IPv4 那半边，所有需要原生 IPv6 出网的场景在这台机器上必然失败。

C1. 实测通过的部分（下面每条都有真实命令输出支撑，时间为 2026-11-02 19:30-19:50）

  项                                  实测结果
  8 设备启动                          ✓ [Deploying devices] 8/8；gateway/dns/nat64/siit + 4 客户端
  地址规划                            ✓ gateway eth0 2001:db8:1::1 + 192.168.0.1，eth1 172.17.0.3（接 docker0）
                                        dns ::53 / nat64 ::64 / siit ::46 / dual ::10 / ipv4 .40 / strict ::60 / nat64_client ::664
                                        strict 客户端 eth0 上 v6 地址数=1、v4 地址数=0（真正的单栈）
  区内 DNS                            ✓ dual → A 110.242.70.57/.69.21 + AAAA 2408:871a:...（各 2 条）
                                        ipv6 → 只有 AAAA；siit → A 192.168.46.1；ns → 192.168.0.53
  DNS64 合成                          ✓ ipv4.lab.X 的 AAAA 查询返回 64:ff9b::6ef2:4639 与 64:ff9b::6ef2:4515
                                        （正是 110.242.70.57 / 110.242.69.21 的 RFC6052 编码）
                                        客户端视角（在 ipv6_nat64_client 里 dig）同样拿到这两条
  Jool NAT64                          ✓ nat64 容器里 `jool instance display` → nat64 / netfilter 实例存在
  经 NAT64 真出网                      ✓ ipv6_nat64_client 内 `nc -z 64:ff9b::6ef2:4639 443` 成功 → 纯 v6 客户端能打 IPv4 互联网
                                        （test_runner 的等待条件 ping 64:ff9b::192.168.0.64 也 OK）
  Jool SIIT                           ✓ siit 容器里 siit/netfilter 实例存在；`jool_siit -i siit eamt display` 输出正是脚本里那两条：
                                        2a00:1450:4001:c21::8b/128 <-> 192.168.46.1/32
                                        2001:db8:4::/120 <-> 192.168.0.0/24
  gateway 转发/NAT                    ✓ iptables/ip6tables POSTROUTING -o eth1 MASQUERADE 两条都在
                                        v6 路由 64:ff9b::/96 via ::64、2001:db8:4::/120 via ::46 都在；v4 默认经 172.17.0.1 出 docker0
  strict 客户端隔离                   ✓ 路由表里有 unreachable 64:ff9b::/96；`nc -z 64:ff9b::...:443` 被拒（STRICT_BLOCKED，没漏 NAT64）
  双栈客户端 v4 路径                  ✓ dual_client `nc -z 110.242.70.57 443` 成功
  ipv4 客户端 v4 路径                 ✓ ipv4_client `nc -z 110.242.70.57 443` 成功
  生命周期                            ✓ 第一次实跑（客户端未装 scanapi 直接退出）后，四台服务节点按 srv_entrypoint 逻辑自行退出，
                                        整个 lab 自毁——说明"等客户端离线 → 关服务 → gateway 退出 → run_lab 返回"的链路是通的

C2. 实测失败的部分（都是同一个根因：host 没有 IPv6 出网）

  项                        实测
  host IPv6 出网            ✗ 只有 2001:dc7:dd00:6400::40/128（/128，无 ::/0）；ping6 2400:3200::1 100% 丢包
  gateway eth1 的 v6        ✗ 只有 fe80::42:acff:fe11:3/64，没有全局 v6，也没有 v6 默认路由
  strict 客户端原生 v6      ✗ nc -z <baidu AAAA> 443 → V6_FAIL
  dual 客户端 v6 分支       ✗ 同上 → DUAL_V6_FAIL
  SIIT 场景                ✗ ipv4_client `nc -z 192.168.46.1 443` → SIIT_FAIL
                              （包能被 SIIT 翻译成 v6，但翻译完要走 v6 出网，host 没 v6 → 黑洞）
  scanapi 安装             ✗ 全部 4 个客户端容器里 pip 都失败；ipv6_strict_client 是 `[Errno 101] Network is unreachable`
                              （无 v4 也没有 v6 出网），进而 scanapi 不存在、报告 CSV 不存在、sed 报
                              "can't read /shared/results/ipv6_strict_client-dual-report.csv"、容器 Exited(2)

  → 也就是说：本机能验证"矩阵的左半边"（IPv4 直连 + NAT64→IPv4），整个右半边（原生 IPv6 指向真实服务器、
    strict 客户端、SIIT）必须先把 host 的 IPv6 默认路由解决掉，或者把被测服务搬进 lab。
  → 另外，scanapi 是每个客户端容器运行时 pip 安装的，即便 v6 通了，strict 客户端也依赖"v6 能到 PyPI"，
    这在纯 v6 环境里是脆弱点（建议把 scanapi 预装进镜像）。

C3. 想复现这次成功启动，需要绕过三个本机特有的坑

  坑 1  Docker Hub 与本机 daemon.json 里的三个 mirror 全不可用
        · registry-1.docker.io 超时；USTC/163/百度 mirror 全部失效
        · 可用的是 docker.1ms.run（镜像站能出 manifest，但 blob 走 Cloudflare 会随机 connection reset）
        · 绕法：在本地起一个带 skopeo 的容器，`skopeo copy --retry-times 20 docker://docker.1ms.run/kathara/base docker-daemon:kathara/base:latest`
          （skopeo 逐 blob 重试比 docker pull 稳），bind 同理
  坑 2  Kathara 网络插件必须存在，但 `docker plugin install` 只会去 registry 拉
        · 先 `skopeo copy ... dir:/tmp/np` 拿到插件配置 blob + 层
        · 解开层到 rootfs，把配置 blob 存成 config.json
        · `docker plugin create kathara/katharanp_vde:amd64 /tmp/npimg` → kathara lstart 时会自动 enable
  坑 3  本机 docker 是 UOS 定制的 docker-ce 19.03.8.2，Server 版本号报 "dev"
        · Kathara 3.8.3 的 version_lt("dev","26.0.0") → int('') → ValueError，直接起不来
        · 绕法：把 Kathara/utils.py 的 parse_docker_engine_version 末尾改成
          `return version if version else "19.03"`（只改 venv 里的包，不影响仓库）

  以及一件必须做但仓库没写的事：先跑 zonefile_creator.py 生成 db.lab，否则 named 因 include 失败而起不来。

C4. 一键复现（本机已验证过的路径）

   VENV=/home/kyu/.hermes/profiles/coder/cache/scratch/kvenv
   KATHARA="$VENV/bin/python $VENV/lib/python3.13/site-packages/kathara.py"
   python3 v6bench/zonefile_creator.py <有 A 且有 AAAA 的域名>
   $KATHARA lstart --noterminals -d v6bench/kathara     # 需要 root：nat64/siit 是 privileged
   # 验证
   docker exec <dns容器> dig +short ipv4.lab.<域名> AAAA        # 期望 64:ff9b::<v4>
   docker exec <nat64客户端> nc -z 64:ff9b::<某 v4 地址> 443   # 期望成功
   $KATHARA lclean -d v6bench/kathara

PART D　读代码时记下的可疑点（按影响排序）
────────────────────────────────────────────────────────────

D-1 zonefile_creator.py 的 DEFAULT_NS 里 v6 地址是 2001:db8::53，而 lab.conf 给 dns 的是 2001:db8:1::53。
    区文件的 ns.lab 的 AAAA 指向一个不存在的地址。当前不影响主流程（客户端不解析 ns.lab），
    但任何"解析 NS 再查"的路径都会失败，也直接违反 draft §3.3.3 想测的东西。

D-2 siit.startup 里 BASE_IPV6=$(dig BASE_DOMAIN @8.8.8.8 aaaa) 算了却**从未使用**；
    真正执行的是 eamt add 2a00:1450:4001:c21::8b/128 192.168.46.1/32 —— 一个 Google 的硬编码地址。
    含义：siit 场景只对"恰好是这个 IP 的服务器"有效，换被测服务就得手改脚本。
    另外这条 dig 依赖 8.8.8.8 可达（国内常被拦），失败也不报错。

D-3 named.conf.options 的 dns64 配了 clients { any; }：
    DNS64 对所有客户端生效，包括 dual_client。dual_client 解析 ipv4.lab.X 时会同时拿到 A 和
    **合成 AAAA 64:ff9b::192.168.0.x**；按 RFC 6724 排序 IPv6 优先，它可能改走 NAT64 出去。
    那 #1（Dual→IPv4-only）测的就不再是"客户端用 A 直连 v4"，场景被污染。
    真实部署里 DNS64 只对 v6-only 客户端的那台 resolver 开。

D-4 siit 的 EAMT 把整个 192.168.0.0/24 映射进 2001:db8:4::/120，同时又给 gateway 配了
    2001:db8:4::/120 via siit 的 v6 路由。lab 内任何 v4 地址都被"翻译成一个 v6 身份"，
    这条映射比测试需要的大得多，容易掩盖/制造路由歧义。

D-5 .gitignore 写的路径是 v6bench/kathara/bind/db.lab 与 .../bind/named.conf.lab-zones，
    但 zonefile_creator.py 实际写到 v6bench/kathara/dns/etc/bindfiles/。
    → 跑一次生成脚本就会在仓库里留下未跟踪文件（git status 会脏）。

D-6 test_runner.sh 没有 set -e，且 pip install / scanapi run 失败都被吞掉；
    只有日志里能看到。报告 CSV 会"看起来跑完了但其实全空"。

D-7 test_runner.sh 里 `nslookup ${BASE_DOMAIN}` 等的是**外部域名**而不是 lab 域；
    v6-only 客户端在无 v6 出网时这条查询要等 forward 超时，60s 上限内可能刚好超。
    等 DNS 就绪的意图，被实现成了"等外网递归成功"。

D-8 srv_entrypoint.sh 用 ping 探测客户端是否离线来决定收工；ping 是 ICMP，某些环境下被禁，
    届时四台服务节点会一直卡住，run_lab.sh 也就永远卡在 `kathara exec gateway sleep infinity`。

D-9 test_runner 的 SIIT 等待写死 nc -z 192.168.46.1 ${TEST_PORT}，端口取自 BASE_PROTO（80/443）；
    若被测服务监听别的端口，这里的等待条件就是错的。

D-10 ipv4_client 在 lab.conf 里 [ipv6]="false"，但 shared.startup 不区分平台，只按 IPv6_ADDR 是否为空加地址；
     它的 resolv.conf 只有 192.168.0.53，理论上 OK，但意味着该节点无法验证"v6 接口存在但不可用"这种半残形态。
