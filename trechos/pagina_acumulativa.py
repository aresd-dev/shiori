"""Trecho do repositório privado (obsidian_agent/publisher.py), reproduzido para demonstração.

Acrescenta trechos marcados ao fim de uma página do vault (ex.: "Ideias para história"):
blocos delimitados, troca atômica só se a página ainda for a que foi lida (o usuário pode
estar editando no Obsidian) e retomada sem duplicar.
"""

import os
import uuid
from pathlib import Path


def _write_replacing(self, path: Path, content: bytes, expected: bytes) -> None:
    """Troca atômica, só se a página ainda for a que lemos (você pode estar editando no Obsidian)."""
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if self._read_page(path) != expected:
            raise PublicationConflict(f"A página {path.name} foi alterada enquanto o programa gravava. Nada foi mudado nela; tente de novo.")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append(self, item: dict) -> None:
    path = self._safe(item["relative_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path = self._safe(item["relative_path"])
    blocks = [block["text"].encode("utf-8") for block in item["blocks"]]
    if not path.exists():
        content = f"# {item['title']}\n".encode("utf-8") + b"".join(blocks)
        temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise PublicationConflict(f"A página {path.name} foi criada por outro programa durante a publicação; tente de novo.") from None
        finally:
            temporary.unlink(missing_ok=True)
        item["created_page"] = True
        return
    if not path.is_file():
        raise UnsafeVaultPath("O destino não é um arquivo comum.")
    current = self._read_page(path)
    missing = [block for block in blocks if block not in current]  # retomada: blocos já gravados ficam como estão
    if missing:
        item.setdefault("created_page", False)
        self._write_replacing(path, current + b"".join(missing), current)
