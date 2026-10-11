"""Trecho do repositório privado (obsidian_agent/storage.py), reproduzido para demonstração.

A memória ensina o que o usuário corrigiu (grafia, categoria), nunca o conteúdo de outra
página: com notas inteiras como exemplo, o modelo local copiava título e resumo de uma
página ao organizar outra (bug encontrado no uso real).
"""

import difflib


def _corrections(row):
    if row["kind"] == "transcription":
        before_words, after_words = row["before"]["text"].split(), row["after"]["text"].split()
        if not before_words:  # transcrição manual: não houve leitura da IA para corrigir
            return []
        pairs = []
        for tag, i, j, k, l in difflib.SequenceMatcher(None, before_words, after_words).get_opcodes():
            # Trocas curtas ensinam a grafia; linhas inseridas ou apagadas seriam conteúdo da página.
            if tag == "replace" and j - i <= 6 and l - k <= 6:
                pairs.append({"antes": " ".join(before_words[i:j]), "depois": " ".join(after_words[k:l])})
        return pairs[:4]
    if row["kind"] == "analysis":
        before = {tuple(s["blocks"]): s for s in row["before"]["segments"]}
        pairs = [{"campo": "categoria", "antes": before[tuple(s["blocks"])]["category"], "depois": s["category"]}
                 for s in row["after"]["segments"]
                 if tuple(s["blocks"]) in before and s["category"] and before[tuple(s["blocks"])]["category"] != s["category"]]
        return pairs[:4]
    # Títulos são específicos de cada página; só a escolha de categoria é um padrão reutilizável.
    pairs = []
    for old, new in zip(row["before"]["organization"]["notes"], row["after"]["organization"]["notes"]):
        if old["category"] != new["category"]:
            pairs.append({"campo": "categoria", "antes": old["category"], "depois": new["category"]})
    return pairs[:4]
