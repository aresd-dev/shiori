"""Trecho do repositório privado (obsidian_agent/segmentation.py), reproduzido para demonstração.

Divide a página em parágrafos e aplica as marcações ((…)) do usuário sem IA. O modelo
só classifica cada bloco (assunto + categoria); juntar vizinhos e recusar categorias
inventadas fica no código. Funções puras, fáceis de testar.
"""

import re

from .models import GENERIC_TITLES, Analysis, BlockLabel, Destination, Methodology, Segment, marker_key

_MARKER = re.compile(r"\(\(\s*([^()]+?)\s*\)\)")


def split_blocks(text: str) -> list[str]:
    """Parágrafos separados por linha em branco; para separar assuntos, basta uma linha em branco."""
    blocks = []
    for raw in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n")):
        lines = [line.rstrip() for line in raw.strip("\n").splitlines()]
        block = "\n".join(lines).strip()
        if block:
            blocks.append(block)
    return blocks


def route_blocks(text: str, destinations: list[Destination]) -> Routing:
    """Uma marcação vale para o parágrafo onde está; a primeira marcação conhecida escolhe o destino."""
    known = {marker_key(destination.marker): destination for destination in destinations}
    blocks, notices = [], []
    for raw in split_blocks(text):
        markers = [match.group(1).strip() for match in _MARKER.finditer(raw)]
        cleaned = _without_markers(raw) if markers else raw
        if not cleaned:
            notices.extend(f"A marcação (({marker})) estava sozinha num parágrafo e foi ignorada." for marker in markers)
            continue
        destination = next((known[marker_key(marker)] for marker in markers if marker_key(marker) in known), None)
        unknown = [marker for marker in markers if marker_key(marker) not in known]
        blocks.append(RoutedBlock(index=len(blocks), text=cleaned, markers=markers, destination=destination, unknown=unknown))
    return Routing(blocks=blocks, notices=notices)


def build_analysis(routing: Routing, labels: list[BlockLabel], methodology: Methodology) -> Analysis:
    """Junta blocos vizinhos do mesmo assunto e categoria; marcações vão direto ao destino, sem IA."""
    categories = {category.name for category in methodology.categories}
    pages = {marker_key(d.marker): d.page for d in methodology.destinations}
    by_index = {label.indice: label for label in labels}
    segments: list[Segment] = []
    uncertainties: list[str] = []
    for block in routing.blocks:
        for marker in block.unknown:
            uncertainties.append(f"Marcação nova (({marker})) não tem destino: crie-o na metodologia ou remova a marcação.")
        if block.destination is not None:
            segments.append(Segment(blocks=[block.index], text=block.text, subject=pages[marker_key(block.destination.marker)][:120],
                                    destination=block.destination.marker, unknown_markers=block.unknown))
            continue
        label = by_index.get(block.index)
        if label is None:
            subject, category = block.text.splitlines()[0][:60], ""
            uncertainties.append(f"Bloco {block.index + 1} ficou sem classificação: escolha assunto e categoria.")
        else:
            subject, category = label.assunto.strip(), label.categoria.strip()
            if _plain(subject) in GENERIC_TITLES:
                uncertainties.append(f"Assunto genérico '{subject}' no bloco {block.index + 1}: dê o nome do assunto.")
            if category not in categories:
                # O modelo às vezes inventa categorias ou copia nomes de campos: nada de categoria falsa.
                uncertainties.append(f"Bloco {block.index + 1}: o modelo sugeriu '{category}', que não é uma categoria aprovada; escolha uma.")
                category = ""
        previous = segments[-1] if segments else None
        # Medido em páginas reais: vizinhos da mesma categoria costumam ser o mesmo tema, mesmo com nomes diferentes.
        if previous and not previous.destination and category and previous.category == category:
            previous.blocks.append(block.index)
            previous.text += "\n\n" + block.text
            previous.unknown_markers.extend(block.unknown)
            continue
        segments.append(Segment(blocks=[block.index], text=block.text, subject=subject, category=category, unknown_markers=block.unknown))
    return Analysis(segments=segments, uncertainties=list(dict.fromkeys(uncertainties)), notices=routing.notices)
