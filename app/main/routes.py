import csv
import os
from io import StringIO
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    BALANCO_ITENS_FIXOS,
    BalancoCorredor,
    BalancoMensal,
    CicloBalanco,
    CorredorLoja,
    Loja,
    Manutencao,
    Ocorrencia,
    SupervisorLoja,
    Usuario,
    Visita,
)


bp = Blueprint("main", __name__)
EXTENSOES_IMAGEM = {"png", "jpg", "jpeg", "webp"}


def lojas_da_visao():
    if current_user.is_admin:
        return Loja.query.filter_by(ativa=True).order_by(Loja.nome).all()
    return (
        Loja.query.join(SupervisorLoja)
        .filter(SupervisorLoja.supervisor_id == current_user.id, Loja.ativa.is_(True))
        .order_by(Loja.nome)
        .all()
    )


def lojas_do_relatorio(supervisor_id=None):
    if current_user.is_admin and supervisor_id:
        return (
            Loja.query.join(SupervisorLoja)
            .filter(SupervisorLoja.supervisor_id == supervisor_id, Loja.ativa.is_(True))
            .order_by(Loja.nome)
            .all()
        )
    return lojas_da_visao()


def intervalo_mes(valor):
    hoje = date.today()
    if valor:
        try:
            ano, mes = [int(parte) for parte in valor.split("-", 1)]
            inicio = date(ano, mes, 1)
        except ValueError:
            inicio = date(hoje.year, hoje.month, 1)
    else:
        inicio = date(hoje.year, hoje.month, 1)

    if inicio.month == 12:
        fim = date(inicio.year + 1, 1, 1)
    else:
        fim = date(inicio.year, inicio.month + 1, 1)

    return inicio, fim


def intervalo_relatorio(args):
    hoje = date.today()
    periodo = args.get("periodo", "mes")

    if periodo == "dia":
        data_valor = args.get("data_dia") or hoje.strftime("%Y-%m-%d")
        try:
            inicio = date.fromisoformat(data_valor)
        except ValueError:
            inicio = hoje
            data_valor = hoje.strftime("%Y-%m-%d")
        fim = date.fromordinal(inicio.toordinal() + 1)
        mes_referencia = date(inicio.year, inicio.month, 1)
        return {
            "periodo": "dia",
            "inicio": inicio,
            "fim": fim,
            "mes_referencia": mes_referencia,
            "mes_valor": mes_referencia.strftime("%Y-%m"),
            "data_dia_valor": data_valor,
            "data_inicio_valor": inicio.strftime("%Y-%m-%d"),
            "data_fim_valor": inicio.strftime("%Y-%m-%d"),
            "periodo_label": inicio.strftime("%d/%m/%Y"),
        }

    if periodo == "intervalo":
        data_inicio_valor = args.get("data_inicio") or hoje.strftime("%Y-%m-%d")
        data_fim_valor = args.get("data_fim") or data_inicio_valor
        try:
            inicio = date.fromisoformat(data_inicio_valor)
        except ValueError:
            inicio = hoje
            data_inicio_valor = hoje.strftime("%Y-%m-%d")
        try:
            fim_inclusivo = date.fromisoformat(data_fim_valor)
        except ValueError:
            fim_inclusivo = inicio
            data_fim_valor = inicio.strftime("%Y-%m-%d")
        if fim_inclusivo < inicio:
            fim_inclusivo = inicio
            data_fim_valor = inicio.strftime("%Y-%m-%d")

        mes_referencia = date(inicio.year, inicio.month, 1)
        return {
            "periodo": "intervalo",
            "inicio": inicio,
            "fim": fim_inclusivo + timedelta(days=1),
            "mes_referencia": mes_referencia,
            "mes_valor": mes_referencia.strftime("%Y-%m"),
            "data_dia_valor": inicio.strftime("%Y-%m-%d"),
            "data_inicio_valor": data_inicio_valor,
            "data_fim_valor": data_fim_valor,
            "periodo_label": f"{inicio.strftime('%d/%m/%Y')} a {fim_inclusivo.strftime('%d/%m/%Y')}",
        }

    inicio, fim = intervalo_mes(args.get("mes", ""))
    return {
        "periodo": "mes",
        "inicio": inicio,
        "fim": fim,
        "mes_referencia": inicio,
        "mes_valor": inicio.strftime("%Y-%m"),
        "data_dia_valor": hoje.strftime("%Y-%m-%d"),
        "data_inicio_valor": hoje.strftime("%Y-%m-%d"),
        "data_fim_valor": hoje.strftime("%Y-%m-%d"),
        "periodo_label": inicio.strftime("%m/%Y"),
    }


def mes_anterior(data_mes):
    if data_mes.month == 1:
        return date(data_mes.year - 1, 12, 1)
    return date(data_mes.year, data_mes.month - 1, 1)


def ciclo_do_relatorio(args):
    ciclos = CicloBalanco.query.order_by(CicloBalanco.competencia_mes.desc(), CicloBalanco.data_contagem.desc()).all()
    ciclo_id = args.get("ciclo_id", type=int)
    if ciclo_id:
        ciclo = db.session.get(CicloBalanco, ciclo_id)
        if ciclo:
            return ciclo, ciclos
    ciclo_aberto = next((ciclo for ciclo in ciclos if ciclo.status == "aberto"), None)
    if current_user.is_admin:
        return ciclo_aberto, ciclos
    return ciclo_aberto, ciclos


def parse_reais(valor):
    texto = (valor or "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError("Valor do balanço inválido.")


def balanco_lancado(balanco):
    if not balanco:
        return False
    return (
        (balanco.valor_total or Decimal("0.00")) > Decimal("0.00")
        or bool(balanco.observacao)
        or balanco.valor_revisado is not None
    )


def corredor_lancado(item):
    return item is not None


def recalcular_totais_balanco(balanco):
    valores = list(balanco.corredores)
    balanco.valor_total = sum((item.valor_fechado or Decimal("0.00") for item in valores), Decimal("0.00"))
    tem_revisao = any(item.valor_revisado is not None for item in valores)
    if tem_revisao:
        balanco.valor_revisado = sum((item.valor_considerado or Decimal("0.00") for item in valores), Decimal("0.00"))
    else:
        balanco.valor_revisado = None


def corredores_por_loja(lojas_ids):
    corredores = (
        CorredorLoja.query.filter(CorredorLoja.loja_id.in_(lojas_ids), CorredorLoja.ativo.is_(True))
        .order_by(CorredorLoja.loja_id, CorredorLoja.ordem, CorredorLoja.nome)
        .all()
    )
    por_loja = {loja_id: [] for loja_id in lojas_ids}
    for corredor in corredores:
        por_loja.setdefault(corredor.loja_id, []).append(corredor)
    return por_loja


def corredor_fixo_balanco(corredor):
    return corredor.nome in BALANCO_ITENS_FIXOS


def total_itens_fixos_balanco(corredores, valores_por_corredor):
    return sum(
        (
            valores_por_corredor[corredor.id].valor_considerado or Decimal("0.00")
            for corredor in corredores
            if corredor_fixo_balanco(corredor) and corredor.id in valores_por_corredor
        ),
        Decimal("0.00"),
    )


def get_loja_visivel(loja_id):
    if not loja_id:
        return None
    lojas_ids = {loja.id for loja in lojas_da_visao()}
    if loja_id not in lojas_ids:
        return None
    return db.session.get(Loja, loja_id)


def salvar_foto_manutencao(arquivo):
    if not arquivo or not arquivo.filename:
        return None

    nome_seguro = secure_filename(arquivo.filename)
    extensao = nome_seguro.rsplit(".", 1)[-1].lower() if "." in nome_seguro else ""
    if extensao not in EXTENSOES_IMAGEM:
        raise ValueError("A foto da manutenção deve ser PNG, JPG, JPEG ou WEBP.")

    pasta = os.path.join(current_app.config["UPLOAD_FOLDER"], "manutencoes")
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = f"{uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(pasta, nome_arquivo))
    return f"uploads/manutencoes/{nome_arquivo}"


@bp.route("/")
@login_required
def dashboard():
    hoje = date.today()

    lojas = lojas_da_visao()

    if current_user.is_admin:
        visitas_hoje = Visita.query.filter_by(data_visita=hoje).all()
        ocorrencias = (
            Ocorrencia.query.filter(Ocorrencia.status.in_(["aberta", "em_andamento"]))
            .join(Loja)
            .order_by(Ocorrencia.data_abertura.desc())
            .all()
        )
    else:
        visitas_hoje = Visita.query.filter_by(supervisor_id=current_user.id, data_visita=hoje).all()
        ocorrencias = (
            Ocorrencia.query.join(Loja)
            .filter(Ocorrencia.status.in_(["aberta", "em_andamento"]), Loja.id.in_([loja.id for loja in lojas]))
            .order_by(Ocorrencia.data_abertura.desc())
            .all()
        )

    visitadas_ids = {visita.loja_id for visita in visitas_hoje}
    pendentes = [loja for loja in lojas if loja.id not in visitadas_ids]

    return render_template(
        "main/dashboard.html",
        hoje=hoje,
        lojas=lojas,
        visitas_hoje=visitas_hoje,
        pendentes=pendentes,
        ocorrencias=ocorrencias,
    )


@bp.route("/manual")
@login_required
def manual():
    return render_template("main/manual.html")


@bp.route("/financeiro")
@login_required
def financeiro():
    return render_template("main/financeiro.html")


@bp.route("/manutencoes")
@login_required
def manutencoes():
    lojas = lojas_da_visao()
    lojas_ids = [loja.id for loja in lojas]
    loja_id = None if current_user.is_admin else request.args.get("loja_id", type=int)
    if loja_id not in lojas_ids:
        loja_id = None
    loja_selecionada = db.session.get(Loja, loja_id) if loja_id else None
    historico_loja_raw = request.args.get("historico_loja_id", "")
    historico_todas = historico_loja_raw == "todas"
    try:
        historico_loja_id = int(historico_loja_raw) if historico_loja_raw and not historico_todas else None
    except ValueError:
        historico_loja_id = None
    if historico_loja_id not in lojas_ids:
        historico_loja_id = None
    categoria = request.args.get("categoria", "")
    status = request.args.get("status", "")
    historico_filtrado = (
        "historico_loja_id" in request.args
        or "categoria" in request.args
        or "status" in request.args
    )

    registros = []
    if historico_filtrado and (historico_todas or historico_loja_id):
        query = Manutencao.query.filter(Manutencao.loja_id.in_(lojas_ids))
        if historico_loja_id:
            query = query.filter(Manutencao.loja_id == historico_loja_id)
        if categoria:
            query = query.filter(Manutencao.categoria == categoria)
        if status:
            query = query.filter(Manutencao.status == status)
        registros = query.order_by(Manutencao.data_solicitacao.desc(), Manutencao.id.desc()).all()
    total_custo = sum((registro.custo or Decimal("0.00") for registro in registros), Decimal("0.00"))

    abertas_query = Manutencao.query.filter(
        Manutencao.loja_id.in_(lojas_ids),
        Manutencao.status.in_(["pendente", "em_andamento"]),
    )
    abertas = abertas_query.count()
    refrigeracao_abertas = abertas_query.filter(Manutencao.categoria == "refrigeracao").count()
    padrao_abertas = abertas_query.filter(Manutencao.categoria == "padrao").count()
    manutencoes_alerta = (
        Manutencao.query.filter(
            Manutencao.loja_id.in_(lojas_ids),
            Manutencao.status.in_(["pendente", "em_andamento"]),
            Manutencao.data_solicitacao < date.today(),
        )
        .order_by(Manutencao.data_solicitacao.asc(), Manutencao.id.asc())
        .all()
    )
    manutencoes_alerta_por_loja = {}
    for manutencao in manutencoes_alerta:
        manutencoes_alerta_por_loja.setdefault(manutencao.loja_id, []).append(manutencao)

    return render_template(
        "main/manutencoes.html",
        hoje=date.today(),
        lojas=lojas,
        loja_id=loja_id,
        loja_selecionada=loja_selecionada,
        historico_loja_id=historico_loja_id,
        historico_todas=historico_todas,
        historico_filtrado=historico_filtrado,
        categoria=categoria,
        status=status,
        registros=registros,
        abertas=abertas,
        refrigeracao_abertas=refrigeracao_abertas,
        padrao_abertas=padrao_abertas,
        total_custo=total_custo,
        manutencoes_alerta_por_loja=manutencoes_alerta_por_loja,
    )


@bp.route("/manutencoes", methods=["POST"])
@login_required
def criar_manutencao():
    if current_user.is_admin:
        abort(403)

    loja_id = request.form.get("loja_id", type=int)
    loja = get_loja_visivel(loja_id)
    if not loja:
        flash("Selecione uma loja válida.", "error")
        return redirect(url_for("main.manutencoes"))

    categoria = request.form.get("categoria", "").strip()
    area_equipamento = request.form.get("area_equipamento", "").strip()
    problema = request.form.get("problema", "").strip()
    tipo = request.form.get("tipo", "").strip()
    responsavel = request.form.get("responsavel", "").strip()
    status = request.form.get("status", "").strip()
    custo_raw = request.form.get("custo", "").strip()
    observacao = request.form.get("observacao", "").strip()
    data_solicitacao_raw = request.form.get("data_solicitacao", "")
    data_atendimento_raw = request.form.get("data_atendimento", "")
    foto = (
        request.files.get("foto_camera")
        or request.files.get("foto_galeria")
        or request.files.get("foto")
    )

    if categoria not in {"refrigeracao", "padrao"}:
        flash("Informe a categoria da manutenção.", "error")
        return redirect(url_for("main.manutencoes", loja_id=loja.id))
    if tipo not in {"preventiva", "corretiva"}:
        flash("Informe se a manutenção é preventiva ou corretiva.", "error")
        return redirect(url_for("main.manutencoes", loja_id=loja.id))
    if status not in {"pendente", "em_andamento", "concluido"}:
        flash("Informe o status da manutenção.", "error")
        return redirect(url_for("main.manutencoes", loja_id=loja.id))
    if not area_equipamento or not problema:
        flash("Informe a área/equipamento e o problema identificado.", "error")
        return redirect(url_for("main.manutencoes", loja_id=loja.id))

    try:
        data_solicitacao = date.fromisoformat(data_solicitacao_raw) if data_solicitacao_raw else date.today()
        data_atendimento = date.fromisoformat(data_atendimento_raw) if data_atendimento_raw else None
        custo = parse_reais(custo_raw) if custo_raw else Decimal("0.00")
        foto_path = salvar_foto_manutencao(foto)
    except ValueError as exc:
        flash(str(exc) if str(exc) else "Informe as datas e o custo corretamente.", "error")
        return redirect(url_for("main.manutencoes", loja_id=loja.id))

    db.session.add(
        Manutencao(
            loja_id=loja.id,
            usuario_id=current_user.id,
            categoria=categoria,
            area_equipamento=area_equipamento,
            problema=problema,
            tipo=tipo,
            responsavel=responsavel,
            custo=custo,
            data_solicitacao=data_solicitacao,
            data_atendimento=data_atendimento or (date.today() if status == "concluido" else None),
            status=status,
            foto_path=foto_path,
            observacao=observacao,
        )
    )
    db.session.commit()
    flash("Manutenção registrada.", "success")
    return redirect(url_for("main.manutencoes"))


@bp.route("/manutencoes/<int:manutencao_id>/status", methods=["POST"])
@login_required
def atualizar_status_manutencao(manutencao_id):
    manutencao = db.session.get(Manutencao, manutencao_id)
    if not manutencao or not get_loja_visivel(manutencao.loja_id):
        abort(404)

    status = request.form.get("status", "")
    if status not in {"pendente", "em_andamento", "concluido", "cancelado"}:
        flash("Status inválido.", "error")
        return redirect(url_for("main.manutencoes", historico_loja_id=manutencao.loja_id, _anchor="historico"))

    data_atendimento_raw = request.form.get("data_atendimento", "")
    custo_raw = request.form.get("custo", "").strip()
    observacao = request.form.get("observacao", "").strip()
    try:
        data_atendimento = date.fromisoformat(data_atendimento_raw) if data_atendimento_raw else None
        custo = parse_reais(custo_raw) if custo_raw else None
    except ValueError:
        flash("Informe a data de atendimento e o custo corretamente.", "error")
        return redirect(url_for("main.manutencoes", historico_loja_id=manutencao.loja_id, _anchor="historico"))

    manutencao.status = status
    if data_atendimento:
        manutencao.data_atendimento = data_atendimento
    elif status == "concluido" and not manutencao.data_atendimento:
        manutencao.data_atendimento = date.today()
    if custo is not None:
        manutencao.custo = custo
    if observacao:
        manutencao.observacao = observacao
    db.session.commit()
    flash("Status da manutenção atualizado.", "success")
    if request.form.get("origem") == "alerta":
        return redirect(url_for("main.manutencoes", loja_id=manutencao.loja_id))
    return redirect(url_for("main.manutencoes", historico_loja_id=manutencao.loja_id, _anchor="historico"))


@bp.route("/relatorios")
@login_required
def relatorios():
    filtros = intervalo_relatorio(request.args)
    ciclo, ciclos_balanco = ciclo_do_relatorio(request.args)
    inicio = filtros["inicio"]
    fim = filtros["fim"]
    mes_referencia = ciclo.competencia_mes if ciclo else filtros["mes_referencia"]
    supervisor_id = request.args.get("supervisor_id", type=int) if current_user.is_admin else current_user.id
    lojas = lojas_do_relatorio(supervisor_id)
    lojas_ids = [loja.id for loja in lojas]
    supervisores = Usuario.query.filter_by(perfil="supervisor", ativo=True).order_by(Usuario.nome).all()

    visitas_query = Visita.query.filter(Visita.data_visita >= inicio, Visita.data_visita < fim)
    if supervisor_id:
        visitas_query = visitas_query.filter(Visita.supervisor_id == supervisor_id)
    visitas = visitas_query.filter(Visita.loja_id.in_(lojas_ids)).all()

    visitas_por_loja = {loja.id: [] for loja in lojas}
    for visita in visitas:
        visitas_por_loja.setdefault(visita.loja_id, []).append(visita)

    mes_passado = mes_anterior(mes_referencia)
    balancos_query = BalancoMensal.query.filter(BalancoMensal.loja_id.in_(lojas_ids))
    if ciclo:
        balancos_query = balancos_query.filter(BalancoMensal.ciclo_balanco_id == ciclo.id)
    else:
        balancos_query = balancos_query.filter(BalancoMensal.mes_referencia == mes_referencia)
    balancos = balancos_query.all()
    balancos_anteriores = BalancoMensal.query.filter(
        BalancoMensal.loja_id.in_(lojas_ids),
        BalancoMensal.mes_referencia == mes_passado,
    ).all()
    balancos_por_loja = {balanco.loja_id: balanco for balanco in balancos}
    anteriores_por_loja = {balanco.loja_id: balanco for balanco in balancos_anteriores}

    resumo_lojas = []
    for loja in lojas:
        visitas_loja = visitas_por_loja.get(loja.id, [])
        total_venda = sum((visita.venda_dia or Decimal("0.00")) for visita in visitas_loja)
        ocorrencias = [ocorrencia for visita in visitas_loja for ocorrencia in visita.ocorrencias]
        abertas = [ocorrencia for ocorrencia in ocorrencias if ocorrencia.status == "aberta"]
        resolvidas = [ocorrencia for ocorrencia in ocorrencias if ocorrencia.status == "resolvida"]
        media_venda = total_venda / len(visitas_loja) if visitas_loja else Decimal("0.00")
        balanco = balancos_por_loja.get(loja.id)
        balanco_anterior = anteriores_por_loja.get(loja.id)
        lancado = balanco_lancado(balanco)
        valor_fechado = balanco.valor_total if balanco else Decimal("0.00")
        valor_revisado = balanco.valor_revisado if balanco and balanco.valor_revisado is not None else None
        diferenca_revisao = valor_revisado - valor_fechado if valor_revisado is not None else None
        valor_balanco = balanco.valor_considerado if balanco else Decimal("0.00")
        valor_anterior = balanco_anterior.valor_considerado if balanco_anterior else Decimal("0.00")
        diferenca = valor_balanco - valor_anterior
        percentual = (diferenca / valor_anterior * 100) if valor_anterior else None
        resumo_lojas.append(
            {
                "loja": loja,
                "visitas": len(visitas_loja),
                "total_venda": total_venda,
                "media_venda": media_venda,
                "balanco": balanco,
                "balanco_lancado": lancado,
                "valor_fechado": valor_fechado,
                "valor_revisado": valor_revisado,
                "diferenca_revisao": diferenca_revisao,
                "valor_balanco": valor_balanco,
                "valor_anterior": valor_anterior,
                "diferenca": diferenca,
                "percentual": percentual,
                "ocorrencias": len(ocorrencias),
                "abertas": len(abertas),
                "resolvidas": len(resolvidas),
            }
        )

    ranking_vendas = sorted(resumo_lojas, key=lambda item: item["total_venda"], reverse=True)
    ranking_problemas = sorted(resumo_lojas, key=lambda item: item["ocorrencias"], reverse=True)
    visitas_detalhadas = []
    for visita in sorted(visitas, key=lambda item: (item.data_visita, item.supervisor.nome, item.loja.nome), reverse=True):
        respostas = list(visita.respostas)
        ocorrencias = list(visita.ocorrencias)
        visitas_detalhadas.append(
            {
                "visita": visita,
                "ok": sum(1 for resposta in respostas if resposta.status == "OK"),
                "nok": sum(1 for resposta in respostas if resposta.status == "NOK"),
                "info": sum(1 for resposta in respostas if resposta.status == "INFO"),
                "ocorrencias": len(ocorrencias),
                "abertas": sum(1 for ocorrencia in ocorrencias if ocorrencia.status == "aberta"),
            }
        )
    total_vendas_visitas = sum((item["total_venda"] for item in resumo_lojas), Decimal("0.00"))
    total_balanco = sum((item["valor_balanco"] for item in resumo_lojas), Decimal("0.00"))
    total_ocorrencias = sum(item["ocorrencias"] for item in resumo_lojas)
    total_visitas = sum(item["visitas"] for item in resumo_lojas)

    return render_template(
        "main/relatorios.html",
        inicio=inicio,
        periodo=filtros["periodo"],
        periodo_label=filtros["periodo_label"],
        mes_valor=mes_referencia.strftime("%Y-%m"),
        data_dia_valor=filtros["data_dia_valor"],
        data_inicio_valor=filtros["data_inicio_valor"],
        data_fim_valor=filtros["data_fim_valor"],
        ciclo_balanco=ciclo,
        ciclos_balanco=ciclos_balanco,
        supervisor_id=supervisor_id,
        supervisores=supervisores,
        resumo_lojas=resumo_lojas,
        ranking_vendas=ranking_vendas,
        ranking_problemas=ranking_problemas,
        visitas_detalhadas=visitas_detalhadas,
        total_vendas_visitas=total_vendas_visitas,
        total_balanco=total_balanco,
        total_ocorrencias=total_ocorrencias,
        total_visitas=total_visitas,
    )


@bp.route("/balancos")
@login_required
def balancos():
    filtros = intervalo_relatorio(request.args)
    ciclo, ciclos_balanco = ciclo_do_relatorio(request.args)
    mes_referencia = ciclo.competencia_mes if ciclo else filtros["mes_referencia"]
    supervisor_id = request.args.get("supervisor_id", type=int) if current_user.is_admin else current_user.id
    lojas = lojas_do_relatorio(supervisor_id)
    lojas_ids = [loja.id for loja in lojas]
    balanco_loja_id = request.args.get("balanco_loja_id", type=int)
    if balanco_loja_id not in lojas_ids:
        balanco_loja_id = None
    supervisores = Usuario.query.filter_by(perfil="supervisor", ativo=True).order_by(Usuario.nome).all()

    mes_passado = mes_anterior(mes_referencia)
    balancos_query = BalancoMensal.query.filter(BalancoMensal.loja_id.in_(lojas_ids))
    if ciclo:
        balancos_query = balancos_query.filter(BalancoMensal.ciclo_balanco_id == ciclo.id)
    else:
        balancos_query = balancos_query.filter(BalancoMensal.mes_referencia == mes_referencia)
    balancos = balancos_query.all()
    balancos_anteriores = BalancoMensal.query.filter(
        BalancoMensal.loja_id.in_(lojas_ids),
        BalancoMensal.mes_referencia == mes_passado,
    ).all()
    balancos_por_loja = {balanco.loja_id: balanco for balanco in balancos}
    anteriores_por_loja = {balanco.loja_id: balanco for balanco in balancos_anteriores}
    corredores_loja = corredores_por_loja(lojas_ids)

    resumo_lojas = []
    for loja in lojas:
        balanco = balancos_por_loja.get(loja.id)
        balanco_anterior = anteriores_por_loja.get(loja.id)
        lancado = balanco_lancado(balanco)
        valor_fechado = balanco.valor_total if balanco else Decimal("0.00")
        valor_revisado = balanco.valor_revisado if balanco and balanco.valor_revisado is not None else None
        diferenca_revisao = valor_revisado - valor_fechado if valor_revisado is not None else None
        valor_balanco = balanco.valor_considerado if balanco else Decimal("0.00")
        valor_anterior = balanco_anterior.valor_considerado if balanco_anterior else Decimal("0.00")
        corredores = corredores_loja.get(loja.id, [])
        corredores_fixos = [corredor for corredor in corredores if corredor_fixo_balanco(corredor)]
        corredores_variaveis = [corredor for corredor in corredores if not corredor_fixo_balanco(corredor)]
        valores_por_corredor = {
            item.corredor_id: item
            for item in balanco.corredores
            if corredor_lancado(item)
        } if balanco else {}
        total_itens_fixos = total_itens_fixos_balanco(corredores, valores_por_corredor)
        corredores_lancados = sum(1 for corredor in corredores if corredor.id in valores_por_corredor)
        total_corredores = len(corredores)
        resumo_lojas.append(
            {
                "loja": loja,
                "corredores": corredores,
                "corredores_fixos": corredores_fixos,
                "corredores_variaveis": corredores_variaveis,
                "valores_por_corredor": valores_por_corredor,
                "corredores_lancados": corredores_lancados,
                "total_corredores": total_corredores,
                "total_itens_fixos": total_itens_fixos,
                "lancamento_completo": total_corredores > 0 and corredores_lancados == total_corredores,
                "tem_corredor_pendente": total_corredores > corredores_lancados,
                "balanco": balanco,
                "balanco_lancado": lancado,
                "valor_fechado": valor_fechado,
                "valor_revisado": valor_revisado,
                "diferenca_revisao": diferenca_revisao,
                "valor_balanco": valor_balanco,
                "valor_anterior": valor_anterior,
            }
        )

    return render_template(
        "main/balancos.html",
        mes_valor=mes_referencia.strftime("%Y-%m"),
        data_dia_valor=filtros["data_dia_valor"],
        ciclo_balanco=ciclo,
        ciclos_balanco=ciclos_balanco,
        supervisor_id=supervisor_id,
        balanco_loja_id=balanco_loja_id,
        supervisores=supervisores,
        lojas=lojas,
        resumo_lojas=resumo_lojas,
        resumo_lancamento=[item for item in resumo_lojas if item["loja"].id == balanco_loja_id] if balanco_loja_id else [],
        pode_salvar_lancamento=(
            current_user.is_admin
            or any(
                item["loja"].id == balanco_loja_id and item["tem_corredor_pendente"]
                for item in resumo_lojas
            )
        ),
        total_balanco=sum((item["valor_balanco"] for item in resumo_lojas), Decimal("0.00")),
        total_lancados=sum(1 for item in resumo_lojas if item["balanco_lancado"]),
    )


@bp.route("/balancos/corredores", methods=["POST"])
@login_required
def criar_corredor_balanco():
    if not current_user.is_admin:
        abort(403)

    loja_id = request.form.get("loja_id", type=int)
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    ordem = request.form.get("ordem", type=int) or 0
    loja = db.session.get(Loja, loja_id) if loja_id else None
    if not loja or not nome:
        flash("Informe a loja e o nome do corredor.", "error")
        return redirect(url_for("admin.lojas", corredor_loja_id=loja_id))

    existente = CorredorLoja.query.filter_by(loja_id=loja.id, nome=nome).first()
    if existente:
        existente.descricao = descricao
        existente.ordem = ordem
        existente.ativo = True
    else:
        db.session.add(CorredorLoja(loja_id=loja.id, nome=nome, descricao=descricao, ordem=ordem, ativo=True))
    db.session.commit()
    flash("Corredor salvo.", "success")
    return redirect(url_for("admin.lojas", corredor_loja_id=loja.id))


@bp.route("/balancos/corredores/<int:corredor_id>", methods=["POST"])
@login_required
def atualizar_corredor_balanco(corredor_id):
    if not current_user.is_admin:
        abort(403)

    corredor = db.session.get(CorredorLoja, corredor_id)
    if not corredor:
        abort(404)
    if corredor_fixo_balanco(corredor):
        corredor.descricao = "Item fixo do balanço"
        corredor.ativo = True
        corredor.ordem = request.form.get("ordem", type=int) or corredor.ordem
        db.session.commit()
        flash("Item fixo atualizado. O nome não pode ser alterado.", "success")
        return redirect(url_for("admin.lojas", corredor_loja_id=corredor.loja_id))
    corredor.nome = request.form.get("nome", "").strip() or corredor.nome
    corredor.descricao = request.form.get("descricao", "").strip()
    corredor.ordem = request.form.get("ordem", type=int) or 0
    corredor.ativo = bool(request.form.get("ativo"))
    db.session.commit()
    flash("Corredor atualizado.", "success")
    return redirect(url_for("admin.lojas", corredor_loja_id=corredor.loja_id))


@bp.route("/balancos/corredores/<int:corredor_id>/excluir", methods=["POST"])
@login_required
def excluir_corredor_balanco(corredor_id):
    if not current_user.is_admin:
        abort(403)

    corredor = db.session.get(CorredorLoja, corredor_id)
    if not corredor:
        abort(404)

    loja_id = corredor.loja_id
    if corredor_fixo_balanco(corredor):
        corredor.ativo = True
        db.session.commit()
        flash("Este item é fixo do balanço e não pode ser excluído.", "error")
        return redirect(url_for("admin.lojas", corredor_loja_id=loja_id))

    if corredor.valores:
        corredor.ativo = False
        flash("Este corredor já tem lançamento. Ele foi inativado para manter o histórico.", "success")
    else:
        db.session.delete(corredor)
        flash("Corredor excluído.", "success")
    db.session.commit()
    return redirect(url_for("admin.lojas", corredor_loja_id=loja_id))


@bp.route("/balancos/salvar", methods=["POST"])
@login_required
def salvar_balancos():
    ciclo_id = request.form.get("ciclo_id", type=int)
    ciclo = db.session.get(CicloBalanco, ciclo_id) if ciclo_id else None
    if not ciclo:
        flash("Nenhum balanço liberado foi selecionado.", "error")
        return redirect(url_for("main.balancos"))
    if not current_user.is_admin and ciclo.status != "aberto":
        flash("Este balanço não está aberto para lançamento.", "error")
        return redirect(url_for("main.balancos", ciclo_id=ciclo.id))

    inicio = ciclo.competencia_mes
    lojas_ids = {loja.id for loja in lojas_da_visao()}

    for loja_id in lojas_ids:
        corredores = (
            CorredorLoja.query.filter_by(loja_id=loja_id, ativo=True)
            .order_by(CorredorLoja.ordem, CorredorLoja.nome)
            .all()
        )
        if not corredores:
            continue

        balanco = BalancoMensal.query.filter_by(loja_id=loja_id, ciclo_balanco_id=ciclo.id).first()
        if not balanco:
            balanco = BalancoMensal.query.filter_by(
                loja_id=loja_id,
                mes_referencia=inicio,
                ciclo_balanco_id=None,
            ).first()

        if current_user.is_admin:
            if not balanco:
                continue
            if balanco.ciclo_balanco_id is None:
                balanco.ciclo_balanco_id = ciclo.id
            valores_por_corredor = {item.corredor_id: item for item in balanco.corredores}
            mudou_revisao = False
            for corredor in corredores:
                revisao_raw = request.form.get(f"revisao_{loja_id}_{corredor.id}", "").strip()
                observacao_revisao = request.form.get(f"observacao_revisao_{loja_id}_{corredor.id}", "").strip()
                item = valores_por_corredor.get(corredor.id)
                if not item:
                    continue
                if revisao_raw:
                    try:
                        item.valor_revisado = parse_reais(revisao_raw)
                    except ValueError as exc:
                        flash(str(exc), "error")
                        return redirect(url_for("main.balancos", ciclo_id=ciclo.id))
                    item.observacao_revisao = observacao_revisao
                    mudou_revisao = True
                elif observacao_revisao and item.valor_revisado is not None:
                    item.observacao_revisao = observacao_revisao
                    mudou_revisao = True
            if mudou_revisao:
                balanco.data_revisao = datetime.utcnow()
                balanco.revisado_por_id = current_user.id
                recalcular_totais_balanco(balanco)
        else:
            valores = []
            valores_por_corredor = {item.corredor_id: item for item in balanco.corredores} if balanco else {}
            for corredor in corredores:
                item_existente = valores_por_corredor.get(corredor.id)
                if corredor_lancado(item_existente):
                    continue
                valor_raw = request.form.get(f"corredor_{loja_id}_{corredor.id}", "").strip()
                observacao = request.form.get(f"observacao_corredor_{loja_id}_{corredor.id}", "").strip()
                if not valor_raw:
                    continue
                try:
                    valor = parse_reais(valor_raw)
                except ValueError as exc:
                    flash(str(exc), "error")
                    return redirect(url_for("main.balancos", ciclo_id=ciclo.id))
                if valor < Decimal("0.00"):
                    flash("O valor do balanço não pode ser negativo.", "error")
                    return redirect(url_for("main.balancos", ciclo_id=ciclo.id))
                valores.append((corredor, valor, observacao, item_existente))

            if not valores:
                continue

            if not balanco:
                balanco = BalancoMensal(loja_id=loja_id, ciclo_balanco_id=ciclo.id, mes_referencia=inicio)
                db.session.add(balanco)
            balanco.ciclo_balanco_id = ciclo.id
            balanco.mes_referencia = inicio
            balanco.observacao = "Lançado por corredores"
            balanco.data_lancamento = datetime.utcnow()
            for corredor, valor, observacao, item in valores:
                if not item:
                    item = BalancoCorredor(balanco=balanco, corredor_id=corredor.id)
                    db.session.add(item)
                item.valor_fechado = valor
                item.observacao = observacao
            recalcular_totais_balanco(balanco)

    db.session.commit()
    flash("Balanço mensal salvo.", "success")
    return redirect(url_for("main.balancos", ciclo_id=ciclo.id))

@bp.route("/balancos/ciclos", methods=["POST"])
@login_required
def criar_ciclo_balanco():
    if not current_user.is_admin:
        abort(403)

    competencia_raw = request.form.get("competencia_mes", "")
    data_contagem_raw = request.form.get("data_contagem", "")
    observacao = request.form.get("observacao", "").strip()
    try:
        competencia, _ = intervalo_mes(competencia_raw)
        data_contagem = date.fromisoformat(data_contagem_raw)
    except ValueError:
        flash("Informe a competência e a data da contagem corretamente.", "error")
        return redirect(url_for("main.balancos"))

    ciclo = CicloBalanco(
        competencia_mes=competencia,
        data_contagem=data_contagem,
        status="aberto",
        observacao=observacao,
    )
    db.session.add(ciclo)
    db.session.commit()
    flash("Balanço liberado para lançamento.", "success")
    return redirect(url_for("main.balancos", ciclo_id=ciclo.id))


@bp.route("/balancos/ciclos/<int:ciclo_id>/status", methods=["POST"])
@login_required
def atualizar_status_ciclo_balanco(ciclo_id):
    if not current_user.is_admin:
        abort(403)

    ciclo = db.session.get(CicloBalanco, ciclo_id)
    if not ciclo:
        abort(404)

    status = request.form.get("status")
    if status not in {"aberto", "fechado", "cancelado"}:
        flash("Status de balanço inválido.", "error")
        return redirect(url_for("main.balancos", ciclo_id=ciclo.id))

    ciclo.status = status
    db.session.commit()
    flash("Status do balanço atualizado.", "success")
    if status == "aberto":
        return redirect(url_for("main.balancos", ciclo_id=ciclo.id))
    return redirect(url_for("main.balancos"))


@bp.route("/relatorios/exportar")
@login_required
def exportar_relatorio():
    filtros = intervalo_relatorio(request.args)
    ciclo, _ = ciclo_do_relatorio(request.args)
    inicio = filtros["inicio"]
    fim = filtros["fim"]
    mes_referencia = ciclo.competencia_mes if ciclo else filtros["mes_referencia"]
    supervisor_id = request.args.get("supervisor_id", type=int) if current_user.is_admin else current_user.id
    lojas = lojas_do_relatorio(supervisor_id)
    lojas_ids = [loja.id for loja in lojas]

    visitas_query = Visita.query.filter(Visita.data_visita >= inicio, Visita.data_visita < fim)
    if supervisor_id:
        visitas_query = visitas_query.filter(Visita.supervisor_id == supervisor_id)
    visitas = visitas_query.filter(Visita.loja_id.in_(lojas_ids)).all()

    visitas_por_loja = {loja.id: [] for loja in lojas}
    for visita in visitas:
        visitas_por_loja.setdefault(visita.loja_id, []).append(visita)

    mes_passado = mes_anterior(mes_referencia)
    balancos_query = BalancoMensal.query.filter(BalancoMensal.loja_id.in_(lojas_ids))
    if ciclo:
        balancos_query = balancos_query.filter(BalancoMensal.ciclo_balanco_id == ciclo.id)
    else:
        balancos_query = balancos_query.filter(BalancoMensal.mes_referencia == mes_referencia)
    balancos = balancos_query.all()
    balancos_anteriores = BalancoMensal.query.filter(
        BalancoMensal.loja_id.in_(lojas_ids),
        BalancoMensal.mes_referencia == mes_passado,
    ).all()
    balancos_por_loja = {balanco.loja_id: balanco for balanco in balancos}
    anteriores_por_loja = {balanco.loja_id: balanco for balanco in balancos_anteriores}

    arquivo = StringIO()
    writer = csv.writer(arquivo, delimiter=";")
    writer.writerow(
        [
            "Loja",
            "Visitas",
            "Vendas nas visitas",
            "Media por visita",
            "Valor fechado original",
            "Valor revisado",
            "Diferenca da revisao",
            "Valor considerado",
            "Mes anterior",
            "Diferenca",
            "Variacao %",
            "Problemas",
            "Abertas",
            "Em andamento",
            "Resolvidas",
            "Canceladas",
        ]
    )

    for loja in lojas:
        visitas_loja = visitas_por_loja.get(loja.id, [])
        total_venda = sum((visita.venda_dia or Decimal("0.00")) for visita in visitas_loja)
        media_venda = total_venda / len(visitas_loja) if visitas_loja else Decimal("0.00")
        ocorrencias = [ocorrencia for visita in visitas_loja for ocorrencia in visita.ocorrencias]
        balanco = balancos_por_loja.get(loja.id)
        balanco_anterior = anteriores_por_loja.get(loja.id)
        valor_fechado = balanco.valor_total if balanco else Decimal("0.00")
        valor_revisado = balanco.valor_revisado if balanco and balanco.valor_revisado is not None else None
        diferenca_revisao = valor_revisado - valor_fechado if valor_revisado is not None else None
        valor_balanco = balanco.valor_considerado if balanco else Decimal("0.00")
        valor_anterior = balanco_anterior.valor_considerado if balanco_anterior else Decimal("0.00")
        diferenca = valor_balanco - valor_anterior
        percentual = (diferenca / valor_anterior * 100) if valor_anterior else None

        writer.writerow(
            [
                loja.nome,
                len(visitas_loja),
                f"{total_venda:.2f}",
                f"{media_venda:.2f}",
                f"{valor_fechado:.2f}",
                f"{valor_revisado:.2f}" if valor_revisado is not None else "",
                f"{diferenca_revisao:.2f}" if diferenca_revisao is not None else "",
                f"{valor_balanco:.2f}",
                f"{valor_anterior:.2f}",
                f"{diferenca:.2f}",
                f"{percentual:.2f}" if percentual is not None else "",
                len(ocorrencias),
                sum(1 for ocorrencia in ocorrencias if ocorrencia.status == "aberta"),
                sum(1 for ocorrencia in ocorrencias if ocorrencia.status == "em_andamento"),
                sum(1 for ocorrencia in ocorrencias if ocorrencia.status == "resolvida"),
                sum(1 for ocorrencia in ocorrencias if ocorrencia.status == "cancelada"),
            ]
        )

    conteudo = "\ufeff" + arquivo.getvalue()
    fim_nome = (fim - timedelta(days=1)).isoformat()
    nome = f"relatorio-{filtros['periodo']}-{inicio.isoformat()}-{fim_nome}.csv"
    return Response(
        conteudo,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )
