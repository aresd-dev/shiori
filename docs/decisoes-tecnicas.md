# Decisões técnicas

Cada decisão abaixo partiu de um problema concreto. Sempre que possível, foi medida com fotos reais de cadernos (31 páginas, com gabarito escrito à mão para comparar).

## 1. Local primeiro

As anotações são pessoais: planos, estudos, ideias. O Shiori roda inteiro no computador do usuário:
- painel Streamlit preso a `127.0.0.1`;
- banco SQLite em disco;
- modelos de visão e de texto pelo **Ollama**: Qwen3-VL, licença Apache 2.0, rodando na GPU local.

Nenhum serviço externo vem ligado. O Gemini e a pesquisa web (Tavily) são opcionais: exigem chave e uma autorização **por tarefa**, que mostra antes exatamente quais dados sairão do computador. As chaves nunca vão para disco nem para os logs.

## 2. O usuário revisa antes de qualquer coisa chegar ao Obsidian

Uma IA pequena erra. Por isso o fluxo tem pontos de revisão explícitos:
1. corrigir o texto lido;
2. conferir a separação de assuntos;
3. editar as notas;
4. aprovar a publicação.

A autonomia existe em três níveis: assistido, preparação automática e publicação automática restrita a categorias escolhidas. Mudar a metodologia, o modelo ou o vault volta ao nível seguro.

## 3. Texto puro em vez de JSON na leitura da foto

**Problema:** pedindo a transcrição em JSON, o modelo local de 2B entrava em loop de repetição dentro da string (linhas em branco infinitas ou uma linha repetida). O Ollama abortava com `token repeat limit reached`.

**Medição (31 fotos reais):**

| Configuração | Concluídas |
|---|---|
| JSON (original) | 9/31 |
| modelo 4B | 14/31 |
| JSON + penalidade de repetição | 27/31 |
| **texto puro + penalidade de repetição** | **28–29/31** |

As restantes foram lidas depois do realce de imagem. A qualidade se manteve, com 1–4% de erro por caractere nas páginas comuns.

## 4. O modelo classifica, o código separa

Uma folha costuma ter 3–4 assuntos. Pedir a um modelo pequeno que recorte trechos livres é frágil. O Shiori divide a página em parágrafos de forma determinística, e o modelo só responde **assunto e categoria de cada bloco**. Juntar vizinhos, recusar categorias inventadas e marcar dúvidas fica no código.

A primeira regra de junção, só assuntos com o mesmo nome, dividia páginas de um tema só em 4–8 notas. A regra atual junta **vizinhos da mesma categoria**. Resultado no gabarito:
- fronteiras entre assuntos: **9/30 → 22/30**;
- categoria certa: 24/35 com o 2B e 29/35 com o 4B, usando descrições nas categorias.

## 5. Marcações do usuário são determinísticas

Escrever `((ideia para história))` num parágrafo manda aquele trecho, literal e sem passar pela IA, para o fim da página "Ideias para história".
- Parênteses simples continuam sendo texto comum.
- Uma marcação desconhecida vira aviso e nunca é publicada sem um destino aprovado.

## 6. Memória que aprende sem vazar conteúdo

As correções do usuário viram exemplos para as próximas tarefas.

**Bug encontrado no uso real:** a memória enviava notas e textos inteiros de outras páginas, e o modelo copiava título e resumo de uma página ao organizar outra.

**Correção:** a memória guarda só **correções curtas**:
- na transcrição, a grafia (`Fabricer → Fabricar`);
- na organização, a categoria (`Programação → Negócios`).

As correções são filtradas por etapa antes do limite. A prévia de consentimento mostra exatamente o que vai.

## 7. Publicar nunca sobrescreve, e desfazer é seguro

- O manifesto da publicação é gravado **antes** de qualquer arquivo.
- Notas novas são criadas por hardlink exclusivo: se o arquivo já existe, a gravação falha em vez de sobrescrever.
- Desfazer remove só o que continua idêntico ao manifesto, conferido por hash. Uma nota editada depois no Obsidian bloqueia o desfazer inteiro.
- Caminhos são validados contra fuga do vault, incluindo symlinks e junctions do Windows.

## 8. Páginas que acumulam, com blocos delimitados

Para os destinos (página única que cresce), cada publicação acrescenta um bloco entre comentários `<!-- shiori:… -->`, invisíveis na leitura:
- a troca é atômica e só acontece se a página ainda for a que foi lida, porque o usuário pode estar editando no Obsidian;
- uma nova tentativa não duplica o bloco;
- desfazer remove só o próprio bloco e preserva o que o usuário escreveu na página.

## 9. Fila única e confiável

Toda tarefa passa por uma fila persistente em SQLite, com **um único worker**, garantido por trava de processo:
- tarefas idempotentes (o mesmo pedido gera a mesma tarefa, mesmo com cliques repetidos);
- revisão otimista: um resultado antigo não sobrescreve uma edição mais nova;
- chamadas externas marcadas antes de sair: após uma queda, nada é repetido sem nova autorização.

No painel, o "Próximo passo" guia cada etapa, e a tela se atualiza sozinha enquanto há tarefa rodando.

## 10. Testes e medição real

- **160 testes** com pytest, sem rede real (HTTP simulado com `httpx.MockTransport`). O painel é testado com `streamlit.testing`.
- Cada bug encontrado no uso real virou um teste que falhava antes da correção: memória vazando, título copiado do nome da metodologia, abas voltando ao início, rascunhos invalidados ao trocar o vault.
- As taxas citadas vêm de fotos reais e de um gabarito. A suíte garante o comportamento, não o acerto de leitura.
