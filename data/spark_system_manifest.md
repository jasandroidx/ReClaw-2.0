# Ravenstack System Architecture Manifest
Generated: Sun Aug 16 03:40:31 AM UTC 2026

## 1. Host & OS
```text
Linux openclaw 6.8.0-124-generic #124-Ubuntu SMP PREEMPT_DYNAMIC Tue May 26 13:00:45 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
NAME="Ubuntu"
VERSION="24.04.4 LTS (Noble Numbat)"
```

## 2. Tailscale & Funnel Status
```text
100.108.130.82  openclaw         jasonmboyd87@  linux    -                                                         
100.105.183.75  boydscomp        jasonmboyd87@  linux    active; direct 24.29.8.176:41641, tx 86604344 rx 7914652  
100.111.101.90  desktop-glsj8sc  jasonmboyd87@  windows  offline, last seen 22h ago                                
100.125.33.97   galaxy-a15-5g    jasonmboyd87@  android  active; direct 24.29.8.176:43925, tx 12319492 rx 4568164  

# Funnel on:
#     - https://openclaw.tail20a090.ts.net

--- Serve / Funnel Status ---

# Funnel on:
#     - https://openclaw.tail20a090.ts.net

https://openclaw.tail20a090.ts.net:8120 (tailnet only)
|-- / proxy http://127.0.0.1:8120

https://openclaw.tail20a090.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:3000

https://openclaw.tail20a090.ts.net:18789 (tailnet only)
|-- / proxy http://127.0.0.1:18789

https://openclaw.tail20a090.ts.net (Funnel on)
|-- / proxy http://127.0.0.1:8100

https://openclaw.tail20a090.ts.net:8000 (tailnet only)
|-- / proxy http://127.0.0.1:8000

https://openclaw.tail20a090.ts.net:8081 (tailnet only)
|-- / proxy http://127.0.0.1:8081

https://openclaw.tail20a090.ts.net:8100 (tailnet only)
|-- / proxy http://127.0.0.1:8100

https://openclaw.tail20a090.ts.net:8110 (tailnet only)
|-- / proxy http://127.0.0.1:8111


# Funnel on:
#     - https://openclaw.tail20a090.ts.net

https://openclaw.tail20a090.ts.net:18789 (tailnet only)
|-- / proxy http://127.0.0.1:18789

https://openclaw.tail20a090.ts.net (Funnel on)
|-- / proxy http://127.0.0.1:8100

https://openclaw.tail20a090.ts.net:8000 (tailnet only)
|-- / proxy http://127.0.0.1:8000

https://openclaw.tail20a090.ts.net:8081 (tailnet only)
|-- / proxy http://127.0.0.1:8081

https://openclaw.tail20a090.ts.net:8100 (tailnet only)
|-- / proxy http://127.0.0.1:8100

https://openclaw.tail20a090.ts.net:8110 (tailnet only)
|-- / proxy http://127.0.0.1:8111

https://openclaw.tail20a090.ts.net:8120 (tailnet only)
|-- / proxy http://127.0.0.1:8120

https://openclaw.tail20a090.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:3000

```

## 3. Docker Stack & Containers
```text
NAME               IMAGE                                COMMAND                  SERVICE            CREATED       STATUS                 PORTS
openclaw-gateway   ghcr.io/openclaw/openclaw:2026.7.1   "tini -s -- node ope…"   openclaw-gateway   3 days ago    Up 3 days (healthy)    127.0.0.1:18789->18789/tcp
reclaw-api         reclaw:2.0                           "uvicorn api.main:ap…"   reclaw-api         4 weeks ago   Up 3 weeks (healthy)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
reclaw-dashboard   python:3.12-slim                     "python3 -m http.ser…"   reclaw-dashboard   4 weeks ago   Up 3 weeks (healthy)   0.0.0.0:8081->8080/tcp, [::]:8081->8080/tcp
```

## 4. Active Crontab
```text
0 6 * * 1 /usr/bin/python3 /root/ReClaw-2.0/scripts/weekly_raziel_self_improve.py >> /root/ReClaw-2.0/data/mcp_logs/weekly_audit.log 2>&1
15 6 * * 1 /usr/bin/python3 /root/ReClaw-2.0/scripts/weekly_raziel_reflection.py >> /root/ReClaw-2.0/data/mcp_logs/weekly_reflection.log 2>&1
```

## 5. ReClaw Directory & Scripts Layout
```text
/root/ReClaw-2.0/data
/root/ReClaw-2.0/data/architectural_registry.yaml
/root/ReClaw-2.0/data/auditor_lessons_log.yaml
/root/ReClaw-2.0/data/audit_pipeline_mistakes.yaml
/root/ReClaw-2.0/data/audit_strategy.yaml
/root/ReClaw-2.0/data/audit_tool_candidates.yaml
/root/ReClaw-2.0/data/backups
/root/ReClaw-2.0/data/backups/fortress-harden-2026-07-19
/root/ReClaw-2.0/data/backups/openclaw-pre-drop-coder-20260719T042509Z.json
/root/ReClaw-2.0/data/backups/openclaw-pre-free-map-20260719T042036Z.json
/root/ReClaw-2.0/data/backups/openclaw-pre-gemini-pro-20260719T041131Z.json
/root/ReClaw-2.0/data/backups/openclaw-pre-oc-cloud-20260719T043107Z.json
/root/ReClaw-2.0/data/backups/rag_embeddings_archive_2026-08-16.tar.gz
/root/ReClaw-2.0/data/backups/sessions-purge-20260719T041301Z
/root/ReClaw-2.0/data/cache
/root/ReClaw-2.0/data/cache/dlgf
/root/ReClaw-2.0/data/cache/dogegpt
/root/ReClaw-2.0/data/cache/dogegpt_budgets
/root/ReClaw-2.0/data/cache/firecrawl
/root/ReClaw-2.0/data/cache/gateway_budget_data_2022.txt
/root/ReClaw-2.0/data/cache/gateway_budget_data_2023.txt
/root/ReClaw-2.0/data/cache/gateway_budget_data_2024.txt
/root/ReClaw-2.0/data/cache/gateway_budget_data_2025.txt
/root/ReClaw-2.0/data/cache/gateway_disbursements_2022.txt
/root/ReClaw-2.0/data/cache/gateway_disbursements_2023.txt
/root/ReClaw-2.0/data/cache/gateway_disbursements_2024.txt
/root/ReClaw-2.0/data/cache/gateway_disbursements_2025.txt
/root/ReClaw-2.0/data/cache/heat
/root/ReClaw-2.0/data/cache/salaries
/root/ReClaw-2.0/data/cache/sboa
/root/ReClaw-2.0/data/cache/socrata
/root/ReClaw-2.0/data/cache/upwork
/root/ReClaw-2.0/data/castle_map.json
/root/ReClaw-2.0/data/content_truth_rules.yaml
/root/ReClaw-2.0/data/county_queue
/root/ReClaw-2.0/data/county_queue/pending
/root/ReClaw-2.0/data/county_queue/state.json
/root/ReClaw-2.0/data/dogegpt_ingest_manifest.json
/root/ReClaw-2.0/data/dual_receipt_pilots
/root/ReClaw-2.0/data/dual_receipt_pilots/dual-winslow-water-2025-01.json
/root/ReClaw-2.0/data/dual_receipt_pilots/dual-winslow-water-2025-01.md
/root/ReClaw-2.0/data/fortress_state.json
/root/ReClaw-2.0/data/fraud_detection_framework.yaml
/root/ReClaw-2.0/data/fraud_scheme_taxonomy.yaml
/root/ReClaw-2.0/data/grant_digests
/root/ReClaw-2.0/data/grant_digests/2026-07-17-draft.md
/root/ReClaw-2.0/data/grant_digests/2026-07-22-draft.md
/root/ReClaw-2.0/data/grant_digests/2026-07-22-scored.md
/root/ReClaw-2.0/data/inbox
/root/ReClaw-2.0/data/inbox/books
/root/ReClaw-2.0/data/inbox/.gitkeep
/root/ReClaw-2.0/data/inbox/heat
/root/ReClaw-2.0/data/inbox/pdfs
/root/ReClaw-2.0/data/inbox/raw
/root/ReClaw-2.0/data/inbox/README.md
/root/ReClaw-2.0/data/inbox/socrata_chicago_test_20260706T095742Z.csv
/root/ReClaw-2.0/data/indiana_county_worklist.yaml
/root/ReClaw-2.0/data/indiana_public_finance_blueprint.yaml
/root/ReClaw-2.0/data/manifests
/root/ReClaw-2.0/data/manifests/gibson
/root/ReClaw-2.0/data/manifests/posey
/root/ReClaw-2.0/data/mcp_logs
/root/ReClaw-2.0/data/mcp_logs/2026-07-06.jsonl
/root/ReClaw-2.0/data/MCP_PUBLIC_PLANE.txt
/root/ReClaw-2.0/data/mcp_public_url.txt
/root/ReClaw-2.0/data/mcp_queue.jsonl
/root/ReClaw-2.0/data/mcp_tunnel_host.txt
/root/ReClaw-2.0/data/memory
/root/ReClaw-2.0/data/memory/reclaw_memory.db
/root/ReClaw-2.0/data/obsidian_fix_backlog.yaml
/root/ReClaw-2.0/data/openclaw_android_url.txt
/root/ReClaw-2.0/data/PERMANENT-OUTBOX-MEMORY.md
/root/ReClaw-2.0/data/public_data_sources.yaml
/root/ReClaw-2.0/data/public_source_map.yaml
/root/ReClaw-2.0/data/rag_chroma
/root/ReClaw-2.0/data/rag_chroma/a05ed378-d465-4189-adac-6213dd524e85
/root/ReClaw-2.0/data/rag_chroma/chroma.sqlite3
/root/ReClaw-2.0/data/rag_state
/root/ReClaw-2.0/data/rag_state/vault_sync_state.json
/root/ReClaw-2.0/data/reclaw_orchestration.yaml
/root/ReClaw-2.0/data/red_flag_taxonomy.yaml
/root/ReClaw-2.0/data/renders
/root/ReClaw-2.0/data/renders/gibson
/root/ReClaw-2.0/data/research
/root/ReClaw-2.0/data/research/algorithmic-auditing-public-finance-blueprint-2026-07-17.md
/root/ReClaw-2.0/data/runs
/root/ReClaw-2.0/data/runs/20260705_135406_pkg-dd1f4a2b83c0.json
/root/ReClaw-2.0/data/runs/20260705_135406_session-87911b6489a7
/root/ReClaw-2.0/data/runs/20260705_135424_pkg-cafc4e1a2e7e.json
/root/ReClaw-2.0/data/runs/20260705_135424_session-13aa0c3c4376
/root/ReClaw-2.0/data/runs/20260705_141023_pkg-9b2fe808ad26.json
/root/ReClaw-2.0/data/runs/20260705_141023_session-1105ab7febc0
/root/ReClaw-2.0/data/runs/20260705_141237_pkg-f01613ca2242.json
/root/ReClaw-2.0/data/runs/20260705_141237_session-2ff81ced3aa9
/root/ReClaw-2.0/data/runs/20260705_141427_pkg-26280758760b.json
/root/ReClaw-2.0/data/runs/20260705_141427_session-3075b3a0edb9
/root/ReClaw-2.0/data/runs/20260705_141441_pkg-0250dfda202c.json
/root/ReClaw-2.0/data/runs/20260705_141441_session-1a238032d108
/root/ReClaw-2.0/data/runs/20260705_141444_pkg-8a5b431f1a97.json
/root/ReClaw-2.0/data/runs/20260705_141444_session-3a463d30dbc5
/root/ReClaw-2.0/data/runs/20260705_141501_pkg-adcacc46eb17.json
/root/ReClaw-2.0/data/runs/20260705_141501_session-fe11cc3ce641
/root/ReClaw-2.0/data/runs/20260705_143356_pkg-add8744107d1.json
/root/ReClaw-2.0/data/runs/20260705_143356_session-c3c9955a6a6f
/root/ReClaw-2.0/data/runs/20260705_150200_pkg-113369be78ae.json
/root/ReClaw-2.0/data/runs/20260705_150200_session-a43dab43cdc5
/root/ReClaw-2.0/data/runs/20260705_150215_pkg-f85d30ead446.json
/root/ReClaw-2.0/data/runs/20260705_150215_session-cff433285aad
/root/ReClaw-2.0/data/runs/20260705_150524_pkg-77aebbfcaeb0.json
/root/ReClaw-2.0/data/runs/20260705_150524_session-ea87d2dc9a3f
/root/ReClaw-2.0/data/runs/20260705_152247_pkg-9490032c57df.json
/root/ReClaw-2.0/data/runs/20260705_152247_session-467515aab804
/root/ReClaw-2.0/data/runs/20260705_152258_pkg-658d543937f4.json
/root/ReClaw-2.0/data/runs/20260705_152258_session-ddec898d6595
/root/ReClaw-2.0/data/runs/20260705_152304_pkg-ba4ae118446d.json
/root/ReClaw-2.0/data/runs/20260705_152304_session-b42e3507cbb1
/root/ReClaw-2.0/data/runs/20260705_152847_pkg-597e5e30031b.json
/root/ReClaw-2.0/data/runs/20260705_152847_session-f23ae6c4fc01
/root/ReClaw-2.0/data/runs/20260705_153211_pkg-bc9bc2063360.json
/root/ReClaw-2.0/data/runs/20260705_153211_session-0af23fc8e4b2
/root/ReClaw-2.0/data/runs/20260705_153239_pkg-cde884012ff5.json
/root/ReClaw-2.0/data/runs/20260705_153239_session-63db595f96f1
/root/ReClaw-2.0/data/runs/20260705_165927_pkg-cbc175d61d86.json
/root/ReClaw-2.0/data/runs/20260705_165927_session-5b72778046d5
/root/ReClaw-2.0/data/runs/20260705_165945_pkg-60d2078bed8d.json
/root/ReClaw-2.0/data/runs/20260705_165945_session-133aee67aaf4
/root/ReClaw-2.0/data/runs/20260705_170205_pkg-ebe296050b05.json
/root/ReClaw-2.0/data/runs/20260705_170205_session-724b523ae6a3
/root/ReClaw-2.0/data/runs/20260705_170332_pkg-ffad7bee3845.json
/root/ReClaw-2.0/data/runs/20260705_170332_session-ff2d2ec176a9
/root/ReClaw-2.0/data/runs/20260705_181809_pkg-7610f7cbe526.json
/root/ReClaw-2.0/data/runs/20260705_181809_session-5406d781f0d4
/root/ReClaw-2.0/data/runs/20260705_181819_pkg-0ab7a4b60a1a.json
/root/ReClaw-2.0/data/runs/20260705_181819_session-a13f73bb5a3a
/root/ReClaw-2.0/data/runs/20260706_021956_pkg-2ea2a48182fa.json
/root/ReClaw-2.0/data/runs/20260706_021956_session-ea3bf4cf2911
/root/ReClaw-2.0/data/runs/20260706_025728_pkg-b8b27d34aa1d.json
/root/ReClaw-2.0/data/runs/20260706_025728_session-b05b474edacc
/root/ReClaw-2.0/data/runs/20260706_025830_pkg-08cde27cffad.json
/root/ReClaw-2.0/data/runs/20260706_025830_session-111b4854a34a
/root/ReClaw-2.0/data/runs/20260706_030423_pkg-8e9a1ee475e4.json
/root/ReClaw-2.0/data/runs/20260706_030423_session-457d41b070be
/root/ReClaw-2.0/data/runs/20260706_030943_pkg-b2badac54eb9.json
/root/ReClaw-2.0/data/runs/20260706_030943_session-7559634a9412
/root/ReClaw-2.0/data/runs/20260706_030950_pkg-fc1b0632afeb.json
/root/ReClaw-2.0/data/runs/20260706_030950_session-c7327deb0f6f
/root/ReClaw-2.0/data/runs/20260706_031110_pkg-26f8bf7de241.json
/root/ReClaw-2.0/data/runs/20260706_031110_session-f5f9b3088375
/root/ReClaw-2.0/data/runs/20260706_080012_pkg-f5ad7141ab19.json
/root/ReClaw-2.0/data/runs/20260706_080012_session-30c596c231e6
/root/ReClaw-2.0/data/runs/20260706_094109_pkg-f5c371c9c56b.json
/root/ReClaw-2.0/data/runs/20260706_094109_session-e011994c448d
/root/ReClaw-2.0/data/runs/20260706_094154_pkg-545113945e16.json
/root/ReClaw-2.0/data/runs/20260706_094154_session-bdedeef79ab5
/root/ReClaw-2.0/data/runs/20260706_094438_pkg-2d2be78437a9.json
/root/ReClaw-2.0/data/runs/20260706_094438_session-b6f50ce3d0a3
/root/ReClaw-2.0/data/runs/20260706_094612_pkg-73fbb5583803.json
/root/ReClaw-2.0/data/runs/20260706_094612_session-947c2787eb77
/root/ReClaw-2.0/data/runs/20260706_095129_pkg-32e330daea57.json
/root/ReClaw-2.0/data/runs/20260706_095129_session-ebe5d5819641
/root/ReClaw-2.0/data/runs/20260707_052201_pkg-c14eae1f79fc.json
/root/ReClaw-2.0/data/runs/20260707_052201_session-7c748f3c0408
/root/ReClaw-2.0/data/runs/20260707_080012_pkg-da5aac18d2a5.json
/root/ReClaw-2.0/data/runs/20260707_080012_session-69ac63f92fa6
/root/ReClaw-2.0/data/runs/20260707_120626_pkg-d679ebc6e988.json
/root/ReClaw-2.0/data/runs/20260707_120626_session-2ba3c959a2a7
/root/ReClaw-2.0/data/runs/20260708_080014_pkg-beabeb8fb9ad.json
/root/ReClaw-2.0/data/runs/20260708_080014_session-965ffa7355db
/root/ReClaw-2.0/data/runs/20260709_080026_pkg-7d66d2196768.json
/root/ReClaw-2.0/data/runs/20260709_080026_session-92197a43c0b0
/root/ReClaw-2.0/data/runs/20260710_080017_pkg-a4f8ce19b9a8.json
/root/ReClaw-2.0/data/runs/20260710_080017_session-c72d0822c608
/root/ReClaw-2.0/data/runs/20260711_080106_pkg-a4a6cf324d0c.json
/root/ReClaw-2.0/data/runs/20260711_080106_session-cc7668d06dc1
/root/ReClaw-2.0/data/runs/20260712_080037_pkg-9001caef1eb1.json
/root/ReClaw-2.0/data/runs/20260712_080037_session-8033bee8986e
/root/ReClaw-2.0/data/runs/20260713_080035_pkg-954ed4ca2fb4.json
/root/ReClaw-2.0/data/runs/20260713_080035_session-989f9fa1fcd6
/root/ReClaw-2.0/data/runs/20260714_080042_pkg-22b1ea661380.json
/root/ReClaw-2.0/data/runs/20260714_080042_session-d0ce92e4dc63
/root/ReClaw-2.0/data/runs/20260715_080039_pkg-e6ac6268e670.json
/root/ReClaw-2.0/data/runs/20260715_080039_session-50ff243db7fb
/root/ReClaw-2.0/data/runs/20260716_080039_pkg-830d8978b991.json
/root/ReClaw-2.0/data/runs/20260716_080039_session-b0894e7a18fb
/root/ReClaw-2.0/data/runs/20260717_054226_pkg-90255d1c78bc.json
/root/ReClaw-2.0/data/runs/20260717_054226_session-d85e555f7709
/root/ReClaw-2.0/data/runs/20260717_054256_pkg-c9fd40fdf178.json
/root/ReClaw-2.0/data/runs/20260717_054256_session-c0ed66f8748f
/root/ReClaw-2.0/data/runs/20260717_054324_pkg-57020a473baf.json
/root/ReClaw-2.0/data/runs/20260717_054324_session-96275a470e61
/root/ReClaw-2.0/data/runs/20260717_054403_pkg-77335acc4e26.json
/root/ReClaw-2.0/data/runs/20260717_054403_session-659cce41db2d
/root/ReClaw-2.0/data/runs/20260717_054440_pkg-7710c2e3d403.json
/root/ReClaw-2.0/data/runs/20260717_054440_session-7a4fcab7e3f7
/root/ReClaw-2.0/data/runs/20260717_054520_pkg-6969ae6230ec.json
/root/ReClaw-2.0/data/runs/20260717_054520_session-538a31a16b5e
/root/ReClaw-2.0/data/runs/20260717_054605_pkg-0cfaaae6f59c.json
/root/ReClaw-2.0/data/runs/20260717_054605_session-01acc87282b3
/root/ReClaw-2.0/data/runs/20260717_054713_pkg-c67b8cc95872.json
/root/ReClaw-2.0/data/runs/20260717_054713_session-24b1edac3fa3
/root/ReClaw-2.0/data/runs/20260717_055054_pkg-02922ea26a44.json
/root/ReClaw-2.0/data/runs/20260717_055054_session-e2d45a67bc36
/root/ReClaw-2.0/data/runs/20260717_055226_pkg-eed91649617b.json
/root/ReClaw-2.0/data/runs/20260717_055226_session-9375ae493295
/root/ReClaw-2.0/data/runs/20260717_080034_pkg-b887661e4fd0.json
/root/ReClaw-2.0/data/runs/20260717_080034_session-69cfd9fa2ae0
/root/ReClaw-2.0/data/runs/20260718_080106_pkg-b803497e075e.json
/root/ReClaw-2.0/data/runs/20260718_080106_session-1f1ca797d1f0
/root/ReClaw-2.0/data/runs/20260719_080109_pkg-42b162828636.json
/root/ReClaw-2.0/data/runs/20260719_080109_session-9e39ed620760
/root/ReClaw-2.0/data/runs/20260720_080108_pkg-75d84a28a451.json
/root/ReClaw-2.0/data/runs/20260720_080108_session-008aee7defe0
/root/ReClaw-2.0/data/runs/20260721_080038_pkg-6002920794fa.json
/root/ReClaw-2.0/data/runs/20260721_080038_session-85e74b4734cf
/root/ReClaw-2.0/data/runs/20260722_080037_pkg-bccfe7871af5.json
/root/ReClaw-2.0/data/runs/20260722_080037_session-c563dc227cd8
/root/ReClaw-2.0/data/runs/20260723_080036_pkg-81fddc8ea503.json
/root/ReClaw-2.0/data/runs/20260723_080036_session-6d2c487dfdba
/root/ReClaw-2.0/data/runs/20260724_080037_pkg-890b005923a2.json
/root/ReClaw-2.0/data/runs/20260724_080037_session-13b90efccb4e
/root/ReClaw-2.0/data/runs/20260725_080035_pkg-4c4ae58ebb68.json
/root/ReClaw-2.0/data/runs/20260725_080035_session-5a1cc87e27a3
/root/ReClaw-2.0/data/runs/20260726_080036_pkg-38122244d11f.json
/root/ReClaw-2.0/data/runs/20260726_080036_session-99a7d408c304
/root/ReClaw-2.0/data/runs/20260727_080036_pkg-4b0d6848a035.json
/root/ReClaw-2.0/data/runs/20260727_080036_session-455bb698b9d0
/root/ReClaw-2.0/data/runs/20260728_080301_pkg-030701c0c8d9.json
/root/ReClaw-2.0/data/runs/20260728_080301_session-d02fc06c502f
/root/ReClaw-2.0/data/runs/20260729_022713_pkg-a8167333b010.json
/root/ReClaw-2.0/data/runs/20260729_022713_session-186a1749cbb8
/root/ReClaw-2.0/data/runs/20260729_022749_pkg-a98726386aef.json
/root/ReClaw-2.0/data/runs/20260729_022749_session-e78c8b7428f8
/root/ReClaw-2.0/data/runs/20260729_080037_pkg-759b17fba526.json
/root/ReClaw-2.0/data/runs/20260729_080037_session-6cd22115b02c
/root/ReClaw-2.0/data/runs/20260730_080038_pkg-443fdb0d9561.json
/root/ReClaw-2.0/data/runs/20260730_080038_session-d03585499464
/root/ReClaw-2.0/data/runs/20260731_080036_pkg-378e2995f02d.json
/root/ReClaw-2.0/data/runs/20260731_080036_session-c67ef92b3dc2
/root/ReClaw-2.0/data/runs/20260801_080036_pkg-8eee7f249145.json
/root/ReClaw-2.0/data/runs/20260801_080036_session-a7228addb523
/root/ReClaw-2.0/data/runs/job-0d72b86c81.status.json
/root/ReClaw-2.0/data/runs/job-2aca38cce9.status.json
/root/ReClaw-2.0/data/runs/job-bad6901bac.status.json
/root/ReClaw-2.0/data/runs/job-e3787c68cb.status.json
/root/ReClaw-2.0/data/runs/job-f84a28596c.status.json
/root/ReClaw-2.0/data/RURAL_DATA_PIPELINE_FROZEN
/root/ReClaw-2.0/data/seeds
/root/ReClaw-2.0/data/seeds/pike_county_winslow_2025.json
/root/ReClaw-2.0/data/sessions
/root/ReClaw-2.0/data/sessions/session-008aee7defe0
/root/ReClaw-2.0/data/sessions/session-01acc87282b3
/root/ReClaw-2.0/data/sessions/session-0af23fc8e4b2
/root/ReClaw-2.0/data/sessions/session-1105ab7febc0
/root/ReClaw-2.0/data/sessions/session-111b4854a34a
/root/ReClaw-2.0/data/sessions/session-133aee67aaf4
/root/ReClaw-2.0/data/sessions/session-13aa0c3c4376
/root/ReClaw-2.0/data/sessions/session-13b90efccb4e
/root/ReClaw-2.0/data/sessions/session-186a1749cbb8
/root/ReClaw-2.0/data/sessions/session-1a238032d108
/root/ReClaw-2.0/data/sessions/session-1f1ca797d1f0
/root/ReClaw-2.0/data/sessions/session-24b1edac3fa3
/root/ReClaw-2.0/data/sessions/session-2ba3c959a2a7
/root/ReClaw-2.0/data/sessions/session-2ff81ced3aa9
/root/ReClaw-2.0/data/sessions/session-3075b3a0edb9
/root/ReClaw-2.0/data/sessions/session-30c596c231e6
/root/ReClaw-2.0/data/sessions/session-3a463d30dbc5
/root/ReClaw-2.0/data/sessions/session-455bb698b9d0
/root/ReClaw-2.0/data/sessions/session-457d41b070be
/root/ReClaw-2.0/data/sessions/session-467515aab804
/root/ReClaw-2.0/data/sessions/session-50ff243db7fb
/root/ReClaw-2.0/data/sessions/session-538a31a16b5e
/root/ReClaw-2.0/data/sessions/session-5406d781f0d4
/root/ReClaw-2.0/data/sessions/session-5a1cc87e27a3
/root/ReClaw-2.0/data/sessions/session-5b72778046d5
/root/ReClaw-2.0/data/sessions/session-63db595f96f1
/root/ReClaw-2.0/data/sessions/session-659cce41db2d
/root/ReClaw-2.0/data/sessions/session-69ac63f92fa6
/root/ReClaw-2.0/data/sessions/session-69cfd9fa2ae0
/root/ReClaw-2.0/data/sessions/session-6cd22115b02c
/root/ReClaw-2.0/data/sessions/session-6d2c487dfdba
/root/ReClaw-2.0/data/sessions/session-724b523ae6a3
/root/ReClaw-2.0/data/sessions/session-7484fe34e9f2
/root/ReClaw-2.0/data/sessions/session-7559634a9412
/root/ReClaw-2.0/data/sessions/session-7a4fcab7e3f7
/root/ReClaw-2.0/data/sessions/session-7c748f3c0408
/root/ReClaw-2.0/data/sessions/session-8033bee8986e
/root/ReClaw-2.0/data/sessions/session-85e74b4734cf
/root/ReClaw-2.0/data/sessions/session-87911b6489a7
/root/ReClaw-2.0/data/sessions/session-8847ef9c590b
/root/ReClaw-2.0/data/sessions/session-92197a43c0b0
/root/ReClaw-2.0/data/sessions/session-9375ae493295
/root/ReClaw-2.0/data/sessions/session-947c2787eb77
/root/ReClaw-2.0/data/sessions/session-96275a470e61
/root/ReClaw-2.0/data/sessions/session-965ffa7355db
/root/ReClaw-2.0/data/sessions/session-989f9fa1fcd6
/root/ReClaw-2.0/data/sessions/session-99a7d408c304
/root/ReClaw-2.0/data/sessions/session-9e39ed620760
/root/ReClaw-2.0/data/sessions/session-a13f73bb5a3a
/root/ReClaw-2.0/data/sessions/session-a43dab43cdc5
/root/ReClaw-2.0/data/sessions/session-a7228addb523
/root/ReClaw-2.0/data/sessions/session-b05b474edacc
/root/ReClaw-2.0/data/sessions/session-b0894e7a18fb
/root/ReClaw-2.0/data/sessions/session-b42e3507cbb1
/root/ReClaw-2.0/data/sessions/session-b6f50ce3d0a3
/root/ReClaw-2.0/data/sessions/session-bdedeef79ab5
/root/ReClaw-2.0/data/sessions/session-bf63f2ddfdab
/root/ReClaw-2.0/data/sessions/session-c0ed66f8748f
/root/ReClaw-2.0/data/sessions/session-c3c9955a6a6f
/root/ReClaw-2.0/data/sessions/session-c563dc227cd8
/root/ReClaw-2.0/data/sessions/session-c67ef92b3dc2
/root/ReClaw-2.0/data/sessions/session-c72d0822c608
/root/ReClaw-2.0/data/sessions/session-c7327deb0f6f
/root/ReClaw-2.0/data/sessions/session-cc7668d06dc1
/root/ReClaw-2.0/data/sessions/session-cff433285aad
/root/ReClaw-2.0/data/sessions/session-d02fc06c502f
/root/ReClaw-2.0/data/sessions/session-d03585499464
/root/ReClaw-2.0/data/sessions/session-d0ce92e4dc63
/root/ReClaw-2.0/data/sessions/session-d85e555f7709
/root/ReClaw-2.0/data/sessions/session-ddec898d6595
/root/ReClaw-2.0/data/sessions/session-e011994c448d
/root/ReClaw-2.0/data/sessions/session-e2d45a67bc36
/root/ReClaw-2.0/data/sessions/session-e78c8b7428f8
/root/ReClaw-2.0/data/sessions/session-ea3bf4cf2911
/root/ReClaw-2.0/data/sessions/session-ea87d2dc9a3f
/root/ReClaw-2.0/data/sessions/session-ebe5d5819641
/root/ReClaw-2.0/data/sessions/session-f061e983435c
/root/ReClaw-2.0/data/sessions/session-f23ae6c4fc01
/root/ReClaw-2.0/data/sessions/session-f5f9b3088375
/root/ReClaw-2.0/data/sessions/session-fe11cc3ce641
/root/ReClaw-2.0/data/sessions/session-ff2d2ec176a9
/root/ReClaw-2.0/data/silent_auditor_workflow.yaml
/root/ReClaw-2.0/data/socrata_sources.yaml
/root/ReClaw-2.0/data/sources
/root/ReClaw-2.0/data/sources/indiana
/root/ReClaw-2.0/data/spark_system_manifest.md
/root/ReClaw-2.0/data/upwork_digests
/root/ReClaw-2.0/data/upwork_digests/2026-07-17.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-19.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-21.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-23.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-25.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-27.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-29.md
/root/ReClaw-2.0/data/upwork_digests/2026-07-31.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-02.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-04.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-06.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-08.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-10.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-12.md
/root/ReClaw-2.0/data/upwork_digests/2026-08-14.md
/root/ReClaw-2.0/data/upwork_preferences.yaml
/root/ReClaw-2.0/data/viral_hook_playbook.yaml
/root/ReClaw-2.0/data/viral_scribe_directive.yaml
/root/ReClaw-2.0/data/WIP-DIRTY-TREE-2026-08-01.md
/root/ReClaw-2.0/scripts
/root/ReClaw-2.0/scripts/bootstrap_orchestration.sh
/root/ReClaw-2.0/scripts/bootstrap_remotion.sh
/root/ReClaw-2.0/scripts/boydscomp-node-service-install.sh
/root/ReClaw-2.0/scripts/boydscomp-node-service-install.sh.bak-pre-tls-20260806T184156Z
/root/ReClaw-2.0/scripts/boydscomp-pc-hands-demo.sh
/root/ReClaw-2.0/scripts/build_indiana_worklist.py
/root/ReClaw-2.0/scripts/ensure-single-openclaw.sh
/root/ReClaw-2.0/scripts/ensure-single-openclaw.sh.bak-20260805T070140Z
/root/ReClaw-2.0/scripts/ensure-tailscale-mcp-funnel.sh
/root/ReClaw-2.0/scripts/ensure-tailscale-mcp-funnel.sh.bak-20260815-nofunnel
/root/ReClaw-2.0/scripts/export_county_salaries.py
/root/ReClaw-2.0/scripts/fortress_alert_watch.py
/root/ReClaw-2.0/scripts/google_oauth_setup.py
/root/ReClaw-2.0/scripts/grant_digest_thin.py
/root/ReClaw-2.0/scripts/ingest_dogegpt_upload.sh
/root/ReClaw-2.0/scripts/ingest.py
/root/ReClaw-2.0/scripts/init-git.ps1
/root/ReClaw-2.0/scripts/linux-node-pair-watch.sh
/root/ReClaw-2.0/scripts/local-coder-on-demand.sh
/root/ReClaw-2.0/scripts/morning_fortress_brief.py
/root/ReClaw-2.0/scripts/obsidian_mcp_server.py
/root/ReClaw-2.0/scripts/post-deploy-healthcheck.sh
/root/ReClaw-2.0/scripts/prefetch_gateway_years.sh
/root/ReClaw-2.0/scripts/prefetch_indiana_basics.sh
/root/ReClaw-2.0/scripts/__pycache__
/root/ReClaw-2.0/scripts/__pycache__/fortress_alert_watch.cpython-312.pyc
/root/ReClaw-2.0/scripts/__pycache__/ravenstack_mcp_server.cpython-312.pyc
/root/ReClaw-2.0/scripts/__pycache__/reclaw_api_mcp_server.cpython-312.pyc
/root/ReClaw-2.0/scripts/__pycache__/reclaw_mcp_server.cpython-312.pyc
/root/ReClaw-2.0/scripts/__pycache__/reclaw_platform_mcp_extensions.cpython-312.pyc
/root/ReClaw-2.0/scripts/__pycache__/reclaw_platform_mcp_server.cpython-312.pyc
/root/ReClaw-2.0/scripts/rank_indiana_peer_outliers.sh
/root/ReClaw-2.0/scripts/ravenstack_mcp_server.py
/root/ReClaw-2.0/scripts/reclaw_api_mcp_server.py
/root/ReClaw-2.0/scripts/reclaw_fs_mcp_server.py
/root/ReClaw-2.0/scripts/reclaw_mcp_server.py
/root/ReClaw-2.0/scripts/reclaw_platform_mcp_extensions.py
/root/ReClaw-2.0/scripts/reclaw_platform_mcp_server.py
/root/ReClaw-2.0/scripts/reclaw_platform_mcp_server.py.bak-20260815-denylist
/root/ReClaw-2.0/scripts/run_audit_copilot.py
/root/ReClaw-2.0/scripts/run_audit_discovery.sh
/root/ReClaw-2.0/scripts/run_benford.py
/root/ReClaw-2.0/scripts/run-daily-pike-winslow.sh
/root/ReClaw-2.0/scripts/run-mcp-public-tunnel.sh
/root/ReClaw-2.0/scripts/run-reclaw-mcp-bridge.sh
/root/ReClaw-2.0/scripts/run-reclaw-mcp-bridge.sh.bak.20260812
/root/ReClaw-2.0/scripts/run_remotion_orchestrator.py
/root/ReClaw-2.0/scripts/run_remotion_render.sh
/root/ReClaw-2.0/scripts/run_sboa_discovery.sh
/root/ReClaw-2.0/scripts/run_socrata_scrape.py
/root/ReClaw-2.0/scripts/run_video_manifest.py
/root/ReClaw-2.0/scripts/run_viral_scribe.py
/root/ReClaw-2.0/scripts/setup-named-mcp-tunnel.sh
/root/ReClaw-2.0/scripts/smoke_morning_digest.py
/root/ReClaw-2.0/scripts/sync-mcp-tunnel-url.sh
/root/ReClaw-2.0/scripts/sync-mcp-tunnel-url.sh.bak.20260807
/root/ReClaw-2.0/scripts/test_gateway_download.py
/root/ReClaw-2.0/scripts/test-run.sh
/root/ReClaw-2.0/scripts/test_silent_auditor.py
/root/ReClaw-2.0/scripts/verify_county_isolation.py
/root/ReClaw-2.0/scripts/verify-openclaw-android-path.sh
/root/ReClaw-2.0/scripts/verify.sh
/root/ReClaw-2.0/scripts/watchdog.py
/root/ReClaw-2.0/scripts/weekly_raziel_reflection.py
/root/ReClaw-2.0/scripts/weekly_raziel_self_improve.py
/root/ReClaw-2.0/scripts/write_fortress_dashboard_status.py
/root/ReClaw-2.0/skills
/root/ReClaw-2.0/skills/approval_gate
/root/ReClaw-2.0/skills/approval_gate/SKILL.md
/root/ReClaw-2.0/skills/clawsmith
/root/ReClaw-2.0/skills/clawsmith/SKILL.md
/root/ReClaw-2.0/skills/github
/root/ReClaw-2.0/skills/github/.clawhub
/root/ReClaw-2.0/skills/github/_meta.json
/root/ReClaw-2.0/skills/github/skill-card.md
/root/ReClaw-2.0/skills/github/SKILL.md
/root/ReClaw-2.0/skills/obsidian-direct
/root/ReClaw-2.0/skills/obsidian-direct/.clawhub
/root/ReClaw-2.0/skills/obsidian-direct/_meta.json
/root/ReClaw-2.0/skills/obsidian-direct/scripts
/root/ReClaw-2.0/skills/obsidian-direct/skill-card.md
/root/ReClaw-2.0/skills/obsidian-direct/SKILL.md
/root/ReClaw-2.0/skills/outreach_crafter
/root/ReClaw-2.0/skills/outreach_crafter/SKILL.md
/root/ReClaw-2.0/skills/playwright-mcp
/root/ReClaw-2.0/skills/playwright-mcp/.clawhub
/root/ReClaw-2.0/skills/playwright-mcp/examples.py
/root/ReClaw-2.0/skills/playwright-mcp/_meta.json
/root/ReClaw-2.0/skills/playwright-mcp/skill-card.md
/root/ReClaw-2.0/skills/playwright-mcp/SKILL.md
/root/ReClaw-2.0/skills/seo_auditor
/root/ReClaw-2.0/skills/seo_auditor/SKILL.md
```

## 6. Obsidian Vault Structure
```text
/root/obsidian-vault/Ravenstack
/root/obsidian-vault/Ravenstack/ops
/root/obsidian-vault/Ravenstack/ops/audits
```

## 7. Schema Sample & Structure
```yaml
# --- File: /root/ReClaw-2.0/data/architectural_registry.yaml ---
# Project ReClaw — Multi-Agent Architectural Registry (machine-readable)
# UI: scratch/reclaw-registry/index.html
# Source of truth for deployed vs backlog; keep in sync with reclaw_orchestration.yaml

version: "2.0.4"
orchestrator: grok
deployment: hetzner_dedicated
default_mode: indiana_county_queue

agents:
  - id: gateway_sentinel
    name: Gateway Sentinel
# --- File: /root/ReClaw-2.0/data/auditor_lessons_log.yaml ---
lessons:
- id: reject-posey-20260724
  symptom: 'Human rejected Posey: Repurposing primary content mode from Silent Auditor
    risk flags to interesting-facts Shorts (I bet you didn’t know format). Clearing
    old-style package to start clean.'
  root_cause: 'Package/review failed operator bar (hook="They thought you wouldn''t
    check. Posey County Sheriff? $110K. Name: Latham, Thomas E.", flags=45, top="Latham,
    Thomas E — Sheriff (Sheriff): $110,107 in 2025 public compensation. In a county
    of ~25,226, that''s a taxpayer talking-point."). granted_by=human'
  content_rule: Next run must respect this reject reason. Prefer SBOA + dual-receipt
    named $ stories over volume. Zero fake vendors from Gateway ent_name.
  status: open
# --- File: /root/ReClaw-2.0/data/audit_pipeline_mistakes.yaml ---
mistakes:
- id: bleed-pike-salary-2026-07-06
  county_affected:
  - Spencer
  - Warrick
  symptom: 'Wood Brett paramedic $92K or lifeguard vs sheriff contrast on wrong county

    '
  root_cause: 'load_salary_detail_records_for_county fell back to ingestion/SalarySearch.csv
    (Pike only)

    '
# --- File: /root/ReClaw-2.0/data/audit_strategy.yaml ---
# Audit strategy — synthesized from DOGEGPT kit + fraud-examination patterns + ReClaw stack.
# Governs red_flag_engine, analyst, scriptwriter, county queue.
#
# 2026-07-17: Operator blueprint ingested —
#   data/indiana_public_finance_blueprint.yaml
#   Ravenstack/ops/algorithmic-auditing-public-finance-blueprint-2026-07-17.md
# Prefer deterministic SBOA + 100R + fund YoY over IsolationForest cold opens.
# Split-purchase / vendor drama ONLY on claims dockets (not Gateway AFR ent_name).

philosophy:
  - explainable_over_exotic
  - audience_must_see_the_weird
# --- File: /root/ReClaw-2.0/data/audit_tool_candidates.yaml ---
# Audit tool discovery backlog — Indiana county faceless-auditor channel.
# Updated: 2026-07-06 via Firecrawl CLI + GitHub API search.
# Rule: every implemented detector must return row-level provenance (Gateway/SBOA/salary row).

pipeline_review:
  date: 2026-07-06
  repos_cloned: scratch/pipeline-review/
  verdict: >
    ReClaw budget stack (ECOD+IF+YoY+peer) beats Jabonsote for county budgets.
    sf-vendor + audit-analytics beat us on vendor-level checks but need transaction
    data Indiana Gateway does not provide. Ported IQR + Nigrini MAD + fund concentration.
  jabonsote_deepseek_if:
# --- File: /root/ReClaw-2.0/data/content_truth_rules.yaml ---
# Content truth rules — SOT for publishable claims (Story Factory)
# Updated: 2026-07-17 after field research (Winslow water, SBOA heat, Gateway schema truth)
# Hard stop: nothing fake enters analysis package, risk score, or review card.

status: freeze_county_mill
freeze_note: >
  No county-queue run-next / refresh until ClaimGate + zero-fake detectors land.
  Posey may stay pending. Operator must explicitly unfreeze.

philosophy:
  - anger_signal_then_public_dollars  # not anomaly CSV → hope
  - dual_receipt_for_pain_stories
# --- File: /root/ReClaw-2.0/data/fraud_detection_framework.yaml ---
# Integrated Fraud Detection & Public Accountability — ReClaw mapping
# Source: external framework report (2026-07-06) → deployed vs backlog

governance:
  human_in_the_loop: county_queue approve/reject before publish
  fair_report: show_ask_cite_never_convict
  local_llm: Ollama :8080 for sensitive ledger context
  feedback_loop: tools/total_reclaw_memory.py on high-severity flags

section_I_detection:
  isolation_forest:
    status: deployed
# --- File: /root/ReClaw-2.0/data/fraud_scheme_taxonomy.yaml ---
# Fraud scheme → detector mapping (government / municipal)

schemes:
  bill_padding:
    description: Invoice for goods/services never ordered or not received
    detectors: [iqr_outlier, vendor_concentration]
    data_required: [vendor_payee, invoice_id]
    gateway_ready: partial

  phantom_vendor:
    description: Fictitious payee on disbursement register
    detectors: [vendor_concentration, round_number_cluster]
# --- File: /root/ReClaw-2.0/data/indiana_county_worklist.yaml ---
generated_from: /root/ReClaw-2.0/data/cache/gateway_disbursements_2024.txt
anchor: Pike
total_counties: 92
counties:
- gateway_code: 63
  name: Pike
  fips: '18125'
  state: IN
  lat: 38.019
  lon: -87.285
  distance_from_pike_mi: 0.0
  county_seat_hint: Pike County, IN
# --- File: /root/ReClaw-2.0/data/indiana_public_finance_blueprint.yaml ---
# Operational distillation of:
# "Algorithmic Auditing of Public Finance: An Operational Blueprint for Indiana Local Government Financial Oversight"
# Operator paste 2026-07-17. Raw archive:
#   data/research/algorithmic-auditing-public-finance-blueprint-2026-07-17.md
# Aligns with Story Factory freeze + content_truth_rules.yaml

status: ingested
ingested: 2026-07-17
source: operator-provided-research-paste

executive_shift:
  from: unsupervised statistical anomaly mill (60-90 unwatchable flags)
# --- File: /root/ReClaw-2.0/data/obsidian_fix_backlog.yaml ---
# Obsidian integration — fix-later backlog (2026-07-06)
# Pipeline works via filesystem; these are enhancements, not blockers.

status: deferred
vault_root: /root/obsidian_vault
vault_git: jasandroidx/obsidian-vault
docs: docs/OBSIDIAN-VAULT-SOT.md
bridge_module: tools/obsidian_bridge.py

working_now:
  - obsidian_bridge publish (package + audit-flags + County Audit Index)
  - RECLAW_OBSIDIAN_VAULT_PATH on host .env
# --- File: /root/ReClaw-2.0/data/public_data_sources.yaml ---
# Public data source registry — Indiana rural counties (Pike primary)
# Used by Researcher + Silent Auditor. Truth + provenance only.

indiana:
  gateway_disbursements:
    name: Indiana Gateway — Disbursements by Fund
    url: https://gateway.ifionline.org/public/download.aspx
    afr_url: https://gateway.ifionline.org/public/AFR.aspx
    description: Statewide flat file of local government disbursements (corruption/procurement audits)
    format: pipe-delimited txt
    years_available: [2010, 2023, 2024, 2025]
    corruption_signals:
# --- File: /root/ReClaw-2.0/data/public_source_map.yaml ---
# Public source map — Story Factory / Silent Auditor
# Updated: 2026-07-17. Honest status from this host.

status: living
host: Hetzner ReClaw (datacenter IP)

access_reality:
  web_search: works
  httpx_public_sites: works
  chrome_browser: works
  firecrawl: key_present_credits_exhausted
  reddit_www_json: blocked_403_datacenter
# --- File: /root/ReClaw-2.0/data/reclaw_orchestration.yaml ---
# ReClaw Orchestration Map — Grok primary orchestrator on Hetzner
# Maps external orchestration spec → deployed capabilities vs backlog
# Default jurisdiction: Indiana 92-county queue (NOT Socrata/SODA — different data regime)

status: active
orchestrator: grok
deployment: hetzner_dedicated
default_mode: indiana_county_queue

stack_health:
  reclaw_api: http://127.0.0.1:8000
  openclaw_gateway: http://127.0.0.1:18789
# --- File: /root/ReClaw-2.0/data/red_flag_taxonomy.yaml ---
# ReClaw red-flag & anomaly taxonomy — every pattern we hunt, any Indiana county.
# Categories map to tools/scriptwriter.py hooks and Content Studio priority.

goal: >
  Faceless local-auditor channel: find genuinely different weird patterns per county
  (not mail-merge). Every flag traces to a public record URL.

layers:
  gateway_disbursements:
    source: gateway.ifionline.org/public/download.aspx
    scope: all_92_counties
    patterns:
# --- File: /root/ReClaw-2.0/data/silent_auditor_workflow.yaml ---
# Silent Auditor Workflow V2 — machine SOT (loaded by auditor_playbook)
# Twin: docs/SILENT-AUDITOR-WORKFLOW.md · Ravenstack/ops/SILENT-AUDITOR-WORKFLOW.md
# Updated: 2026-07-17

version: "2.0"
status: active
updated: "2026-07-17"
not_legal_advice: true

core_objective: >
  Convert Indiana municipal finance records into verified short-form scripts
  without defamation risk, draft-audit disclosure, or Gateway fake-vendor drama.
# --- File: /root/ReClaw-2.0/data/socrata_sources.yaml ---
# Socrata SODA datasets — municipal checkbooks outside Indiana Gateway.
# Primary Indiana county pipeline still uses gateway.ifionline.org flat files.

meta:
  api_docs: https://dev.socrata.com/docs/
  token_env: SOCRATA_APP_TOKEN
  output_dir: data/inbox/

datasets:
  - id: bloomington_payments
    domain: data.bloomington.in.gov
    dataset_id: checkbook  # replace with 4x4 ID after discovery via portal UI
# --- File: /root/ReClaw-2.0/data/upwork_preferences.yaml ---
# Upwork job scan preferences — edit this, not the code.
# Scanner: tools/upwork_scan.py · digests: data/upwork_digests/
# Interval: every 2 days (systemd timer reclaw-upwork-scan)

version: 1
enabled: true

# How results are delivered
notify:
  write_digest: true          # data/upwork_digests/YYYY-MM-DD.md
  write_vault_copy: true      # /root/obsidian_vault/Ravenstack/ops/upwork-digest-latest.md
  webhook: true               # uses ALERT_WEBHOOK from .env if set
# --- File: /root/ReClaw-2.0/data/viral_hook_playbook.yaml ---
# Project ReClaw — Viral Hook & Headline Playbook (HHVCTA)
# Story-first hooks in first 3 seconds. Fair-report — questions not convictions.

psychology:
  rule: Never start with the data. Start with the intent behind the data.
  stop_scroll: >
    First 1–2 seconds must create a curiosity gap or pattern shock.
    Named person + exact $ + "why/they thought" beats "County paid X $Y — public record."
  bad_example: "Chicago spent $14,000 on consulting."
  worse_example: "Gibson County paid Vanoven, Bruce L (Sheriff) $111K — public record."
  good_example: "Why did Chicago pay the same consultant three times in 24 hours?"
  good_salary_example: "They thought you wouldn't check public salaries. Posey County's sheriff? $111K on the books."
# --- File: /root/ReClaw-2.0/data/viral_scribe_directive.yaml ---
# ReClaw Viral Scribe — Investigative short-form script directive
# High-retention taxpayer advocacy; fair-report guardrails (questions, not convictions)

role: Viral Scribe
persona: Investigative journalist + forensic auditor voice — urgent, specific, never conspiratorial

hhvcta_timing:
  hook:     { start_s: 0,  end_s: 3,  duration_s: 3 }
  hint:     { start_s: 3,  end_s: 6,  duration_s: 3 }
  value:    { start_s: 6,  end_s: 45, duration_s: 39 }
  credibility: { start_s: 45, end_s: 50, duration_s: 5 }
  takeaway: { start_s: 50, end_s: 55, duration_s: 5 }
# --- File: /root/ReClaw-2.0/data/castle_map.json ---
{
  "$schema": "../Ravenstack/RAVENSTACK-ORACLE.md#dashboard-tie-in",
  "theme": "blacksmith_castle",
  "grid_size": [3, 3],
  "title": "Ravenstack Fortress",
  "ravenlord": {
    "name": "Jason (Ravenlord)",
    "title": "Overseer of the Mystical Hall",
    "status": "commanding"
  },
  "rooms": [
    {
# --- File: /root/ReClaw-2.0/data/dogegpt_ingest_manifest.json ---
{
  "reviewed_at": "2026-07-06T02:40:38.491724+00:00",
  "upload_path": "/root/DOGEGPT-20260615T020114Z-3-001",
  "upload_size_bytes": 93635707,
  "file_count": 40,
  "ingested": {
    "pike_csvs": [
      "ingestion/pike_budget_textmode.csv",
      "ingestion/pike_county_totals_2022_2025.csv"
    ],
    "pipeline": "ingestion/pipeline_budget_anomalies.py",
    "extractor": "ingestion/extract_pike_budget.py",
# --- File: /root/ReClaw-2.0/data/fortress_state.json ---
{
  "theme": "ravenstack-fortress",
  "title": "Ravenstack Fortress",
  "generated_at": "2026-08-16T03:40:30.401218Z",
  "rooms": [
    {
      "id": "war-room",
      "zone": "desk",
      "label": "War Room",
      "description": "Command & main specialists",
      "accent": "#c9a227"
    },
```
