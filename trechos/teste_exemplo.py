"""Trecho do repositório privado (tests/test_pipeline.py), reproduzido para demonstração.

Teste de regressão do bug de memória visto no painel real: depois de aprovar uma página,
organizar outra não pode enviar ao modelo nada do conteúdo da primeira.
"""

def _spy(pipeline):
    seen = {"transcribe": [], "organize": []}

    class Spy(FakeProvider):
        def transcribe(self, image_path, memory):
            seen["transcribe"].append(memory)
            return super().transcribe(image_path, memory)

        def organize(self, text, methodology, memory, subject=""):
            seen["organize"].append(memory)
            return super().organize(text, methodology, memory, subject)

    pipeline.provider_factory = Spy
    return seen


def test_memory_never_leaks_another_page_into_organization(pipeline, capture):
    # Visto no painel real: a nota aprovada de uma página foi enviada como exemplo e o modelo
    # copiou título e resumo dela ao organizar outra página.
    pipeline.queue(capture["id"], "transcribe")
    execute(pipeline)
    pipeline.store.correct_transcription(capture["id"], "Fotossintese transforma energia luminosa em energia quimica.")
    pipeline.queue(capture["id"], "organize")
    execute(pipeline)
    pipeline.store.approve(capture["id"])
    seen = _spy(pipeline)
    other = pipeline.import_text("Mitocôndrias produzem ATP.".encode(), "outra.md")
    pipeline.queue(other["id"], "organize")
    execute(pipeline)
    sent = json.dumps(seen["organize"], ensure_ascii=False)
    assert "Fotossint" not in sent and "energia" not in sent and "quimica" not in sent
