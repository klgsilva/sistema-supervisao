from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Auditoria,
    BALANCO_ITENS_FIXOS,
    PERFIS_USUARIO,
    PERMISSOES_POR_PERFIL,
    PERMISSOES_USUARIO,
    ChecklistItem,
    CorredorLoja,
    Loja,
    SupervisorLoja,
    Usuario,
    UsuarioPermissao,
)


bp = Blueprint("admin", __name__, url_prefix="/admin")


def registrar_auditoria(acao, entidade=None, entidade_id=None, descricao=None):
    db.session.add(
        Auditoria(
            usuario_id=current_user.id if current_user.is_authenticated else None,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            descricao=descricao,
        )
    )


def permissoes_disponiveis():
    return set(PERMISSOES_USUARIO)


def permissoes_padrao(perfil):
    return PERMISSOES_POR_PERFIL.get(perfil, set()) & permissoes_disponiveis()


def aplicar_permissoes_padrao(usuario):
    if usuario.is_admin:
        return
    for permissao in permissoes_padrao(usuario.perfil):
        db.session.add(UsuarioPermissao(usuario=usuario, permissao=permissao))


def criar_itens_fixos_balanco(loja):
    for ordem, nome_item in enumerate(BALANCO_ITENS_FIXOS, start=1):
        existe = CorredorLoja.query.filter_by(loja_id=loja.id, nome=nome_item).first()
        if not existe:
            db.session.add(
                CorredorLoja(
                    loja_id=loja.id,
                    nome=nome_item,
                    descricao="Item fixo do balanco",
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
        registrar_auditoria("Cadastrou loja", "Loja", loja.id, loja.nome)
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
    registrar_auditoria("Atualizou loja", "Loja", loja.id, loja.nome)
    db.session.commit()
    flash("Loja atualizada.", "success")
    return redirect(url_for("admin.lojas"))


@bp.route("/supervisores", methods=["GET", "POST"])
@admin_required
def supervisores():
    if request.method == "POST":
        perfil = request.form.get("perfil", "supervisor")
        if perfil not in PERFIS_USUARIO:
            abort(400)
        usuario = Usuario(
            nome=request.form["nome"].strip(),
            email=request.form["email"].strip().lower(),
            perfil=perfil,
            ativo=True,
        )
        usuario.set_password(request.form["senha"])
        db.session.add(usuario)
        db.session.flush()
        aplicar_permissoes_padrao(usuario)
        registrar_auditoria("Cadastrou usuario", "Usuario", usuario.id, f"{usuario.nome} - {usuario.perfil_label}")
        db.session.commit()
        flash("Usuario cadastrado.", "success")
        return redirect(url_for("admin.supervisores"))

    usuarios_lista = Usuario.query.order_by(Usuario.nome).all()
    return render_template("admin/supervisores.html", usuarios=usuarios_lista, perfis=PERFIS_USUARIO)


@bp.route("/supervisores/<int:supervisor_id>/editar", methods=["POST"])
@admin_required
def editar_supervisor(supervisor_id):
    usuario = db.get_or_404(Usuario, supervisor_id)
    perfil_anterior = usuario.perfil
    perfil = request.form.get("perfil", usuario.perfil)
    if perfil not in PERFIS_USUARIO:
        abort(400)
    usuario.nome = request.form["nome"].strip()
    usuario.email = request.form["email"].strip().lower()
    usuario.perfil = perfil
    usuario.ativo = bool(request.form.get("ativo"))
    senha = request.form.get("senha", "").strip()
    if senha:
        usuario.set_password(senha)
    if usuario.permissoes:
        permissoes_atuais = {item.permissao for item in usuario.permissoes}
        permissoes_validas = permissoes_disponiveis()
        for item in list(usuario.permissoes):
            if item.permissao not in permissoes_validas:
                db.session.delete(item)
        if perfil_anterior != perfil:
            UsuarioPermissao.query.filter_by(usuario_id=usuario.id).delete()
            aplicar_permissoes_padrao(usuario)
    registrar_auditoria("Atualizou usuario", "Usuario", usuario.id, f"{usuario.nome} - {usuario.perfil_label}")
    db.session.commit()
    flash("Usuario atualizado.", "success")
    return redirect(url_for("admin.supervisores"))


@bp.route("/supervisores/<int:supervisor_id>/excluir", methods=["POST"])
@admin_required
def excluir_supervisor(supervisor_id):
    usuario = db.get_or_404(Usuario, supervisor_id)
    if usuario.id == current_user.id:
        abort(400)
    if usuario.visitas:
        flash("Usuario possui visitas no historico. Inative em vez de excluir.", "error")
        return redirect(url_for("admin.supervisores"))

    SupervisorLoja.query.filter_by(supervisor_id=usuario.id).delete()
    registrar_auditoria("Excluiu usuario", "Usuario", usuario.id, usuario.nome)
    db.session.delete(usuario)
    db.session.commit()
    flash("Usuario excluido.", "success")
    return redirect(url_for("admin.supervisores"))


@bp.route("/vinculos", methods=["GET", "POST"])
@admin_required
def vinculos():
    supervisores_lista = (
        Usuario.query.filter(Usuario.perfil != "admin", Usuario.ativo.is_(True))
        .order_by(Usuario.nome)
        .all()
    )
    lojas_lista = Loja.query.order_by(Loja.nome).all()
    permissoes_validas = permissoes_disponiveis()

    if request.method == "POST":
        supervisor_id = int(request.form["supervisor_id"])
        usuario = db.get_or_404(Usuario, supervisor_id)
        if usuario.is_admin:
            abort(400)
        lojas_ids = {int(valor) for valor in request.form.getlist("lojas")}
        permissoes = {valor for valor in request.form.getlist("permissoes") if valor in permissoes_validas}
        if not permissoes:
            flash("Marque pelo menos uma permissao para este usuario.", "error")
            return redirect(url_for("admin.vinculos", supervisor_id=supervisor_id))

        SupervisorLoja.query.filter_by(supervisor_id=supervisor_id).delete()
        for loja_id in lojas_ids:
            db.session.add(SupervisorLoja(supervisor_id=supervisor_id, loja_id=loja_id))

        UsuarioPermissao.query.filter_by(usuario_id=supervisor_id).delete()
        for permissao in permissoes:
            db.session.add(UsuarioPermissao(usuario_id=supervisor_id, permissao=permissao))
        registrar_auditoria(
            "Atualizou vinculos",
            "Usuario",
            usuario.id,
            f"{usuario.nome}: {len(lojas_ids)} lojas, {len(permissoes)} permissoes",
        )
        db.session.commit()
        flash("Vinculos atualizados.", "success")
        return redirect(url_for("admin.vinculos", supervisor_id=supervisor_id))

    supervisor_id = request.args.get("supervisor_id", type=int)
    usuario_selecionado = db.session.get(Usuario, supervisor_id) if supervisor_id else None
    if usuario_selecionado and usuario_selecionado.is_admin:
        usuario_selecionado = None
        supervisor_id = None
    selecionadas = set()
    permissoes_selecionadas = set()
    if supervisor_id:
        selecionadas = {
            item.loja_id for item in SupervisorLoja.query.filter_by(supervisor_id=supervisor_id).all()
        }
        permissoes_selecionadas = {
            item.permissao for item in UsuarioPermissao.query.filter_by(usuario_id=supervisor_id).all()
        }
        if not permissoes_selecionadas and usuario_selecionado:
            permissoes_selecionadas = permissoes_padrao(usuario_selecionado.perfil)

    return render_template(
        "admin/vinculos.html",
        supervisores=supervisores_lista,
        lojas=lojas_lista,
        supervisor_id=supervisor_id,
        usuario_selecionado=usuario_selecionado,
        selecionadas=selecionadas,
        permissoes_itens=PERMISSOES_USUARIO,
        permissoes_selecionadas=permissoes_selecionadas,
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
        db.session.flush()
        registrar_auditoria("Cadastrou checklist", "ChecklistItem", item.id, f"{item.setor} - {item.descricao}")
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
    registrar_auditoria("Atualizou checklist", "ChecklistItem", item.id, f"{item.setor} - {item.descricao}")
    db.session.commit()
    flash("Item atualizado.", "success")
    return redirect(url_for("admin.checklist"))
