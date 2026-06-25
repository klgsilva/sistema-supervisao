from datetime import date, datetime
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(30), nullable=False, default="supervisor")
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    lojas = db.relationship("SupervisorLoja", back_populates="supervisor", cascade="all, delete-orphan")
    visitas = db.relationship("Visita", back_populates="supervisor")

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.perfil == "admin"

    @property
    def is_active(self):
        return self.ativo


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


class Loja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    supervisores = db.relationship("SupervisorLoja", back_populates="loja", cascade="all, delete-orphan")
    visitas = db.relationship("Visita", back_populates="loja")
    ocorrencias = db.relationship("Ocorrencia", back_populates="loja")
    balancos = db.relationship("BalancoMensal", back_populates="loja", cascade="all, delete-orphan")
    corredores_balanco = db.relationship("CorredorLoja", back_populates="loja", cascade="all, delete-orphan")
    manutencoes = db.relationship("Manutencao", back_populates="loja", cascade="all, delete-orphan")


class SupervisorLoja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)

    supervisor = db.relationship("Usuario", back_populates="lojas")
    loja = db.relationship("Loja", back_populates="supervisores")

    __table_args__ = (UniqueConstraint("supervisor_id", "loja_id", name="uq_supervisor_loja"),)


class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setor = db.Column(db.String(80), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    respostas = db.relationship("RespostaChecklist", back_populates="checklist_item")


class Visita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    data_visita = db.Column(db.Date, nullable=False, default=date.today)
    venda_dia = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    observacao = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="concluida")

    loja = db.relationship("Loja", back_populates="visitas")
    supervisor = db.relationship("Usuario", back_populates="visitas")
    respostas = db.relationship("RespostaChecklist", back_populates="visita", cascade="all, delete-orphan")
    ocorrencias = db.relationship("Ocorrencia", back_populates="visita", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("loja_id", "supervisor_id", "data_visita", name="uq_visita_loja_supervisor_dia"),
    )


class RespostaChecklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey("visita.id"), nullable=False)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey("checklist_item.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    comentario = db.Column(db.Text)
    foto_path = db.Column(db.String(255))

    visita = db.relationship("Visita", back_populates="respostas")
    checklist_item = db.relationship("ChecklistItem", back_populates="respostas")


class Ocorrencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey("visita.id"), nullable=False)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey("checklist_item.id"), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="aberta")
    foto_path = db.Column(db.String(255))
    data_abertura = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime)

    visita = db.relationship("Visita", back_populates="ocorrencias")
    loja = db.relationship("Loja", back_populates="ocorrencias")
    checklist_item = db.relationship("ChecklistItem")


class Manutencao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    categoria = db.Column(db.String(40), nullable=False)
    area_equipamento = db.Column(db.String(160), nullable=False)
    problema = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default="corretiva")
    responsavel = db.Column(db.String(120))
    custo = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    data_solicitacao = db.Column(db.Date, nullable=False, default=date.today)
    data_atendimento = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default="pendente")
    foto_path = db.Column(db.String(255))
    observacao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    loja = db.relationship("Loja", back_populates="manutencoes")
    usuario = db.relationship("Usuario")


class CicloBalanco(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competencia_mes = db.Column(db.Date, nullable=False)
    data_contagem = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="aberto")
    observacao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    balancos = db.relationship("BalancoMensal", back_populates="ciclo")

    @property
    def aberto(self):
        return self.status == "aberto"


class CorredorLoja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(255))
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    loja = db.relationship("Loja", back_populates="corredores_balanco")
    valores = db.relationship("BalancoCorredor", back_populates="corredor")

    __table_args__ = (UniqueConstraint("loja_id", "nome", name="uq_corredor_loja_nome"),)


class BalancoMensal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(db.Integer, db.ForeignKey("loja.id"), nullable=False)
    ciclo_balanco_id = db.Column(db.Integer, db.ForeignKey("ciclo_balanco.id"))
    mes_referencia = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    observacao = db.Column(db.Text)
    data_lancamento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    valor_revisado = db.Column(db.Numeric(12, 2))
    observacao_revisao = db.Column(db.Text)
    data_revisao = db.Column(db.DateTime)
    revisado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    loja = db.relationship("Loja", back_populates="balancos")
    ciclo = db.relationship("CicloBalanco", back_populates="balancos")
    revisado_por = db.relationship("Usuario")
    corredores = db.relationship("BalancoCorredor", back_populates="balanco", cascade="all, delete-orphan")

    @property
    def valor_considerado(self):
        return self.valor_revisado if self.valor_revisado is not None else self.valor_total

    __table_args__ = (UniqueConstraint("loja_id", "mes_referencia", name="uq_balanco_loja_mes"),)


class BalancoCorredor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balanco_id = db.Column(db.Integer, db.ForeignKey("balanco_mensal.id"), nullable=False)
    corredor_id = db.Column(db.Integer, db.ForeignKey("corredor_loja.id"), nullable=False)
    valor_fechado = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    valor_revisado = db.Column(db.Numeric(12, 2))
    observacao = db.Column(db.Text)
    observacao_revisao = db.Column(db.Text)

    balanco = db.relationship("BalancoMensal", back_populates="corredores")
    corredor = db.relationship("CorredorLoja", back_populates="valores")

    @property
    def valor_considerado(self):
        return self.valor_revisado if self.valor_revisado is not None else self.valor_fechado

    __table_args__ = (UniqueConstraint("balanco_id", "corredor_id", name="uq_balanco_corredor"),)
