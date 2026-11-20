"""Confere se um artigo de docs/research cumpre os minimos do PLANO-MELHORIA.md.

Uso: python3 -I docs/research/check_paper.py ARQUIVO.md [--min-total N] [--min-refs N]
Sai com codigo 0 se tudo passar, 1 se algo falhar. Nao altera nada.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# minimos de palavras por secao numerada (prefixo "## N.")
MIN_SECTION = {1: 600, 2: 900, 3: 700, 4: 900, 5: 250, 6: 400, 7: 300, 8: 150}
MAX_SECTION = {8: 320}
FORBIDDEN = re.compile(
    r"onnx|mediapipe|opencv|manifest|sha256|DRAW_|src/draw|pseudoc[oó]digo|limiar|threshold",
    re.IGNORECASE,
)
NUMBER_IN_RESULTS = re.compile(r"\d+(?:[.,]\d+)?\s?(?:%|ms|mm|px|fps)")


def words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def split_sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## +", text, flags=re.MULTILINE)
    out: dict[str, str] = {}
    for part in parts[1:]:
        title, _, body = part.partition("\n")
        out[title.strip()] = body
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--min-total", type=int, default=4500)
    ap.add_argument("--min-refs", type=int, default=25)
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")
    sections = split_sections(text)
    problems: list[str] = []

    def need(ok: bool, msg: str) -> None:
        if not ok:
            problems.append(msg)

    title = re.search(r"^# +(.+)$", text, flags=re.MULTILINE)
    need(bool(title) and words(title.group(1)) <= 20, "titulo ausente ou > 20 palavras")

    for name in ("Resumo", "Abstract"):
        body = sections.get(name, "")
        need(150 <= words(body) <= 250, f"{name}: precisa de 150 a 250 palavras")
    for label in ("Palavras-chave", "Keywords"):
        m = re.search(rf"{label}:?\**:?\s*(.+)", text)
        n = len(re.split(r"[;,]", m.group(1))) if m else 0
        need(4 <= n <= 6, f"{label}: precisa de 4 a 6 itens")

    body_words = 0
    for num, minimum in MIN_SECTION.items():
        key = next((k for k in sections if re.match(rf"{num}\.", k)), None)
        if key is None:
            problems.append(f"falta a secao '## {num}. ...'")
            continue
        n = words(sections[key])
        body_words += n
        need(n >= minimum, f"secao {num}: {n} palavras, minimo {minimum}")
        if num in MAX_SECTION:
            need(n <= MAX_SECTION[num], f"secao {num}: passa de {MAX_SECTION[num]}")
        if num == 5:
            need(
                not NUMBER_IN_RESULTS.search(sections[key]),
                "secao 5 tem numero de resultado: sem dados medidos nao pode ter",
            )
    need(
        body_words >= args.min_total,
        f"corpo (secoes 1 a 8): {body_words} palavras, minimo {args.min_total}",
    )
    need(len(text.replace("\n", " ")) >= int(args.min_total * 6.2), "poucos caracteres")

    figs = re.findall(r"^\*\*Figura \d+\.\*\*\s*(.+)$", text, flags=re.MULTILINE)
    tabs = re.findall(r"^\*\*Tabela \d+\.\*\*\s*(.+)$", text, flags=re.MULTILINE)
    need(len(figs) >= 3, f"figuras com legenda: {len(figs)}, minimo 3")
    need(len(tabs) >= 2, f"tabelas com legenda: {len(tabs)}, minimo 2")
    need(all(words(c) >= 25 for c in figs + tabs), "legenda com menos de 25 palavras")

    decl = sections.get("Declarações", "")
    need(len(re.findall(r"^[-*] ", decl, flags=re.MULTILINE)) >= 6, "declaracoes < 6")

    refs_body = sections.get("Referências", "")
    refs = re.findall(r"^\[\d+\].+$", refs_body, flags=re.MULTILINE)
    need(
        len(refs) >= args.min_refs, f"referencias: {len(refs)}, minimo {args.min_refs}"
    )
    need("[VERIFICAR" not in text, "ainda ha [VERIFICAR ...] no texto")
    need(
        all(("doi.org" in r or "https://" in r) for r in refs),
        "referencia sem DOI ou URL",
    )

    need(not FORBIDDEN.search(text), f"termo proibido: {FORBIDDEN.search(text)}")

    prose = re.sub(r"^[#|>\-*\[!].*$", "", text, flags=re.MULTILINE)
    sentences = [s for s in re.split(r"[.!?]\s", prose) if words(s) > 3]
    avg = sum(words(s) for s in sentences) / max(len(sentences), 1)
    need(avg <= 30, f"frase media com {avg:.0f} palavras, maximo 30")

    print(f"{args.file}: corpo={body_words} palavras, refs={len(refs)}")
    for p in problems:
        print(f"FALHA: {p}")
    print("OK" if not problems else f"{len(problems)} falha(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
