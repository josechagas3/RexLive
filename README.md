# Rex Live 🐾

v0.4: cachorro virtual, tela vertical e leitura de comentários e presentes TikTok. Python 3.10+, SQLite e HTML/CSS/JavaScript. O simulador funciona sem dependências externas; a conexão real usa TikTokLive 7.0.1.

## Iniciar no Windows

Nesta revisão, a versão atualizada foi iniciada na porta **8768** para preservar uma instância anterior em 8765: painel em **http://127.0.0.1:8768/** e captura em **http://127.0.0.1:8768/?captura=1**. Para repetir essa porta, execute `.venv\Scripts\python.exe app.py --port 8768` dentro da pasta RexLive. Os passos abaixo usam a porta padrão, 8765, quando estiver livre.

1. Abra `iniciar.bat` e mantenha a janela aberta.
2. No navegador, acesse **http://127.0.0.1:8765**.
3. Informe um nome e use os botões ou digite um comando.
4. Encerre o servidor com Ctrl+C. Os cuidados já ficam salvos automaticamente.

O iniciador usa primeiro o ambiente `.venv` do projeto, depois Python instalado, o launcher `py` e, por último, o Python incluído neste ambiente do Codex. Em outros computadores, instale Python 3.10 ou superior caso necessário. Alternativa pelo terminal, dentro da pasta RexLive:

```console
python app.py
```

Se a porta estiver ocupada: `python app.py --port 8766` e abra a mesma porta no navegador. Não abra o HTML diretamente: ele precisa do servidor Python.

## O que está pronto

- Cachorro vetorial original, animado, com estados normal, fome, feliz, dormindo, comemorando e triste.
- Saciedade (atributo `fome`), vida, felicidade e energia entre 0 e 100.
- Seis comandos simulados, XP e níveis; 100 XP por nível.
- SQLite com estado, ranking local e os últimos 100 cuidados.
- Tela adaptável e modo de captura em **http://127.0.0.1:8765/?captura=1**.
- Atualização da interface a cada segundo; simulação a cada dois segundos.
- Canvas vertical de 1080 × 1920, com top 3 cuidadores na captura e top 5 no painel.
- Fila de agradecimentos, partículas de carinho e aviso de subida de nível.
- Aviso de desconexão, reconexão automática e opção de reduzir animações.
- Conectar/desconectar o perfil TikTok pelo painel, com contadores e estado da conexão.
- Identidade por ID do espectador, proteção contra duplicatas e intervalo de 5 segundos por pessoa.

## Conectar ao TikTok — Fase 3

O perfil padrão é **@terra.updatess**. A biblioteca já está instalada no ambiente `.venv` deste computador. Para preparar outra instalação, execute `instalar_tiktok.bat` com acesso à internet e, depois, `iniciar.bat`. Não copie a pasta `.venv` entre computadores: recrie-a com o instalador.

1. Abra a sua live no TikTok.
2. No painel do Rex, confira **@terra.updatess** em **Conectar sua live**.
3. Clique em **Conectar TikTok** e aguarde o status **Conectado**.
4. Peça a um espectador para comentar exatamente `comida`, `água`, `brincar`, `dormir`, `acordar` ou `carinho`. Também são aceitos `agua`, letras maiúsculas e o prefixo `!`, como `!comida`.
5. Confira o contador de cuidados, o agradecimento e o ranking. Use **Desconectar** para voltar aos botões do simulador.

Não é necessário digitar senha ou cookies no Rex. A ponte apenas recebe eventos: não publica comentários e não envia mensagens para ninguém. Presentes ainda não têm efeito no jogo.

A conexão não começa sozinha ao iniciar o servidor. Se o perfil estiver fora do ar, o painel informa isso e permite tentar novamente. Falhas transitórias têm no máximo quatro tentativas, com pausas de 5, 10 e 20 segundos. O botão Desconectar também cancela uma tentativa em andamento.

Enquanto a conexão está ativa ou sendo tentada, o simulador fica bloqueado. O ranking acumulado preserva os pontos anteriores e identifica entradas de teste com `(teste)` e espectadores com `TikTok`. Duas pessoas com o mesmo apelido continuam separadas pelo ID recebido; mudar o apelido não perde os pontos. O perfil digitado no painel vale até reiniciar o servidor; o padrão está em `config.py`.

Cada espectador pode gerar um cuidado aceito a cada 5 segundos. Outros comentários são ignorados. Reenvios com o mesmo ID não duplicam os pontos; até 10 mil IDs de cuidados aceitos são guardados no SQLite. Os eventos antigos enviados ao entrar na sala são descartados. Uma queda de conexão pode perder comentários que o serviço não reenviar.

`dormir` só coloca Rex para dormir; repetições não o acordam nem rendem XP extra. Somente `!acordar` o desperta, garantindo pelo menos 15 de energia. Comida, água e carinho continuam funcionando durante o sono, sem acordá-lo. Brincar exige Rex acordado. No painel, o botão alterna entre enviar dormir e acordar.

**Limite atual:** integração implementada e testada localmente com transporte simulado e objetos reais da biblioteca. O recebimento de comentários de uma transmissão real ainda não foi validado, pois a live não estava aberta.

A [TikTokLive](https://github.com/isaackogan/TikTokLive) é uma biblioteca não oficial; usa o serviço de assinatura de terceiros Euler Stream, com limites comunitários gratuitos. A disponibilidade depende do TikTok e desse serviço. Não há assinatura paga configurada no Rex. Dependência fixada: [TikTokLive 7.0.1](https://pypi.org/project/TikTokLive/7.0.1/).

## Regras

| Comando | Efeito |
|---|---|
| comida | +10 saciedade |
| água / agua | +5 energia e +3 vida |
| brincar | +15 felicidade, −10 energia, −3 saciedade; exige 10 energia |
| dormir | Coloca Rex para dormir |
| acordar | Acorda Rex e garante pelo menos 15 de energia |
| carinho | +10 felicidade, sem interromper o sono |

Cada cuidado aplicado rende 10 XP para Rex e 10 pontos para o cuidador, mesmo se o atributo já estiver cheio. Ganhos param em 100. O nome identifica o cuidador apenas no simulador; não representa uma identidade autenticada do TikTok.

Por minuto com o servidor ativo: −1,5 saciedade, −0,7 felicidade e −0,25 energia; dormindo, a energia sobe 8 por minuto. A vida perde 2 por minuto com saciedade abaixo de 20, e recupera 0,5 com saciedade acima de 60 e energia acima de 30. Não há morte permanente. O tempo desligado não gera perdas; suspensões longas do computador não são integralmente contabilizadas.

Prioridade dos estados: sono, comemoração de nível (10 segundos), fome abaixo de 30, tristeza se felicidade ou vida estiver abaixo de 30, felicidade após interação (7 segundos), normal.

## Tela de live e momentos de crescimento

A captura usa uma cena vertical de 1080 × 1920 com Rex em destaque, três status principais, pódio dos cuidadores e comandos grandes. A felicidade permanece disponível no painel do criador. Os alertas nomeiam quem cuidou do Rex, mostram o ganho real (limitado a 100%) e incluem uma reação animada por ação. O texto “AU AU!” é visual; não há áudio.

Ao zerar a energia, Rex dorme automaticamente. O sono recupera 8 pontos por minuto, mas ele aguarda um `!acordar` da comunidade, mesmo ao chegar a 100%. Não é necessário esperar: acordar garante um mínimo de 15 pontos. Repetir acordar enquanto ele já está acordado não gera XP.

A cada 30 minutos, um aviso de 20 segundos mostra quanto XP falta para o próximo nível. O relógio começa ao iniciar o servidor no simulador e reinicia ao conectar uma nova sessão TikTok; tentativas automáticas de reconexão mantêm o mesmo relógio. Reiniciar o servidor reinicia o relógio. O XP e o nível mostrados são reais e atualizados durante o aviso.

Use **Testar aviso de crescimento** na seção Preparar a transmissão para exibir uma prévia, sincronizada nas telas abertas, sem alterar XP ou o horário do próximo aviso. Agradecimentos e comemorações de nível têm prioridade visual. Se ocuparem toda a janela de 20 segundos, o aviso periódico não interrompe os cuidados.

## Captura

1. Mantenha o painel em **http://127.0.0.1:8765/** aberto para controlar Rex.
2. Na seção **Preparar a transmissão**, clique em **Abrir tela 9:16** ou copie o endereço. A captura usa **http://127.0.0.1:8765/?captura=1**.
3. Use uma fonte de navegador local com largura **1080** e altura **1920**, quando o software de transmissão oferecer essa opção. Outra opção é capturar a janela do navegador e enquadrar o canvas vertical.
4. A captura mostra Rex, status, XP, agradecimentos e os três primeiros cuidadores. Os botões, formulários e demais controles ficam só no painel.
5. Envie um cuidado pelo painel e confira a outra janela. A atualização normalmente aparece na próxima consulta, a cada segundo.

O canvas mantém a proporção 9:16 e cabe inteiro na janela sem rolagem. Em janelas horizontais, haverá espaço nas laterais: enquadre apenas o canvas na transmissão. O conteúdo tem margens maiores à direita e na base; confira o enquadramento final junto dos elementos da sua live.

Os agradecimentos duram 4,2 segundos, ou 2,2 segundos quando a fila está cheia. Até 30 aguardam apresentação individual; excesso vira um agradecimento coletivo, sem perder os pontos salvos. A API disponibiliza os últimos 100 eventos para recuperar rajadas e interrupções. Ao abrir ou recarregar a captura, os cuidados antigos não são reapresentados. Uma reconexão na mesma página recupera eventos novos; lacunas maiores que o histórico aparecem no resumo coletivo.

A opção **Reduzir animações neste navegador** é salva e compartilhada entre abas da mesma origem. O jogo também respeita a preferência de movimento reduzido do sistema. Outras aplicações de captura podem ter armazenamento próprio.

Se o servidor cair, a captura mostra **Reconectando ao jardim…** e tenta se conectar novamente. Os atributos exibidos são os últimos conhecidos até a conexão voltar. Não há áudio nesta versão.

**A captura dentro do TikTok Live Studio/OBS ainda precisa ser validada nesses aplicativos.** O indicador da captura alterna entre modo simulador, tentativa de conexão e comentários ao vivo conforme o estado recebido do servidor.

## Arquivos

```text
RexLive/
  app.py          Servidor HTTP e coordenação do jogo
  cachorro.py     Regras e emoções
  banco.py        Persistência transacional
  config.py       Caminhos e porta padrão
  tiktok_live.py  Leitura de comentários, presentes e controle de conexão
  presentes.py    Mapeamento e aplicação de efeitos de presentes
  test_presentes.py Testes locais de presentes, combos e persistência
  iniciar.bat     Iniciador para Windows
  instalar_tiktok.bat Prepara o ambiente isolado e instala a integração
  requirements-tiktok.txt Versão da biblioteca
  test_rex.py     Testes automatizados
  test_tiktok.py  Testes de integração sem rede
  momentos.py     Relógio dos avisos de crescimento
  test_live_rules.py Testes de energia e avisos
  test_live_events.cjs Testes da fila de apresentação (Node.js)
  interface/
    index.html    Tela e desenho SVG do Rex
    style.css     Layout e animações
    script.js     Atualização e comandos
    live-events.js Fila de agradecimentos e agrupamento de rajadas
  dados/
    rex.db        Criado automaticamente na primeira execução
```

O desenho está em SVG dentro do HTML; PNGs e uma pasta de imagens não são necessários nesta etapa. Todos os arquivos são completos e editáveis.

## Testar

```console
.venv\Scripts\python.exe -m unittest -v test_rex test_tiktok test_live_rules test_presentes
node --test test_live_events.cjs
```

São 49 testes Python e 11 JavaScript. Os 60 passaram nesta revisão, sem testes ignorados, com TikTokLive instalado. Usam bancos temporários e transporte local, sem acessar uma live ou alterar seus dados. Cobrem comentários, presentes, combos, deduplicação persistente, migração, rollback, concorrência, sono, XP, API e fila visual. Sem TikTokLive, quatro testes específicos da biblioteca são ignorados. Node.js é necessário somente para os testes JavaScript.

Compatibilidade: o adaptador assíncrono corrige o fechamento do cliente no TikTokLive 7.0.1, evitando executar um segundo loop dentro do loop ativo. Antes de atualizar a dependência, rode os testes e valide uma live de teste.

Para fazer backup, encerre o servidor e copie `dados/rex.db`. O servidor só escuta em 127.0.0.1. Não exponha esta versão diretamente à internet.

## Próxima etapa

v0.5: alertas e animações específicos de presentes, ranking visual separado e últimos apoiadores. A captura e os comentários reais já foram validados pelo criador; os presentes desta revisão ainda precisam de validação em live real.

## v0.3 — Evento de comida

A versão v0.2 foi validada em transmissão real pelo criador. Nesta etapa, `!comida` destaca o nome do cuidador, mostra o ganho real de saciedade, partículas de comida e corações, animação de entrada e expressão contente. Rex dormindo permanece dormindo. Quando a saciedade já está cheia, o alerta mostra o XP recebido.

Recarregue o painel e a captura para carregar os arquivos novos. Para áudio, abra **♫ Som do Rex**, no canto inferior direito da janela usada na transmissão, e clique em **Ativar som nesta janela**. Na captura, passe o mouse pelo canto inferior direito para revelar esse controle. Ajuste o volume e feche o controle antes de transmitir; retire o mouse desse canto. Ative somente em uma janela para evitar duplicação e inclua o áudio dessa janela no LIVE Studio. O som sintetizado depende da ativação por clique em cada nova janela e não usa arquivos externos.

Validação local: 35 testes Python e 11 JavaScript passaram; o navegador apresentou o evento no painel e na captura, e confirmou a ativação do áudio. A escuta e a captura do áudio no Studio e a validação com comentários reais ficam para a próxima transmissão.

Roteiro da próxima live: enviar `!comida`, conferir nome e ganho, ouvir os dois sons curtos, enviar cuidados de pessoas diferentes e conferir ordem/ranking. Testar também `!dormir` seguido de `!comida`: Rex deve continuar dormindo. Conferir `!agua`, `!brincar`, `!carinho` e `!acordar`.

## v0.4 — Presentes TikTok

- `Rose`: +5 de saciedade por unidade.
- `Heart Me`: +10 de felicidade por unidade.
- `Coffee`: +20 de energia por unidade.
- `Lion`: registra evento especial; não evolui o Rex nem inventa aumento de atributo.

O nome recebido é comparado sem distinguir maiúsculas/minúsculas. Presentes desconhecidos são ignorados. Quantidades inteiras de 1 a 10.000 são aceitas. Os nomes/variantes disponíveis precisam ser conferidos na live real.

Presentes não concedem XP, não acordam Rex nem ativam os temporizadores de felicidade/comemoração. A expressão normal continua derivada dos atributos e do sono. Atributos permanecem entre 0 e 100; os deltas efetivos ficam registrados.

Cada unidade dá **10 pontos de apoio**, independentemente do tipo. Esses pontos são do ranking de presentes, não XP ou valor monetário. `valor` no banco representa o efeito nominal total do mapeamento, não moedas/diamantes.

`TIKTOK_PRESENTE_COOLDOWN = 1` define um segundo entre aplicações de efeitos por apoiador, independente dos comentários. Durante esse intervalo, presentes válidos continuam registrados, pontuados e enviados ao histórico, mas não alteram atributos (`efeito_aplicado=false`). O combo aplica sua quantidade final de uma vez e conta somente ao terminar; retransmissões são deduplicadas por sala/grupo/usuário/presente ou por mensagem quando não há grupo. A deduplicação de presentes persiste no SQLite após reinícios.

A tabela `presentes` armazena identificador, apoiador, presente, quantidade, efeito nominal e real, pontos, data e chave única. Salvamento do Rex, presente e evento ocorre na mesma transação. A migração é aditiva e preserva comentários/ranking antigos.

`GET /api/estado` mantém `ranking` de comentários e acrescenta `ranking_presentes` e `presentes` (100 mais recentes). Eventos de presentes participam da fila existente e incluem `tipo="presente"` e dados estruturados em `presente`. O ranking da captura ainda mostra comentários; o ranking visual de presentes e as animações por tipo são da v0.5. O painel já informa a quantidade de envios registrados e a fila mostra um agradecimento genérico.

Para carregar esta versão, encerre e inicie novamente o servidor **entre transmissões**, usando a mesma porta, e recarregue painel/captura. O banco existente será migrado na inicialização. Esta implementação não reiniciou sua live nem alterou seu banco de produção.

Validação real pendente: confirmar os presentes disponíveis, enviar uma Rosa e um combo, conferir um único registro/pontuação, testar Coração e Café e observar que não há XP/despertar. Para o Leão, a lógica foi testada localmente; sua recepção real só será confirmada quando ocorrer um envio. Não é necessário comprar presentes para executar os testes automatizados.

Referência do tratamento de combos: https://github.com/isaackogan/TikTokLive/blob/master/examples/gifts.py (também conferido com a biblioteca instalada).

Backup anterior: `backups/antes-v04.bundle` (histórico Git), `backups/antes-v04.patch` (alterações locais anteriores) e `backups/presentes-antes-v04.py` (mapeamento original). Backups locais não entram nos commits.

O commit desta revisão não pôde ser criado: o ambiente bloqueou `.git/index.lock`. Após revisar, registre no seu terminal:

```powershell
git add .gitignore README.md app.py banco.py config.py presentes.py tiktok_live.py test_presentes.py interface/index.html interface/script.js
git commit -m "v0.4: integra presentes TikTok com persistência e pontuação separada"
```
