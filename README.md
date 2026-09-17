# Rex Live 🐾

Fases 1 a 3: cachorro virtual, tela vertical e integração de leitura de comentários TikTok. Python 3.10+, SQLite e HTML/CSS/JavaScript. O simulador funciona sem dependências externas; a conexão real usa TikTokLive 7.0.1.

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
- Cinco comandos simulados, XP e níveis; 100 XP por nível.
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
  tiktok_live.py  Leitura de comentários e controle de conexão
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
.venv\Scripts\python.exe -m unittest -v test_rex test_tiktok test_live_rules
node --test test_live_events.cjs
```

São 35 testes Python e 8 JavaScript. Usam bancos temporários e transporte simulado, sem acessar o TikTok ou alterar os dados reais. Cobrem regras do jogo, persistência, migração do banco antigo, API, identificação, intervalo entre cuidados, duplicatas após reiniciar, cancelamento, fim de live e tentativas limitadas. Dois testes verificam o cliente e o formato de evento da biblioteca instalada. Os novos testes verificam sono automático, despertar, ganho real dos cuidados e os limites de tempo dos avisos. Os testes JavaScript verificam a fila e os textos de apresentação. Node.js é necessário apenas para os testes JavaScript.

Compatibilidade: o adaptador assíncrono corrige o fechamento do cliente no TikTokLive 7.0.1, evitando executar um segundo loop dentro do loop ativo. Antes de atualizar a dependência, rode os testes e valide uma live de teste.

Para fazer backup, encerre o servidor e copie `dados/rex.db`. O servidor só escuta em 127.0.0.1. Não exponha esta versão diretamente à internet.

## Próximas etapas

Validar a Fase 3 com a live de @terra.updatess aberta e conferir o enquadramento no software de transmissão. Depois iniciar a Fase 4: presentes, evolução especial, itens e temporadas. Presentes ainda não estão implementados.

## Validação desta revisão

43 testes automatizados passaram. A conferência visual desta reformulação ficou pendente: o controle do navegador foi interrompido por não conseguir identificar o endereço com segurança. A leitura de comentários de uma live real também continua pendente, pois a live não estava aberta.
