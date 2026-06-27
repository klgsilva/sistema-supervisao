# Manual de uso - Sistema de Visita de Supervisão

Desenvolvido por Ricardo Klinger.

Este documento explica o que cada perfil de usuário deve fazer no sistema e como usar os principais módulos no dia a dia.

## Perfis do sistema

O sistema possui dois perfis principais:

- **Admin**: gerencia cadastros, vínculos, balanços, relatórios, ocorrências e acompanha tudo.
- **Supervisor (a)**: registra visitas, lança vendas, responde checklist, registra manutenções e lança balanços das lojas vinculadas.

## Fluxo geral

1. O admin cadastra lojas, supervisor (a), vínculos e checklist.
2. O supervisor (a) acessa o sistema pelo celular ou computador.
3. O supervisor (a) registra as visitas das lojas do dia.
4. Em cada visita, informa a venda diária, responde o checklist e adiciona fotos quando necessário.
5. Se marcar NOK, o sistema cria ocorrência automaticamente.
6. O admin acompanha visitas, ocorrências, manutenções, balanços e relatórios.

## O que o admin deve fazer

### 1. Cadastrar lojas

Menu: **Lojas**

O admin deve manter as 12 lojas cadastradas e ativas.

Na tela de lojas, o admin pode:

- cadastrar nova loja;
- editar nome e código;
- ativar ou inativar loja;
- cadastrar corredores/setores da loja.

### 2. Cadastrar corredores por loja

Menu: **Lojas > Corredores por loja**

Cada loja pode ter corredores ou setores próprios.

Exemplos:

- Açougue
- Câmara fria
- Higiene
- Molhos
- Secos
- Hortifruti

Os corredores são usados no lançamento do balanço. Cada loja pode ter uma estrutura diferente.

### 3. Cadastrar supervisor (a)

Menu: **Supervisores**

O admin pode:

- cadastrar supervisor (a);
- editar nome, e-mail e senha;
- ativar ou inativar usuário;
- excluir apenas quando não houver histórico.

O e-mail pode ser real ou fictício, desde que seja único no sistema.

### 4. Vincular supervisor (a) às lojas

Menu: **Vínculos**

O admin escolhe um supervisor (a) e marca quais lojas pertencem a ele.

Regra:

- supervisor (a) só vê as lojas vinculadas;
- admin vê todas as lojas.

### 5. Cadastrar itens de checklist

Menu: **Checklist**

O admin pode cadastrar e editar os itens que serão respondidos nas visitas.

Exemplos de setores:

- Atendimento
- Loja
- Estoque
- Açougue
- Ilhas
- Hortifruti
- Promoções
- Reuniões

### 6. Acompanhar painel principal

Menu: **Painel**

O admin acompanha:

- lojas visitadas hoje;
- pendentes do dia;
- ocorrências ativas;
- detalhes das visitas realizadas.

### 7. Acompanhar ocorrências

Menu: **Ocorrências**

Ocorrência nasce automaticamente quando um item do checklist é marcado como NOK.

O admin pode verificar:

- loja;
- item com problema;
- descrição;
- foto, quando houver;
- status.

Status possíveis:

- aberta;
- em andamento;
- resolvida;
- cancelada.

### 8. Acompanhar manutenções

Menu: **Manutenções**

O admin não registra manutenção. Ele apenas visualiza, filtra e acompanha.

Filtros disponíveis:

- loja;
- categoria;
- status.

Categorias:

- refrigeração / câmara fria;
- manutenção padrão.

### 9. Liberar balanço

Menu: **Balanços**

O admin libera o balanço informando:

- competência;
- data da contagem;
- observação, se necessário.

Depois que o balanço é liberado, os campos de liberação ficam bloqueados para evitar alteração indevida.

O admin também pode alterar o status do balanço:

- aberto;
- fechado;
- cancelado.

Quando o balanço está fechado, supervisor (a) não consegue lançar novos valores.

### 10. Revisar balanço

Menu: **Balanços**

Depois que o supervisor (a) lança o valor fechado, o admin pode inserir o valor revisado, quando a central identificar diferença.

O sistema mostra:

- valor fechado original;
- valor revisado;
- diferença entre fechado e revisado;
- valor considerado no relatório.

### 11. Ver relatórios

Menu: **Relatórios**

O admin pode filtrar por:

- mês;
- dia;
- período escolhido;
- supervisor (a);
- ciclo de balanço.

Opções do relatório:

- rankings;
- visitas por supervisor (a);
- balanço e comparação.

## O que o supervisor (a) deve fazer

### 1. Acessar o painel

Menu: **Painel**

O supervisor (a) vê apenas as lojas vinculadas a ele.

No painel, ele acompanha:

- lojas visitadas hoje;
- lojas pendentes;
- ocorrências ativas das lojas dele.

### 2. Registrar visita

Menu: **Nova visita**

O supervisor (a) deve escolher uma loja pendente do dia.

Regra:

- cada loja pode ter apenas uma visita por dia por supervisor (a);
- no dia seguinte a lista reinicia;
- não existe trava se uma loja não foi visitada no dia anterior.

Na visita, o supervisor (a) informa:

- venda do dia anterior;
- observação geral, se houver;
- respostas do checklist.

### 3. Responder checklist

Cada item pode ser marcado como:

- **OK**: está dentro do padrão;
- **NOK**: está fora do padrão;
- **Informativo**: campo apenas para texto, quando não faz sentido marcar OK/NOK.

Quando marcar **NOK**:

- comentário é obrigatório;
- o sistema cria uma ocorrência aberta automaticamente;
- pode anexar foto.

Quando marcar **OK**:

- pode anexar foto como evidência;
- a foto aparece no detalhe da visita;
- não cria ocorrência.

### Avarias

O item de avarias funciona de forma diferente dos demais:

- marque **Não** quando não existirem avarias na loja;
- marque **Sim** quando existirem avarias;
- ao marcar **Sim**, o sistema exige informar quais produtos estão avariados;
- ao marcar **Sim**, o sistema cria uma ocorrência aberta automaticamente.

Itens de reunião não pedem foto, pois são apenas perguntas e registro de assunto.

### 4. Anexar foto

Nos campos de foto existem duas opções:

- **Tirar foto**: abre a câmera;
- **Galeria**: permite escolher imagem já salva.

Após selecionar ou tirar foto, o sistema mostra uma mensagem confirmando que a foto foi adicionada.

### 5. Ver ocorrências ativas durante a visita

Se a loja possui ocorrência aberta, a tela de nova visita mostra um alerta.

O supervisor (a) deve verificar se o problema foi resolvido e atualizar o status quando necessário.

### 6. Registrar manutenção

Menu: **Manutenções**

O supervisor (a) escolhe a loja e registra a manutenção.

Campos principais:

- categoria;
- tipo;
- status;
- equipamento ou área;
- responsável;
- custo;
- foto opcional;
- problema identificado;
- data da solicitação;
- data de atendimento;
- observação.

Categorias:

- **Refrigeração / Câmara fria**: usada para equipamentos terceirizados e conferência semanal.
- **Manutenção padrão**: usada para itens internos da empresa, como elétrica, computadores e estrutura.

Após salvar, a tela volta ao estado inicial para evitar lançamento duplicado.

Se existir manutenção **pendente** ou **em andamento** de dias anteriores, o sistema mostra um alerta ao escolher a loja. O supervisor (a) deve verificar se foi resolvida e atualizar o status quando necessário.

### 7. Lançar balanço por corredores

Menu: **Balanços**

O supervisor (a) escolhe a loja e informa os valores por itens fixos e por corredor/setor.

Itens fixos do balanço:

- Avarias/Loja;
- Remanejamento;
- Descartes;
- Uso e consumo.

Regras:

- cada corredor lançado fica bloqueado;
- campo em branco continua disponível para lançamento posterior;
- valor `0,00` conta como lançado e significa que não houve valor naquele item;
- quando todos os corredores forem lançados, a loja fica bloqueada;
- supervisor (a) não edita valor já lançado.

Exemplo:

Se a loja tem 5 corredores e o supervisor (a) lança apenas 3, os 3 ficam bloqueados e os outros 2 continuam abertos.

Se no mês não houve Remanejamento, informe `0,00`. Se deixar em branco, o sistema entende que aquele item ainda será lançado depois.

## Relatórios disponíveis

### Rankings

Mostra:

- lojas que mais venderam no dia a dia;
- lojas com mais problemas.

### Visitas por supervisor (a)

Mostra:

- data;
- supervisor (a);
- loja;
- venda;
- quantidade de OK;
- quantidade de NOK;
- informativos;
- ocorrências;
- ocorrências abertas;
- link para abrir o detalhe da visita.

Esse relatório é útil para o admin verificar quais lojas cada supervisor (a) visitou.

### Balanço e comparação

Mostra por loja:

- valor fechado;
- valor revisado;
- diferença da revisão;
- valor considerado;
- mês anterior;
- diferença;
- variação percentual;
- visitas;
- vendas nas visitas;
- média por visita;
- problemas;
- ocorrências abertas;
- ocorrências resolvidas.

## Regras importantes

- Admin não registra visita.
- Admin não registra manutenção.
- Supervisor (a) vê apenas suas lojas.
- Cada loja só pode ter uma visita por dia por supervisor (a).
- Checklist NOK exige comentário.
- Checklist NOK cria ocorrência automaticamente.
- Avarias marcadas como Sim exigem informar quais produtos estão avariados.
- Ocorrência pode ser resolvida ou cancelada depois.
- Foto OK é evidência, não ocorrência.
- Foto NOK fica ligada à ocorrência.
- Balanço só pode ser lançado quando estiver aberto.
- Valor revisado do balanço é lançado pelo admin.
- Corredores são cadastrados na tela de lojas.

## Recomendações de uso

- O supervisor (a) deve registrar a visita no mesmo dia em que ela acontecer.
- O admin deve revisar ocorrências abertas com frequência.
- O admin deve liberar o balanço apenas quando chegar o período correto.
- Antes do primeiro balanço, cadastre os corredores de cada loja.
- Ao fechar o balanço, confira se todas as lojas necessárias já foram lançadas.
