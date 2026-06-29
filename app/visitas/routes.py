import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ChecklistItem, Loja, Ocorrencia, RespostaChecklist, SupervisorLoja, Usuario, Visita


bp = Blueprint("visitas", __name__, url_prefix="/visitas")
STATUS_OCORRENCIA = {"aberta", "em_andamento", "resolvida", "cancelada"}
EXTENSOES_IMAGEM = {"png", "jpg", "jpeg", "webp"}
ITENS_TEXTO_LIVRE = (
    "Informar quais produtos estão avariados",
    "Informar quais produtos estão próximos do vencimento",
    "Informar os assuntos tratados nas reuniões",
)
AVARIA_PERGUNTA_PREFIXO = "verificar se existem avarias"
AVARIA_DETALHE_TERMOS = ("informar", "produtos", "avariados")


def parse_reais(valor):
    texto = (valor or "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError("Venda do dia inválida.")


def salvar_foto_ocorrencia(arquivo):
    if not arquivo or not arquivo.filename:
        return None

    nome_seguro = secure_filename(arquivo.filename)
    extensao = nome_seguro.rsplit(".", 1)[-1].lower() if "." in nome_seguro else ""
    if extensao not in EXTENSOES_IMAGEM:
        raise ValueError("A foto da ocorrência deve ser PNG, JPG, JPEG ou WEBP.")

    pasta = os.path.join(current_app.config["UPLOAD_FOLDER"], "ocorrencias")
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = f"{uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(pasta, nome_arquivo))
    return f"uploads/ocorrencias/{nome_arquivo}"


def item_texto_livre(item):
    return any(item.descricao.startswith(prefixo) for prefixo in ITENS_TEXTO_LIVRE)


def item_avaria_pergunta(item):
    return item.setor == "Avarias" and item.descricao.lower().startswith(AVARIA_PERGUNTA_PREFIXO)


def item_avaria_detalhe(item):
    descricao = item.descricao.lower()
    return item.setor == "Avarias" and all(termo in descricao for termo in AVARIA_DETALHE_TERMOS)


def item_permite_foto(item):
    return item.setor != "Reuniões" and not item_texto_livre(item)


def arquivo_foto_item(item_id):
    for nome in (f"foto_camera_{item_id}", f"foto_galeria_{item_id}", f"foto_{item_id}"):
        arquivo = request.files.get(nome)
        if arquivo and arquivo.filename:
            return arquivo
    return None


def lojas_permitidas():
    return (
        Loja.query.join(SupervisorLoja)
        .filter(SupervisorLoja.supervisor_id == current_user.id, Loja.ativa.is_(True))
        .order_by(Loja.nome)
        .all()
    )


def lojas_pendentes_hoje():
    lojas = lojas_permitidas()
    visitadas_ids = {
        visita.loja_id
        for visita in Visita.query.filter_by(
            supervisor_id=current_user.id,
            data_visita=date.today(),
        ).all()
    }
    return [loja for loja in lojas if loja.id not in visitadas_ids]


def supervisor_pode_loja(supervisor_id, loja_id):
    if current_user.can_view_all_stores:
        return True
    return (
        SupervisorLoja.query.filter_by(supervisor_id=supervisor_id, loja_id=loja_id).first()
        is not None
    )


def loja_vinculada_ao_supervisor(supervisor_id, loja_id):
    return (
        SupervisorLoja.query.filter_by(supervisor_id=supervisor_id, loja_id=loja_id).first()
        is not None
    )


def ocorrencias_ativas_por_loja(lojas):
    lojas_ids = [loja.id for loja in lojas]
    if not lojas_ids:
        return {}
    ocorrencias = (
        Ocorrencia.query.filter(
            Ocorrencia.loja_id.in_(lojas_ids),
            Ocorrencia.status.in_(["aberta", "em_andamento"]),
        )
        .order_by(Ocorrencia.data_abertura.desc())
        .all()
    )
    agrupadas = {}
    for ocorrencia in ocorrencias:
        agrupadas.setdefault(ocorrencia.loja_id, []).append(ocorrencia)
    return agrupadas


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if not current_user.can_access("nova_visita"):
        abort(403)

    lojas = lojas_pendentes_hoje()
    itens = ChecklistItem.query.filter_by(ativo=True).order_by(ChecklistItem.setor, ChecklistItem.id).all()
    ocorrencias_ativas = ocorrencias_ativas_por_loja(lojas)

    if request.method == "POST":
        loja_id = request.form.get("loja_id", type=int)
        supervisor_id = current_user.id

        lojas_ids = {loja.id for loja in lojas}
        if (
            not loja_id
            or not supervisor_id
            or loja_id not in lojas_ids
            or not loja_vinculada_ao_supervisor(supervisor_id, loja_id)
        ):
            abort(403)

        visita_existente = Visita.query.filter_by(
            loja_id=loja_id,
            supervisor_id=supervisor_id,
            data_visita=date.today(),
        ).first()
        if visita_existente:
            flash("Esta loja já possui visita hoje para este supervisor.", "error")
            return render_template("visitas/form.html", lojas=lojas, itens=itens, ocorrencias_ativas=ocorrencias_ativas, item_texto_livre=item_texto_livre, item_avaria_pergunta=item_avaria_pergunta, item_avaria_detalhe=item_avaria_detalhe)

        erros = []
        respostas = []
        item_detalhe_avarias = next((item for item in itens if item_avaria_detalhe(item)), None)
        for item in itens:
            comentario = request.form.get(f"comentario_{item.id}", "").strip()
            if item_avaria_detalhe(item):
                continue
            if item_avaria_pergunta(item):
                status = request.form.get(f"status_{item.id}")
                comentario_avarias = (
                    request.form.get(f"comentario_{item_detalhe_avarias.id}", "").strip()
                    if item_detalhe_avarias
                    else comentario
                )
                if status not in {"OK", "NOK"}:
                    erros.append(f"Responda o item: {item.descricao}")
                if status == "NOK" and not comentario_avarias:
                    erros.append("Informe quais produtos estão avariados.")
                foto = arquivo_foto_item(item.id) if item_permite_foto(item) else None
                respostas.append((item, status, comentario_avarias if status == "NOK" else "", foto))
                if item_detalhe_avarias:
                    respostas.append((item_detalhe_avarias, "INFO", comentario_avarias, None))
                continue
            if item_texto_livre(item):
                respostas.append((item, "INFO", comentario, None))
                continue

            status = request.form.get(f"status_{item.id}")
            if status not in {"OK", "NOK"}:
                erros.append(f"Responda o item: {item.descricao}")
            if status == "NOK" and not comentario:
                erros.append(f"Comentário obrigatório para NOK: {item.descricao}")
            foto = arquivo_foto_item(item.id) if item_permite_foto(item) else None
            respostas.append((item, status, comentario, foto))

        try:
            venda_dia = parse_reais(request.form.get("venda_dia"))
        except ValueError as exc:
            erros.append(str(exc))

        if erros:
            db.session.rollback()
            for erro in erros:
                flash(erro, "error")
            return render_template("visitas/form.html", lojas=lojas, itens=itens, ocorrencias_ativas=ocorrencias_ativas, item_texto_livre=item_texto_livre, item_avaria_pergunta=item_avaria_pergunta, item_avaria_detalhe=item_avaria_detalhe)

        visita = Visita(
            loja_id=loja_id,
            supervisor_id=supervisor_id,
            data_visita=date.today(),
            venda_dia=venda_dia,
            observacao=request.form.get("observacao", "").strip(),
            status="concluida",
        )
        db.session.add(visita)
        db.session.flush()

        fotos_por_item = {}
        for item, status, comentario, foto in respostas:
            if foto and foto.filename:
                try:
                    fotos_por_item[item.id] = salvar_foto_ocorrencia(foto)
                except ValueError as exc:
                    erros.append(str(exc))

        if erros:
            db.session.rollback()
            for erro in erros:
                flash(erro, "error")
            return render_template("visitas/form.html", lojas=lojas, itens=itens, ocorrencias_ativas=ocorrencias_ativas, item_texto_livre=item_texto_livre, item_avaria_pergunta=item_avaria_pergunta, item_avaria_detalhe=item_avaria_detalhe)

        for item, status, comentario, foto in respostas:
            resposta = RespostaChecklist(
                visita_id=visita.id,
                checklist_item_id=item.id,
                status=status,
                comentario=comentario,
                foto_path=fotos_por_item.get(item.id),
            )
            db.session.add(resposta)
            if status == "NOK":
                db.session.add(
                    Ocorrencia(
                        visita_id=visita.id,
                        loja_id=loja_id,
                        checklist_item_id=item.id,
                        descricao=comentario,
                        status="aberta",
                        foto_path=fotos_por_item.get(item.id),
                    )
                )

        ocorrencias_ids = request.form.getlist("ocorrencia_id")
        for ocorrencia_id in ocorrencias_ids:
            ocorrencia = db.session.get(Ocorrencia, int(ocorrencia_id))
            if not ocorrencia or ocorrencia.loja_id != loja_id:
                continue
            novo_status = request.form.get(f"ocorrencia_status_{ocorrencia_id}", ocorrencia.status)
            if novo_status not in {"aberta", "em_andamento", "resolvida", "cancelada"}:
                continue
            ocorrencia.status = novo_status
            ocorrencia.data_fechamento = datetime.utcnow() if novo_status in {"resolvida", "cancelada"} else None

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Esta loja já possui visita hoje para este supervisor.", "error")
            return render_template("visitas/form.html", lojas=lojas, itens=itens, ocorrencias_ativas=ocorrencias_ativas, item_texto_livre=item_texto_livre, item_avaria_pergunta=item_avaria_pergunta, item_avaria_detalhe=item_avaria_detalhe)

        flash("Visita registrada com sucesso.", "success")
        return redirect(url_for("visitas.detalhe", visita_id=visita.id))

    return render_template("visitas/form.html", lojas=lojas, itens=itens, ocorrencias_ativas=ocorrencias_ativas, item_texto_livre=item_texto_livre, item_avaria_pergunta=item_avaria_pergunta, item_avaria_detalhe=item_avaria_detalhe)


@bp.route("/<int:visita_id>")
@login_required
def detalhe(visita_id):
    visita = db.get_or_404(Visita, visita_id)
    if not current_user.can_view_all_stores and visita.supervisor_id != current_user.id:
        abort(403)
    return render_template("visitas/detalhe.html", visita=visita)


@bp.route("/loja/<int:loja_id>/historico")
@login_required
def historico_loja(loja_id):
    loja = db.get_or_404(Loja, loja_id)
    if not current_user.can_view_all_stores and not supervisor_pode_loja(current_user.id, loja_id):
        abort(403)
    visitas = (
        Visita.query.filter_by(loja_id=loja_id)
        .order_by(Visita.data_visita.desc(), Visita.id.desc())
        .all()
    )
    return render_template("visitas/historico_loja.html", loja=loja, visitas=visitas)


@bp.route("/ocorrencias")
@login_required
def ocorrencias():
    if not current_user.can_access("ocorrencias"):
        abort(403)
    query = Ocorrencia.query.join(Loja)
    if not current_user.can_view_all_stores:
        lojas_ids = [item.loja_id for item in SupervisorLoja.query.filter_by(supervisor_id=current_user.id)]
        query = query.filter(Loja.id.in_(lojas_ids))
    ocorrencias_lista = query.order_by(Ocorrencia.status, Ocorrencia.data_abertura.desc()).all()
    return render_template("visitas/ocorrencias.html", ocorrencias=ocorrencias_lista)


@bp.route("/ocorrencias/<int:ocorrencia_id>/status", methods=["POST"])
@login_required
def atualizar_status_ocorrencia(ocorrencia_id):
    if not current_user.can_access("ocorrencias"):
        abort(403)
    ocorrencia = db.get_or_404(Ocorrencia, ocorrencia_id)
    if not current_user.can_view_all_stores and not supervisor_pode_loja(current_user.id, ocorrencia.loja_id):
        abort(403)
    status = request.form.get("status")
    if status not in STATUS_OCORRENCIA:
        abort(400)
    ocorrencia.status = status
    ocorrencia.data_fechamento = datetime.utcnow() if status in {"resolvida", "cancelada"} else None
    db.session.commit()
    flash("Status da ocorrência atualizado.", "success")
    return redirect(request.referrer or url_for("visitas.ocorrencias"))
