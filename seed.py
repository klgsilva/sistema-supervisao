import os

from app import create_app
from app.extensions import db
from app.models import (
    BALANCO_ITENS_FIXOS,
    PERMISSOES_POR_PERFIL,
    ChecklistItem,
    CorredorLoja,
    Loja,
    SupervisorLoja,
    Usuario,
    UsuarioPermissao,
)
from sqlalchemy import inspect, text


LOJAS_KALICIA = ["Alvorada", "Lirio do Vale", "Compensa", "Ponte", "Cachoeirinha", "Educandos"]
LOJAS_NETE = ["Torquato", "Manoa", "Nova Cidade", "Cidade Nova", "Fuxico", "Zumbi"]

CHECKLIST = [
    ("Atendimento", "Equipe uniformizada e identificada"),
    ("Atendimento", "Padrão de atendimento sendo seguido"),
    ("Loja", "Ambiente limpo e organizado"),
    ("Loja", "Produtos precificados corretamente"),
    ("Estoque", "Rupturas críticas verificadas"),
    ("Caixa", "Procedimentos de caixa conferidos"),
    ("Segurança", "Equipamentos e acessos em conformidade"),
    ("Gestão", "Metas do dia alinhadas com o gerente"),
    ("Avarias", "Verificar se existem avarias na loja"),
    ("Avarias", "Informar quais produtos estão avariados quando houver"),
    ("Validade", "Verificar produtos próximos do vencimento"),
    ("Validade", "Informar quais produtos estão próximos do vencimento quando houver"),
    ("Açougue", "Açougue limpo e organizado"),
    ("Açougue", "Produtos do açougue armazenados corretamente"),
    ("Açougue", "Temperatura do açougue conferida"),
    ("Ilhas", "Ilhas limpas e organizadas"),
    ("Ilhas", "Temperatura das ilhas correta"),
    ("Ilhas", "Verificar se há formação de gelo nas ilhas"),
    ("Hortifruti", "Hortifruti limpo e organizado"),
    ("Hortifruti", "Verificar se há verduras ou frutas podres"),
    ("Promoções", "Produtos solicitados para promoção foram colocados na loja"),
    ("Promoções", "Produtos em promoção estão sinalizados corretamente"),
    ("Promoções", "Produtos em promoção estão em locais estratégicos"),
    ("Reuniões", "Gerentes estão realizando reuniões com os funcionários"),
    ("Reuniões", "Informar os assuntos tratados nas reuniões"),
]


def demo_data_enabled():
    return os.environ.get("SEED_DEMO_DATA", "").lower() in {"1", "true", "yes", "sim"}


def get_or_create_usuario(nome, email, senha, perfil):
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        usuario = Usuario(nome=nome, email=email, perfil=perfil)
        usuario.set_password(senha)
        db.session.add(usuario)
    return usuario


def sincronizar_permissoes_padrao(usuario):
    if usuario.is_admin:
        return
    if usuario.permissoes:
        return
    for permissao in PERMISSOES_POR_PERFIL.get(usuario.perfil, set()):
        db.session.add(UsuarioPermissao(usuario=usuario, permissao=permissao))


def ensure_schema():
    inspector = inspect(db.engine)
    if "ocorrencia" in inspector.get_table_names():
        colunas = {coluna["name"] for coluna in inspector.get_columns("ocorrencia")}
        if "foto_path" not in colunas:
            db.session.execute(text("ALTER TABLE ocorrencia ADD COLUMN foto_path VARCHAR(255)"))
            db.session.commit()
    if "resposta_checklist" in inspector.get_table_names():
        colunas = {coluna["name"] for coluna in inspector.get_columns("resposta_checklist")}
        if "foto_path" not in colunas:
            db.session.execute(text("ALTER TABLE resposta_checklist ADD COLUMN foto_path VARCHAR(255)"))
            db.session.commit()
    if "usuario" in inspector.get_table_names():
        colunas = {coluna["name"] for coluna in inspector.get_columns("usuario")}
        if "ativo" not in colunas:
            db.session.execute(text("ALTER TABLE usuario ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT 1"))
            db.session.commit()
    if "balanco_mensal" in inspector.get_table_names():
        colunas = {coluna["name"] for coluna in inspector.get_columns("balanco_mensal")}
        novas_colunas = {
            "ciclo_balanco_id": "INTEGER",
            "valor_revisado": "NUMERIC(12, 2)",
            "observacao_revisao": "TEXT",
            "data_revisao": "TIMESTAMP",
            "revisado_por_id": "INTEGER",
        }
        for nome, tipo in novas_colunas.items():
            if nome not in colunas:
                db.session.execute(text(f"ALTER TABLE balanco_mensal ADD COLUMN {nome} {tipo}"))
                db.session.commit()
    if "manutencao" in inspector.get_table_names():
        colunas = {coluna["name"] for coluna in inspector.get_columns("manutencao")}
        if "custo" not in colunas:
            db.session.execute(text("ALTER TABLE manutencao ADD COLUMN custo NUMERIC(12, 2) NOT NULL DEFAULT 0"))
            db.session.commit()
        if "foto_path" not in colunas:
            db.session.execute(text("ALTER TABLE manutencao ADD COLUMN foto_path VARCHAR(255)"))
            db.session.commit()


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_schema()

        admin_nome = os.environ.get("ADMIN_NOME", "Administrador")
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@supervisao.local")
        admin_senha = os.environ.get("ADMIN_SENHA", "admin123")

        admin = get_or_create_usuario(admin_nome, admin_email, admin_senha, "admin")
        admin.ativo = True
        db.session.commit()

        Usuario.query.filter_by(perfil="gestor").update({"perfil": "operador"})
        db.session.commit()

        for usuario in Usuario.query.all():
            sincronizar_permissoes_padrao(usuario)
        db.session.commit()

        lojas_por_nome = {}
        for indice, nome in enumerate(LOJAS_KALICIA + LOJAS_NETE, start=1):
            loja = Loja.query.filter_by(nome=nome).first()
            if not loja:
                loja = Loja(nome=nome, codigo=f"L{indice:02d}", ativa=True)
                db.session.add(loja)
            lojas_por_nome[nome] = loja
        db.session.flush()

        for loja in lojas_por_nome.values():
            for ordem, nome_item in enumerate(BALANCO_ITENS_FIXOS, start=1):
                item = CorredorLoja.query.filter_by(loja_id=loja.id, nome=nome_item).first()
                if not item:
                    db.session.add(
                        CorredorLoja(
                            loja_id=loja.id,
                            nome=nome_item,
                            descricao="Item fixo do balanço",
                            ordem=-100 + ordem,
                            ativo=True,
                        )
                    )
                else:
                    item.descricao = item.descricao or "Item fixo do balanço"
                    item.ordem = -100 + ordem
                    item.ativo = True

        for setor, descricao in CHECKLIST:
            existe = ChecklistItem.query.filter_by(setor=setor, descricao=descricao).first()
            if not existe:
                db.session.add(ChecklistItem(setor=setor, descricao=descricao, ativo=True))

        if demo_data_enabled():
            kalicia = get_or_create_usuario("KALICIA LIMA", "kalicia@supervisao.local", "supervisor123", "supervisor")
            nete = get_or_create_usuario("Nete", "nete@supervisao.local", "supervisor123", "supervisor")
            db.session.flush()

            SupervisorLoja.query.delete()
            for nome in LOJAS_KALICIA:
                db.session.add(SupervisorLoja(supervisor_id=kalicia.id, loja_id=lojas_por_nome[nome].id))
            for nome in LOJAS_NETE:
                db.session.add(SupervisorLoja(supervisor_id=nete.id, loja_id=lojas_por_nome[nome].id))

        db.session.commit()
        print("Banco inicial criado/atualizado com admin, lojas e checklist.")
        print(f"Admin: {admin_email} / {admin_senha}")
        if demo_data_enabled():
            print("Dados de demonstração criados.")
            print("KALICIA LIMA: kalicia@supervisao.local / supervisor123")
            print("Nete: nete@supervisao.local / supervisor123")


if __name__ == "__main__":
    seed()
