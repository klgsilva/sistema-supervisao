# Manual de uso - Sistema de Visita de Supervisao

Desenvolvido por Ricardo Klinger.

Este manual explica o fluxo do sistema e o que cada usuario pode fazer.

## Perfis

O sistema trabalha com tres perfis:

- **Administrador**: faz cadastros, vinculos, checklist, liberacao de balanco, revisoes e acompanhamento geral.
- **Supervisor (a)**: perfil usado para usuarios responsaveis por lojas e rotinas de supervisao.
- **Operador (a)**: perfil usado para usuarios de apoio, checagens ou tarefas especificas.

Importante: para supervisor (a) e operador (a), o acesso real nao fica preso ao nome do perfil. O administrador decide em **Vinculos** quais lojas e quais telas cada usuario pode acessar.

Exemplo: se um operador precisar ver Relatorios, o administrador marca a caixa **Relatorios** para ele. Se nao marcar Financeiro, ele nao acessa Financeiro.

## Fluxo geral

1. O administrador cadastra lojas, corredores, usuarios e checklist.
2. O administrador entra em **Vinculos**.
3. Escolhe o usuario.
4. Marca as lojas liberadas.
5. Marca os acessos liberados.
6. O usuario entra no sistema e ve somente o menu permitido.

## Usuarios

Menu: **Usuarios**

O administrador pode:

- cadastrar usuario;
- escolher perfil: administrador, supervisor (a) ou operador (a);
- editar nome, e-mail, senha e status;
- ativar ou inativar usuario;
- excluir usuario sem historico.

## Vinculos

Menu: **Vinculos**

Nesta tela o administrador escolhe um usuario e marca:

- lojas liberadas;
- Painel;
- Nova visita;
- Ocorrencias;
- Manutencoes;
- Registrar manutencao;
- Atualizar manutencao/ocorrencia;
- Balancos;
- Lancar balanco;
- Relatorios;
- Financeiro.

Se a caixa estiver marcada, o usuario ve e acessa a funcao. Se estiver desmarcada, a funcao nao aparece no menu e tambem fica bloqueada por URL direta.

## Lojas

Menu: **Lojas**

O administrador pode:

- cadastrar lojas;
- editar nome e codigo;
- ativar ou inativar loja;
- cadastrar corredores/setores de cada loja.

Os corredores sao usados no lancamento do balanco. Cada loja pode ter corredores diferentes.

## Checklist

Menu: **Checklist**

O administrador cadastra e edita os itens respondidos nas visitas.

Itens com **NOK** exigem comentario e criam ocorrencia automaticamente.

## Visitas

Menu: **Nova visita**

Usuario com permissao escolhe uma loja pendente do dia e registra:

- venda diaria;
- observacao geral;
- respostas do checklist;
- fotos quando necessario.

Regras:

- cada loja permite uma visita por dia por usuario;
- no dia seguinte a lista de pendentes reinicia;
- loja ja visitada no dia nao aparece para nova visita.

## Avarias

O item de avarias funciona como Sim/Nao:

- marque **Nao** quando nao houver avarias;
- marque **Sim** quando houver avarias;
- ao marcar Sim, e obrigatorio informar quais produtos estao avariados;
- ao marcar Sim, o sistema cria ocorrencia aberta.

## Fotos

Em visitas e manutencoes, quando disponivel:

- **Tirar foto** abre a camera;
- **Galeria** permite escolher imagem salva.

Foto em item OK serve como evidencia. Foto em item NOK fica ligada a ocorrencia.

## Ocorrencias

Menu: **Ocorrencias**

Ocorrencias nascem automaticamente quando um item do checklist e marcado como NOK.

Status possiveis:

- aberta;
- em andamento;
- resolvida;
- cancelada.

Quando uma loja possui ocorrencia aberta, o sistema mostra alerta para verificar se o problema foi sanado.

## Manutencoes

Menu: **Manutencoes**

Usuario com permissao pode registrar manutencao informando:

- loja;
- categoria;
- tipo;
- status;
- area/equipamento;
- responsavel;
- custo;
- foto opcional;
- problema;
- datas;
- observacao.

Categorias:

- **Refrigeracao / Camara fria**: equipamentos terceirizados e controle semanal.
- **Manutencao padrao**: eletrica, computadores, estrutura e itens internos.

Manutencao pendente ou em andamento de dias anteriores aparece como alerta.

## Balancos

Menu: **Balancos**

O administrador libera o balanco informando:

- competencia;
- data da contagem;
- observacao, se necessario.

Usuario com permissao de **Lancar balanco** informa valores por itens fixos e corredores.

Itens fixos:

- Avarias/Loja;
- Remanejamento;
- Descartes;
- Uso e consumo.

Regras:

- corredor lancado fica bloqueado;
- campo em branco continua disponivel para lancamento posterior;
- valor `0,00` conta como lancamento;
- administrador pode lancar valor revisado quando houver correcao da central.

## Relatorios

Menu: **Relatorios**

Disponiveis:

- rankings de vendas e problemas;
- visitas por usuario;
- balanco e comparacao por loja;
- filtros por mes, dia ou periodo escolhido;
- exportacao CSV.

Administrador pode ver tudo. Outros usuarios veem apenas lojas vinculadas e somente se tiverem permissao de Relatorios.

## Financeiro

Menu: **Financeiro**

Modulo reservado para futuras atualizacoes.

Mensagem exibida:

**Parte financeira em atualizacao. Aguarde novas atualizacoes.**

## Regras importantes

- Administrador nao registra visita.
- Administrador nao registra manutencao.
- Supervisor (a) e operador (a) veem apenas lojas vinculadas.
- O menu muda conforme as permissoes marcadas em Vinculos.
- Digitar URL direta nao libera acesso sem permissao.
- Checklist NOK exige comentario.
- Checklist NOK cria ocorrencia automaticamente.
- Balanco so aceita lancamento quando esta aberto.
