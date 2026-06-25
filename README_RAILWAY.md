# Deploy no Railway

Use este caminho para colocar o sistema online pelo Railway.

## Arquivos importantes

- `requirements.txt`
- `railway.json`
- `run.py`
- `seed.py`
- `app/`

## Passo a passo

1. Suba o projeto para um repositório no GitHub.
2. Entre em [Railway](https://railway.app).
3. Clique em `New Project`.
4. Escolha `Deploy from GitHub repo`.
5. Selecione o repositório do sistema.
6. Depois que criar o serviço, clique em `New` dentro do projeto.
7. Escolha `Database` > `Add PostgreSQL`.
8. O Railway vai criar a variável `DATABASE_URL` automaticamente.
9. No serviço web, confira se o start command está:

```bash
python seed.py && gunicorn run:app
```

10. Gere um domínio público no serviço web em `Settings` > `Networking`.

## Login inicial

```text
admin@supervisao.local
admin123
```

## Observação sobre fotos

Para demonstração, o upload local funciona. Para produção real, o ideal é usar armazenamento externo para fotos, como Cloudinary, S3 ou Supabase Storage.
