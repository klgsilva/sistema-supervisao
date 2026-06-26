from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BALANCO_ITENS_FIXOS, ChecklistItem, CorredorLoja, Loja, SupervisorLoja, Usuario


bp = Blueprint("admin", __name__, url_prefix="/admin")


def criar_itens_fixos_balanco(loja):
    for ordem, nome_item in enumerate(BALANCO_ITENS_FIXOS, start=1):
        existe = CorredorLoja.query.filter_by(loja_id=loja.id, nome=nome_item).first()
        if not existe:
            db.session.add(
                CorredorLoja(
                    loja_id=loja.id,
                    nome=nome_item,
                    descricao="Item fixo do balanço",
                    ordem=-100 + ordem,
                    ativo=True,
                )
            )


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.route("/lojas", methods=["GET", "POST"])
@admin_required
def lojas():
    if request.method == "POST":
        loja = Loja(
            nome=request.form["nome"].strip(),
            codigo=request.form["codigo"].strip().upper(),
            ativa=bool(request.form.get("ativa")),
        )
        db.session.add(loja)
        db.session.flush()
        criar_itens_fixos_balanco(loja)
        db.session.commit()
        flash("Loja cadastrada.", "success")
        return redirect(url_for("admin.lojas"))

    lojas_lista = Loja.query.order_by(Loja.nome).all()
    lojas_ids = [loja.id for loja in lojas_lista]
    corredor_loja_id = request.args.get("corredor_loja_id", type=int)
    if corredor_loja_id not in lojas_ids:
        corredor_loja_id = None
    todos_corredores = (
        CorredorLoja.query.filter_by(loja_id=corredor_loja_id)
        .order_by(CorredorLoja.ordem, CorredorLoja.nome)
        .all()
        if corredor_loja_id
        else []
    )
    return render_template(
        "admin/lojas.html",
        lojas=lojas_lista,
        corredor_loja_id=corredor_loja_id,
        todos_corredores=todos_corredores,
        itens_fixos_balanco=BALANCO_ITENS_FIXOS,
    )


@bp.route("/lojas/<int:loja_id>/editar", methods=["POST"])
@admin_required
def editar_loja(loja_id):
    loja = db.get_or_404(Loja, loja_id)
    loja.nome = request.form["nome"].strip()
    loja.codigo = request.form["codigo"].strip().upper()
    loja.ativa = bool(request.form.get("ativa"))
    db.session.commit()
    flash("Loja atualizada.", "success")
    return redirect(url_for("admin.lojas"))


@bp.route("/supervisores", methods=["GET", "POST"])
@admin_required
def supervisores():
    if request.method == "POST":
        supervisor = Usuario(
            nome=request.form["nome"].strip(),
            email=request.form["email"].strip().lower(),
            perfil="supervisor",
            ativo=True,
        )
        supervisor.set_password(request.form["senha"])
        db.session.add(supervisor)
        db.session.commit()
        flash("Supervisor cadastrado.", "success")
        return redirect(url_for("admin.supervisores"))

    supervisores_lista = Usuario.query.filter_by(perfil="supervisor").order_by(Usuario.nome).all()
    return render_template("admin/supervisores.html", supervisores=supervisores_lista)


@bp.route("/supervisores/<int:supervisor_id>/editar", methods=["POST"])
@admin_required
def editar_supervisor(supervisor_id):
    supervisor = db.get_or_404(Usuario, supervisor_id)
    supervisor.nome = request.form["nome"].strip()
    supervisor.email = request.form["email"].strip().lower()
    supervisor.ativo = bool(request.form.get("ativo"))
    senha = request.form.get("senha", "").strip()
    if senha:
        supervisor.set_password(senha)
    db.session.commit()
    flash("Supervisor atualizado.", "success")
    return redirect(url_for("admin.supervisores"))


@bp.route("/supervisores/<int:supervisor_id>/excluir", methods=["POST"])
@admin_required
def excluir_supervisor(supervisor_id):
    supervisor = db.get_or_404(Usuario, supervisor_id)
    if supervisor.perfil != "supervisor":
        abort(400)
    if supervisor.visitas:
        flash("Supervisor possui visitas no histórico. Inative em vez de excluir.", "error")
        return redirect(url_for("admin.supervisores"))

    SupervisorLoja.query.filter_by(supervisor_id=supervisor.id).delete()
    db.session.delete(supervisor)
    db.session.commit()
    flash("Supervisor excluído.", "success")
    return redirect(url_for("admin.supervisores"))


@bp.route("/vinculos", methods=["GET", "POST"])
@admin_required
def vinculos():
    supervisores_lista = Usuario.query.filter_by(perfil="supervisor", ativo=True).order_by(Usuario.nome).all()
    lojas_lista = Loja.query.order_by(Loja.nome).all()

    if request.method == "POST":
        supervisor_id = int(request.form["supervisor_id"])
        lojas_ids = {int(valor) for valor in request.form.getlist("lojas")}
        SupervisorLoja.query.filter_by(supervisor_id=supervisor_id).delete()
        for loja_id in lojas_ids:
            db.session.add(SupervisorLoja(supervisor_id=supervisor_id, loja_id=loja_id))
        db.session.commit()
        flash("Vínculos atualizados.", "success")
        return redirect(url_for("admin.vinculos", supervisor_id=supervisor_id))

    supervisor_id = request.args.get("supervisor_id", type=int)
    selecionadas = set()
    if supervisor_id:
        selecionadas = {
            item.loja_id for item in SupervisorLoja.query.filter_by(supervisor_id=supervisor_id).all()
        }

    return render_template(
        "admin/vinculos.html",
        supervisores=supervisores_lista,
        lojas=lojas_lista,
        supervisor_id=supervisor_id,
        selecionadas=selecionadas,
    )


@bp.route("/checklist", methods=["GET", "POST"])
@admin_required
def checklist():
    if request.method == "POST":
        item = ChecklistItem(
            setor=request.form["setor"].strip(),
            descricao=request.form["descricao"].strip(),
            ativo=bool(request.form.get("ativo")),
        )
        db.session.add(item)
        db.session.commit()
        flash("Item cadastrado.", "success")
        return redirect(url_for("admin.checklist"))

    itens = ChecklistItem.query.order_by(ChecklistItem.setor, ChecklistItem.descricao).all()
    return render_template("admin/checklist.html", itens=itens)


@bp.route("/checklist/<int:item_id>/editar", methods=["POST"])
@admin_required
def editar_checklist(item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    item.setor = request.form["setor"].strip()
    item.descricao = request.form["descricao"].strip()
    item.ativo = bool(request.form.get("ativo"))
    db.session.commit()
    flash("Item atualizado.", "success")
    return redirect(url_for("admin.checklist"))
