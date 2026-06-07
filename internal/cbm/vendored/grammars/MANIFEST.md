# Vendored tree-sitter Grammar Manifest

**Provenance + version record for the tree-sitter grammars under this directory.**

The grammars were originally vendored as bare `parser.c`+`scanner.c` with **no recorded upstream version or commit**. This manifest reconstructs that provenance and pins each vendored grammar to a specific upstream commit, cross-verified against two independent registries (nvim-treesitter `parsers.lua` + Helix `languages.toml`).

## How generated
`private/grammar_audit/{discover,resolve_stragglers}.sh` (upstream + tag) → `verify_sources.py` (cross-verify vs nvim-treesitter + Helix, capture pinned commit) → `gen_manifest.py`. Captured 2026-06-02.

## Summary

- Grammars: **157** — vendored-from-upstream: **140**, first-party/self-maintained: **12**, registry-disagreement: **5**
- ABI distribution: **7×** ABI-13 **86×** ABI-14 **64×** ABI-15 (runtime ceiling is ABI 15; never vendor ABI 16 without a runtime upgrade)
- Vendored copies missing LICENSE: **68** (restore on next re-vendor — redistribution compliance)
- `verdict`: VERIFIED-BOTH = our source matches *both* registries; VERIFIED-NVIM/HELIX = matches one; registry-disagreement = registries name a different repo (listed separately).

> ⚠️ **Pinned commit = the revision nvim-treesitter/Helix vendor** (battle-tested, canonical source), not bleeding-edge HEAD. When re-vendoring, update the pinned commit here.

## Custom extraction handling (definition extraction)

The grammars below carry **custom definition-extraction support** in
`internal/cbm/extract_defs.c` (and `internal/cbm/lang_specs.c`). Their function /
definition nodes do **not** expose a `name` field that the generic extractor reads
— the name lives on a nested/child/parent node, or (for the Lisp family) a
definition is a macro form inside a generic `list` node with no dedicated def
node. Without this handling these grammars produce only a file-level `Module`
node and **zero functions/types**. A future grammar refresh that changes these
node shapes must update the corresponding branch.

Guarded by the `contract_all_grammars_in_graph` graph-breadth test in
`tests/test_lang_contract.c` (each was reproduced as a failing case before the fix).

| grammar | custom handling |
|---|---|
| ada      | `resolve_func_name`: `subprogram_body`/`subprogram_declaration` → `procedure_specification`/`function_specification` child's `name` field |
| cairo    | `resolve_func_name`: `function_definition`/`function_signature` → `identifier` child |
| clojure  | `extract_lisp_def`: `(defn …)` / `(def …)` head-symbol forms in `list_lit` |
| d        | `resolve_func_name`: `function_declaration` → `identifier` child |
| fortran  | `resolve_func_name`: `subroutine`/`function` → inner `*_statement`'s `name` field |
| fsharp   | `func_types` += `function_or_value_defn`; `resolve_func_name` → `function_declaration_left`/`value_declaration_left` identifier |
| haskell  | `func_types` += `bind` (nullary value bindings; `signature` suppressed) |
| hlsl     | added to the C-family declarator-name gate (tree-sitter-cpp derivative) |
| ispc     | added to the C-family declarator-name gate (extends tree-sitter-c) |
| odin     | `resolve_func_name`: `procedure_declaration` → `identifier` child |
| pascal   | `resolve_func_name`: `defProc` → `header` (`declProc`) child's `name` field |
| racket   | `extract_lisp_def`: `(define …)` head-symbol forms in `list` |
| rescript | `resolve_func_name`: `function` (arrow) → enclosing `let_binding`'s `pattern` field |
| scheme   | `extract_lisp_def`: `(define …)` head-symbol forms in `list` |
| slang    | added to the C-family declarator-name gate (tree-sitter-cpp/hlsl fork) |
| squirrel | `resolve_func_name`: `function_declaration` → `identifier` child |

## Vendored from verified upstream

| grammar | cur ABI | upstream repo | pinned commit | verdict | LICENSE |
|---|:---:|---|---|---|:---:|
| ada | 14 | briot/tree-sitter-ada | `6b58259a08b1` | VERIFIED-BOTH | ❌ |
| agda | 14 | tree-sitter/tree-sitter-agda | `e8d47a6987ef` | VERIFIED-BOTH | ✅ |
| apex | 14 | aheber/tree-sitter-sfapex | `3597575a4297` | VERIFIED-NVIM | ✅ |
| astro | 14 | virchau13/tree-sitter-astro | `213f6e6973d9` | VERIFIED-BOTH | ✅ |
| awk | 14 | Beaglefoot/tree-sitter-awk | `34bbdc7cce8e` | VERIFIED-BOTH | ✅ |
| bash | 15 | tree-sitter/tree-sitter-bash | `a06c2e4415e9` | VERIFIED-BOTH | ❌ |
| beancount | 15 | polarmutex/tree-sitter-beancount | `429cff869513` | VERIFIED-BOTH | ✅ |
| bibtex | 15 | latex-lsp/tree-sitter-bibtex | `8d04ed27b3bc` | VERIFIED-BOTH | ✅ |
| bicep | 14 | tree-sitter-grammars/tree-sitter-bicep | `bff59884307c` | VERIFIED-BOTH | ✅ |
| bitbake | 14 | tree-sitter-grammars/tree-sitter-bitbake | `a5d04fdb5a69` | VERIFIED-BOTH | ✅ |
| blade | 15 | EmranMR/tree-sitter-blade | `b9436b7b9369` | VERIFIED-BOTH | ✅ |
| c | 15 | tree-sitter/tree-sitter-c | `ae19b676b13b` | VERIFIED-BOTH | ❌ |
| c_sharp | 15 | tree-sitter/tree-sitter-c-sharp | `88366631d598` | VERIFIED-BOTH | ✅ |
| cairo | 14 | tree-sitter-grammars/tree-sitter-cairo | `6238f609bea2` | VERIFIED-NVIM | ✅ |
| capnp | 14 | tree-sitter-grammars/tree-sitter-capnp | `7b0883c03e5e` | VERIFIED-BOTH | ✅ |
| clojure | 14 | sogaiu/tree-sitter-clojure | `e43eff80d17c` | VERIFIED-BOTH | ❌ |
| cmake | 14 | uyha/tree-sitter-cmake | `c7b2a71e7f8e` | VERIFIED-BOTH | ❌ |
| commonlisp | 14 | tree-sitter-grammars/tree-sitter-commonlisp | `32323509b3d9` | VERIFIED-BOTH | ❌ |
| cpp | 14 | tree-sitter/tree-sitter-cpp | `8b5b49eb196b` | VERIFIED-BOTH | ❌ |
| crystal | 14 | crystal-lang-tools/tree-sitter-crystal | `50ca9e6fcfb1` | VERIFIED-HELIX | ✅ |
| css | 15 | tree-sitter/tree-sitter-css | `dda5cfc5722c` | VERIFIED-BOTH | ❌ |
| csv | 15 | tree-sitter-grammars/tree-sitter-csv | `f6bf6e35eb0b` | VERIFIED-NVIM | ✅ |
| cuda | 15 | tree-sitter-grammars/tree-sitter-cuda | `48b066f334f4` | VERIFIED-NVIM | ❌ |
| d | 14 | gdamore/tree-sitter-d | `fb028c8f14f4` | VERIFIED-BOTH | ❌ |
| dart | 15 | UserNobody14/tree-sitter-dart | `0fc19c3a57b1` | VERIFIED-BOTH | ❌ |
| devicetree | 15 | joelspadin/tree-sitter-devicetree | `e685f1f6ac17` | VERIFIED-BOTH | ✅ |
| diff | 15 | tree-sitter-grammars/tree-sitter-diff | `2520c3f934b3` | VERIFIED-NVIM | ✅ |
| dockerfile | 14 | camdencheek/tree-sitter-dockerfile | `971acdd90856` | VERIFIED-BOTH | ❌ |
| elisp | 15 | Wilfred/tree-sitter-elisp | `32323509b3d9` | VERIFIED-HELIX | ❌ |
| elixir | 14 | elixir-lang/tree-sitter-elixir | `7937d3b4d65f` | VERIFIED-BOTH | ❌ |
| elm | 15 | elm-tooling/tree-sitter-elm | `6d9511c28181` | VERIFIED-BOTH | ❌ |
| erlang | 14 | WhatsApp/tree-sitter-erlang | `1d78195c4fbb` | VERIFIED-NVIM | ❌ |
| fennel | 14 | alexmozaidze/tree-sitter-fennel | `3f0f6b24d599` | MISMATCH | ✅ |
| fish | 14 | ram02z/tree-sitter-fish | `fa2143f5d66a` | VERIFIED-BOTH | ✅ |
| fortran | 15 | stadelmanma/tree-sitter-fortran | `be30d90dc7df` | VERIFIED-BOTH | ❌ |
| fsharp | 15 | ionide/tree-sitter-fsharp | `1c2d9351d1f7` | VERIFIED-BOTH | ❌ |
| func | 14 | tree-sitter-grammars/tree-sitter-func | `f780ca55e65e` | VERIFIED-NVIM | ✅ |
| gdscript | 14 | PrestonKnopp/tree-sitter-gdscript | `9686853b696d` | VERIFIED-BOTH | ✅ |
| gitattributes | 14 | tree-sitter-grammars/tree-sitter-gitattributes | `1b7af09d45b5` | VERIFIED-NVIM | ✅ |
| gitignore | 13 | shunsambongi/tree-sitter-gitignore | `f4685bf11ac4` | VERIFIED-BOTH | ✅ |
| gleam | 15 | gleam-lang/tree-sitter-gleam | `0bb1b0ae1a35` | VERIFIED-BOTH | ✅ |
| glsl | 14 | tree-sitter-grammars/tree-sitter-glsl | `24a6c8ef698e` | VERIFIED-NVIM | ❌ |
| gn | 14 | tree-sitter-grammars/tree-sitter-gn | `bc06955bc1e3` | VERIFIED-NVIM | ✅ |
| go | 15 | tree-sitter/tree-sitter-go | `2346a3ab1bb3` | VERIFIED-BOTH | ❌ |
| gomod | 15 | camdencheek/tree-sitter-go-mod | `2e886870578e` | VERIFIED-BOTH | ✅ |
| gotemplate | 15 | ngalaiko/tree-sitter-go-template | `aa71f63de226` | VERIFIED-BOTH | ✅ |
| graphql | 13 | bkegley/tree-sitter-graphql | `5e66e961eee4` | VERIFIED-BOTH | ❌ |
| groovy | 15 | murtaza64/tree-sitter-groovy | `781d9cd1b482` | VERIFIED-BOTH | ❌ |
| hare | 15 | tree-sitter-grammars/tree-sitter-hare | `eed7ddf6a66b` | VERIFIED-NVIM | ✅ |
| haskell | 15 | tree-sitter/tree-sitter-haskell | `7fa19f195803` | VERIFIED-HELIX | ❌ |
| hcl | 15 | tree-sitter-grammars/tree-sitter-hcl | `64ad62785d44` | MISMATCH | ❌ |
| hlsl | 14 | tree-sitter-grammars/tree-sitter-hlsl | `bab9111922d5` | VERIFIED-NVIM | ✅ |
| html | 14 | tree-sitter/tree-sitter-html | `73a3947324f6` | VERIFIED-BOTH | ❌ |
| hyprlang | 15 | tree-sitter-grammars/tree-sitter-hyprlang | `cecd6b748107` | VERIFIED-BOTH | ✅ |
| ini | 15 | justinmk/tree-sitter-ini | `e4018b517613` | VERIFIED-BOTH | ❌ |
| ispc | 14 | tree-sitter-grammars/tree-sitter-ispc | `9b2f9aec2106` | VERIFIED-NVIM | ✅ |
| java | 14 | tree-sitter/tree-sitter-java | `e10607b45ff7` | VERIFIED-BOTH | ❌ |
| javascript | 15 | tree-sitter/tree-sitter-javascript | `58404d8cf191` | VERIFIED-BOTH | ❌ |
| jsdoc | 15 | tree-sitter/tree-sitter-jsdoc | `658d18dcdddb` | VERIFIED-BOTH | ✅ |
| json | 14 | tree-sitter/tree-sitter-json | `001c28d7a298` | VERIFIED-BOTH | ❌ |
| json5 | 15 | Joakker/tree-sitter-json5 | `aa630ef48903` | VERIFIED-BOTH | ✅ |
| jsonnet | 14 | sourcegraph/tree-sitter-jsonnet | `ddd075f1939a` | VERIFIED-BOTH | ✅ |
| julia | 15 | tree-sitter/tree-sitter-julia | `8454f2667172` | VERIFIED-HELIX | ❌ |
| kconfig | 14 | tree-sitter-grammars/tree-sitter-kconfig | `9ac99fe4c0c2` | VERIFIED-BOTH | ✅ |
| kdl | 14 | tree-sitter-grammars/tree-sitter-kdl | `b37e3d58e5c5` | VERIFIED-NVIM | ✅ |
| kotlin | 14 | fwcd/tree-sitter-kotlin | `93bfeee1555d` | VERIFIED-BOTH | ✅ |
| lean | 13 | Julian/tree-sitter-lean | `d98426109258` | VERIFIED-HELIX | ❌ |
| linkerscript | 14 | tree-sitter-grammars/tree-sitter-linkerscript | `f99011a35542` | VERIFIED-NVIM | ✅ |
| liquid | 14 | hankthetank27/tree-sitter-liquid | `9566ca799110` | VERIFIED-NVIM | ✅ |
| llvm | 15 | benwilliamgraham/tree-sitter-llvm | `2914786ae677` | VERIFIED-BOTH | ✅ |
| lua | 15 | tree-sitter-grammars/tree-sitter-lua | `10fe0054734e` | VERIFIED-BOTH | ❌ |
| luau | 14 | tree-sitter-grammars/tree-sitter-luau | `a8914d6c1fc5` | VERIFIED-NVIM | ✅ |
| make | 15 | tree-sitter-grammars/tree-sitter-make | `70613f3d812c` | VERIFIED-NVIM | ❌ |
| markdown | 15 | tree-sitter-grammars/tree-sitter-markdown | `f969cd3ae3f9` | VERIFIED-BOTH | ❌ |
| matlab | 15 | acristoffers/tree-sitter-matlab | `c2390a59016f` | VERIFIED-BOTH | ❌ |
| mermaid | 14 | monaqa/tree-sitter-mermaid | `90ae195b3193` | VERIFIED-BOTH | ✅ |
| meson | 15 | tree-sitter-grammars/tree-sitter-meson | `c84f3540624b` | VERIFIED-BOTH | ❌ |
| nasm | 14 | naclsn/tree-sitter-nasm | `d1b3638d017f` | VERIFIED-BOTH | ✅ |
| nickel | 15 | nickel-lang/tree-sitter-nickel | `b5b6cc3bc7b9` | VERIFIED-BOTH | ✅ |
| nim | 14 | alaviss/tree-sitter-nim | `3878440d9398` | VERIFIED-BOTH | ❌ |
| nix | 13 | nix-community/tree-sitter-nix | `eabf96807ea4` | VERIFIED-BOTH | ❌ |
| objc | 14 | tree-sitter-grammars/tree-sitter-objc | `181a81b8f23a` | VERIFIED-NVIM | ❌ |
| ocaml | 14 | tree-sitter/tree-sitter-ocaml | `5a979b3ec7f1` | VERIFIED-BOTH | ❌ |
| odin | 14 | tree-sitter-grammars/tree-sitter-odin | `d2ca8efb4487` | VERIFIED-BOTH | ✅ |
| pascal | 14 | Isopod/tree-sitter-pascal | `042119eca2e1` | VERIFIED-BOTH | ✅ |
| perl | 14 | tree-sitter-perl/tree-sitter-perl | `ea9667dc65a8` | VERIFIED-BOTH | ❌ |
| php | 15 | tree-sitter/tree-sitter-php | `3f2465c217d0` | VERIFIED-BOTH | ❌ |
| pkl | 15 | apple/tree-sitter-pkl | `f5beed1da8e5` | VERIFIED-BOTH | ❌ |
| po | 14 | tree-sitter-grammars/tree-sitter-po | `bd860a0f57f6` | VERIFIED-NVIM | ✅ |
| pony | 14 | tree-sitter-grammars/tree-sitter-pony | `73ff874ae4c9` | VERIFIED-NVIM | ✅ |
| powershell | 15 | airbus-cert/tree-sitter-powershell | `73800ecc8bdd` | VERIFIED-BOTH | ✅ |
| prisma | 15 | victorhqc/tree-sitter-prisma | `3556b2c1f20e` | VERIFIED-BOTH | ✅ |
| properties | 14 | tree-sitter-grammars/tree-sitter-properties | `6310671b24d4` | VERIFIED-BOTH | ✅ |
| puppet | 14 | tree-sitter-grammars/tree-sitter-puppet | `15f192929b7d` | VERIFIED-NVIM | ✅ |
| purescript | 15 | postsolar/tree-sitter-purescript | `f541f95ffd68` | VERIFIED-BOTH | ✅ |
| python | 15 | tree-sitter/tree-sitter-python | `v0.25.0` | VERIFIED-BOTH | ❌ |
| r | 14 | r-lib/tree-sitter-r | `0e6ef7741712` | VERIFIED-BOTH | ❌ |
| racket | 14 | 6cdh/tree-sitter-racket | `54649be8b939` | VERIFIED-NVIM | ✅ |
| regex | 15 | tree-sitter/tree-sitter-regex | `b2ac15e27fce` | VERIFIED-BOTH | ✅ |
| requirements | 14 | tree-sitter-grammars/tree-sitter-requirements | `caeb2ba854de` | VERIFIED-BOTH | ✅ |
| rescript | 15 | rescript-lang/tree-sitter-rescript | `43c2f1f35024` | VERIFIED-BOTH | ✅ |
| ron | 14 | tree-sitter-grammars/tree-sitter-ron | `78938553b930` | VERIFIED-BOTH | ❌ |
| rst | 14 | stsewd/tree-sitter-rst | `4e562e1598b9` | VERIFIED-BOTH | ✅ |
| ruby | 14 | tree-sitter/tree-sitter-ruby | `ad907a69da0c` | VERIFIED-BOTH | ❌ |
| rust | 15 | tree-sitter/tree-sitter-rust | `77a3747266f4` | VERIFIED-BOTH | ✅ |
| scala | 15 | tree-sitter/tree-sitter-scala | `14c5cfd2b8e0` | VERIFIED-BOTH | ✅ |
| scheme | 14 | 6cdh/tree-sitter-scheme | `c6cb7c7d7a04` | VERIFIED-BOTH | ✅ |
| scss | 14 | serenadeai/tree-sitter-scss | `c478c6868648` | MISMATCH | ❌ |
| slang | 15 | tree-sitter-grammars/tree-sitter-slang | `1dbcc4abc7b3` | VERIFIED-BOTH | ✅ |
| smali | 14 | tree-sitter-grammars/tree-sitter-smali | `fdfa6a1febc4` | VERIFIED-BOTH | ✅ |
| smithy | 14 | indoorvivants/tree-sitter-smithy | `ec4fe14586f2` | VERIFIED-BOTH | ✅ |
| solidity | 15 | JoranHonig/tree-sitter-solidity | `048fe686cb1f` | VERIFIED-BOTH | ✅ |
| soql | 14 | aheber/tree-sitter-sfapex | `3597575a4297` | VERIFIED-NVIM | ✅ |
| sosl | 14 | aheber/tree-sitter-sfapex | `3597575a4297` | VERIFIED-NVIM | ✅ |
| sql | 15 | DerekStride/tree-sitter-sql | `851e9cb257ba` | VERIFIED-BOTH | ❌ |
| squirrel | 14 | tree-sitter-grammars/tree-sitter-squirrel | `072c969749e6` | VERIFIED-NVIM | ✅ |
| starlark | 14 | tree-sitter-grammars/tree-sitter-starlark | `a453dbf3ba43` | VERIFIED-NVIM | ✅ |
| svelte | 14 | tree-sitter-grammars/tree-sitter-svelte | `ae5199db4775` | VERIFIED-NVIM | ❌ |
| sway | 14 | FuelLabs/tree-sitter-sway | `9b7845ce06ec` | VERIFIED-BOTH | ✅ |
| swift | 14 | alex-pinkus/tree-sitter-swift | `8abb3e8b3325` | VERIFIED-BOTH | ❌ |
| systemverilog | 15 | gmlarumbe/tree-sitter-systemverilog | `293928578cb2` | VERIFIED-BOTH | ✅ |
| tablegen | 14 | tree-sitter-grammars/tree-sitter-tablegen | `b1170880c613` | VERIFIED-NVIM | ✅ |
| tcl | 15 | tree-sitter-grammars/tree-sitter-tcl | `8f11ac7206a5` | VERIFIED-BOTH | ✅ |
| teal | 15 | euclidianAce/tree-sitter-teal | `05d276e73705` | VERIFIED-BOTH | ✅ |
| templ | 15 | vrischmann/tree-sitter-templ | `1c6db04effbc` | VERIFIED-BOTH | ✅ |
| thrift | 14 | tree-sitter-grammars/tree-sitter-thrift | `68fd0d80943a` | VERIFIED-BOTH | ✅ |
| tlaplus | 14 | tlaplus-community/tree-sitter-tlaplus | `add40814fda3` | VERIFIED-BOTH | ✅ |
| toml | 14 | tree-sitter-grammars/tree-sitter-toml | `64b56832c2cf` | MISMATCH | ❌ |
| tsx | 14 | tree-sitter/tree-sitter-typescript | `75b3874edb2d` | VERIFIED-BOTH | ❌ |
| typescript | 14 | tree-sitter/tree-sitter-typescript | `75b3874edb2d` | VERIFIED-BOTH | ❌ |
| typst | 14 | uben0/tree-sitter-typst | `46cf4ded12ee` | VERIFIED-BOTH | ✅ |
| verilog | 14 | tree-sitter/tree-sitter-verilog | `4457145e795b` | VERIFIED-HELIX | ❌ |
| vhdl | 15 | jpt13653903/tree-sitter-vhdl | `c2d9be3d5ab7` | MISMATCH | ✅ |
| vim | 15 | tree-sitter-grammars/tree-sitter-vim | `3092fcd99eb8` | VERIFIED-BOTH | ❌ |
| vue | 15 | tree-sitter-grammars/tree-sitter-vue | `ce8011a414fd` | VERIFIED-NVIM | ❌ |
| wgsl | 13 | szebniok/tree-sitter-wgsl | `40259f3c77ea` | VERIFIED-BOTH | ✅ |
| wit | 15 | bytecodealliance/tree-sitter-wit | `v1.3.0` | VERIFIED-NVIM | ✅ |
| xml | 14 | tree-sitter-grammars/tree-sitter-xml | `5000ae8f22d1` | VERIFIED-NVIM | ❌ |
| yaml | 14 | tree-sitter-grammars/tree-sitter-yaml | `4463985dfccc` | VERIFIED-NVIM | ❌ |
| zig | 14 | tree-sitter-grammars/tree-sitter-zig | `6479aa13f32f` | VERIFIED-BOTH | ❌ |

## First-party / self-maintained

These grammars are **authored and maintained in-house** (per the maintainer) — they are not tracked by nvim-treesitter or Helix and are **not** swept from any upstream. Treat them as owned source; do not overwrite from a public repo.

| grammar | cur ABI | LICENSE |
|---|:---:|:---:|
| assembly | 14 | ✅ |
| cfml | 15 | ✅ |
| cfscript | 15 | ✅ |
| cobol | 14 | ❌ |
| dotenv | 15 | ✅ |
| form | 15 | ❌ |
| janet | 14 | ❌ |
| magma | 15 | ❌ |
| pine | 14 | ✅ |
| protobuf | 13 | ❌ |
| qml | 14 | ✅ |
| wolfram | 13 | ❌ |

## Registry disagreement — needs a maintainer decision

Our resolved repo differs from what the registries list, and the two registries disagree with each other (or only one lists it). Pick the canonical source before vendoring.

| grammar | our resolution | nvim-treesitter | Helix |
|---|---|---|---|
| jinja2 | dbt-labs/tree-sitter-jinja2 | - | varpeti/tree-sitter-jinja2 |
| just | casey/tree-sitter-just | IndianBoy42/tree-sitter-just | poliorcetics/tree-sitter-just |
| move | tree-sitter-grammars/tree-sitter-move | - | tzakian/tree-sitter-move |
| sshconfig | ObserverOfTime/tree-sitter-ssh-config | tree-sitter-grammars/tree-sitter-ssh-config | - |
| zsh | tree-sitter-grammars/tree-sitter-zsh | georgeharker/tree-sitter-zsh | - |
