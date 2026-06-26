# Sistema de Visita de Supervisão

Sistema web em Flask para controlar visitas diárias de supervisor (a) em 12 lojas, com venda diária, checklist operacional, ocorrências automáticas para respostas NOK, fotos, relatórios e painéis por perfil.

## Tecnologias

- Python Flask
- SQLite local ou PostgreSQL em produção
- SQLAlchemy
- Flask-Migrate
- Flask-Login
- HTML, CSS e JavaScript puro

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

Acesse: `http://127.0.0.1:5000`

## Manual de uso

Para entender o que cada usuário deve fazer no sistema, consulte:

[`MANUAL_USO.md`](MANUAL_USO.md)

## Dados iniciais

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Admin | `admin@supervisao.local` | `admin123` |

O seed cria:

- usuário admin;
- 12 lojas;
- checklist operacional padrão.

Supervisor (a), vínculos, visitas, ocorrências, fotos e balanços começam vazios.

## Deploy no Render + PostgreSQL

1. Crie um repositório no GitHub e envie este projeto.
2. Entre em [Render](https://render.com).
3. Clique em `New` > `Blueprint`.
4. Conecte o repositório do GitHub.
5. O Render vai ler o arquivo `render.yaml` e criar:
   - um Web Service Flask;
   - um banco PostgreSQL;
   - um disco persistente para uploads/fotos.
6. Aguarde o deploy finalizar.
7. Acesse a URL `.onrender.com` criada pelo Render.

O comando de produção roda automaticamente:

```bash
python seed.py && gunicorn run:app
```

Isso cria/atualiza as tabelas e garante os dados iniciais.

## Variáveis de ambiente usadas

| Variável | Uso |
| --- | --- |
| `DATABASE_URL` | conexão PostgreSQL no Render |
| `SECRET_KEY` | chave segura do Flask |
| `UPLOAD_FOLDER` | pasta persistente para fotos |

No Render, o `render.yaml` já configura essas variáveis.

## Lojas iniciais

Lojas cadastradas inicialmente:

Alvorada, Lirio do Vale, Compensa, Ponte, Cachoeirinha, Educandos, Torquato, Manoa, Nova Cidade, Cidade Nova, Fuxico e Zumbi.

## Regras implementadas

- Admin visualiza todas as lojas, visitas e ocorrências, mas não registra visitas.
- Supervisor (a) visualiza apenas as lojas vinculadas.
- Supervisores podem ser inativados; exclusão só é permitida quando não há visitas no histórico.
- Relatórios mostram ranking de vendas diárias registradas nas visitas, balanço fechado por loja, comparação com mês anterior e ranking de problemas.
- Relatórios podem ser filtrados por mês ou dia; admin também pode filtrar por supervisor (a).
- Relatórios podem ser exportados em CSV compatível com Excel.
- Cada loja permite no máximo uma visita por dia por supervisor (a).
- Ao registrar visita, aparecem apenas as lojas ainda pendentes no dia; no dia seguinte a lista reinicia.
- Venda diária aceita formato em reais, como `1.234,56`.
- Comentário é obrigatório quando um item do checklist é marcado como NOK.
- Toda resposta NOK cria uma ocorrência aberta automaticamente e pode receber foto.
- Ocorrências podem ser marcadas como aberta, em andamento, resolvida ou cancelada.
- Ao retornar em uma loja com ocorrência ativa, a visita mostra o alerta para verificar se o problema foi sanado e atualizar o status.
- Checklist operacional aparece agrupado por setor.

## Migrations

O projeto funciona com `python seed.py`, que cria as tabelas e faz pequenos ajustes de schema. Se quiser usar migrações:

```bash
flask --app run.py db init
flask --app run.py db migrate -m "estrutura inicial"
flask --app run.py db upgrade
```
