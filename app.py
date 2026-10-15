"""Gerenciador de Tarefas — estrutura inicial com Flask e Flask-SQLAlchemy."""

import io
import os
from datetime import datetime

from flask import Flask, flash, make_response, redirect, render_template, request, url_for
from models import db, Contato, Tarefa
from weasyprint import HTML

app = Flask(__name__)

# Banco de dados SQLite local (criado em instance/app.db)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Necessária para sessões (mensagens flash). Em produção, defina via ambiente.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

db.init_app(app)


# Cria as tabelas automaticamente na inicialização do app
with app.app_context():
    db.create_all()


# ---------- Filtros de template ----------

@app.template_filter("br_date")
def br_date(value):
    """Formata uma data como dd/mm/aaaa."""
    return value.strftime("%d/%m/%Y") if value else "—"


# ---------- Funções auxiliares ----------

def contato_existe(contato_id):
    """True se contato_id for nulo ou pertencer a um Contato cadastrado."""
    return contato_id is None or db.session.get(Contato, contato_id) is not None


# ---------- Rotas ----------

@app.route("/")
def home():
    return redirect(url_for("tarefas"))


@app.route("/tarefas")
def tarefas():
    Tarefa.verificar_atrasadas()  # checagem automática de prazos

    # Filtro opcional por responsável (?contato=<id>)
    contato_filtro = None
    query = Tarefa.query
    contato_id = request.args.get("contato", type=int)
    if contato_id is not None:
        contato_filtro = db.get_or_404(Contato, contato_id)
        query = query.filter(Tarefa.contato_id == contato_filtro.id)

    lista = query.order_by(Tarefa.id.desc()).all()
    return render_template(
        "tarefas.html",
        tarefas=lista,
        contatos=Contato.query.order_by(Contato.nome).all(),
        contato_filtro=contato_filtro,
    )


@app.route("/tarefas/cadastrar", methods=["GET", "POST"])
def nova_tarefa():
    if request.method == "GET":
        return render_template("tarefa_form.html",
                               contatos=Contato.query.order_by(Contato.nome).all())

    descricao = request.form.get("descricao", "").strip()
    if not descricao:
        return redirect(url_for("tarefas"))

    prazo = None
    prazo_raw = request.form.get("prazo", "").strip()
    if prazo_raw:
        try:
            prazo = datetime.strptime(prazo_raw, "%Y-%m-%d").date()
        except ValueError:
            prazo = None  # ignora prazo em formato inválido

    prioridade = request.form.get("prioridade", "media")
    if prioridade not in {"baixa", "media", "alta"}:
        prioridade = "media"

    status = request.form.get("status", Tarefa.STATUS_PENDENTE)
    if status not in {Tarefa.STATUS_PENDENTE, Tarefa.STATUS_FAZENDO, Tarefa.STATUS_CONCLUIDA}:
        status = Tarefa.STATUS_PENDENTE

    contato_id = request.form.get("contato_id", type=int)
    if not contato_existe(contato_id):
        flash("Contato inválido. Escolha um responsável cadastrado.", "danger")
        return redirect(url_for("nova_tarefa"))

    nova = Tarefa(
        descricao=descricao,
        prazo=prazo,
        prioridade=prioridade,
        status=status,
        contato_id=contato_id,
    )
    db.session.add(nova)
    db.session.commit()
    return redirect(url_for("tarefas"))


@app.route("/tarefas/<int:id>/editar", methods=["GET", "POST"])
def editar_tarefa(id):
    tarefa = db.get_or_404(Tarefa, id)
    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()
        if descricao:
            tarefa.descricao = descricao

        prazo_raw = request.form.get("prazo", "").strip()
        try:
            tarefa.prazo = datetime.strptime(prazo_raw, "%Y-%m-%d").date() if prazo_raw else None
        except ValueError:
            pass  # mantém o prazo anterior se o formato for inválido

        prioridade = request.form.get("prioridade", tarefa.prioridade)
        if prioridade in {"baixa", "media", "alta"}:
            tarefa.prioridade = prioridade

        status = request.form.get("status", tarefa.status)
        if status not in {Tarefa.STATUS_PENDENTE, Tarefa.STATUS_FAZENDO, Tarefa.STATUS_CONCLUIDA}:
            status = tarefa.status
        tarefa.status = status

        contato_id = request.form.get("contato_id", type=int)
        if not contato_existe(contato_id):
            flash("Contato inválido. Escolha um responsável cadastrado.", "danger")
            return redirect(url_for("editar_tarefa", id=id))
        tarefa.contato_id = contato_id

        db.session.commit()
        return redirect(url_for("tarefas"))
    return render_template("tarefa_form.html", tarefa=tarefa,
                           contatos=Contato.query.order_by(Contato.nome).all())


@app.route("/tarefas/<int:id>/deletar", methods=["POST"])
def deletar_tarefa(id):
    tarefa = db.get_or_404(Tarefa, id)
    db.session.delete(tarefa)
    db.session.commit()
    return redirect(url_for("tarefas"))


# ---------- Relatórios ----------

@app.route("/relatorios")
def relatorios():
    """Página com opções de exportação de relatórios."""
    contatos = Contato.query.order_by(Contato.nome).all()
    return render_template("relatorios.html", contatos=contatos)


@app.route("/relatorios/gerar", methods=["POST"])
def gerar_relatorio():
    """Gera um relatório em PDF com base nos filtros escolhidos."""
    tipo = request.form.get("tipo", "tarefas")
    status = request.form.get("status", "todos")
    prioridade = request.form.get("prioridade", "todas")
    contato_id = request.form.get("contato_id", type=int)
    data_inicio = request.form.get("data_inicio", "")
    data_fim = request.form.get("data_fim", "")
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Monta a consulta base
    if tipo == "contatos":
        query = Contato.query
        if contato_id:
            query = query.filter(Contato.id == contato_id)
        itens = query.order_by(Contato.nome).all()
        template = "relatorio_contatos.html"
        contexto = {
            "contatos": itens,
            "titulo": "Relatório de Contatos",
            "agora": agora,
        }
    else:
        query = Tarefa.query
        if status != "todos":
            query = query.filter(Tarefa.status == status)
        if prioridade != "todas":
            query = query.filter(Tarefa.prioridade == prioridade)
        if contato_id:
            query = query.filter(Tarefa.contato_id == contato_id)
        if data_inicio:
            query = query.filter(Tarefa.prazo >= data_inicio)
        if data_fim:
            query = query.filter(Tarefa.prazo <= data_fim)
        itens = query.order_by(Tarefa.id.desc()).all()
        template = "relatorio_tarefas.html"
        contexto = {
            "tarefas": itens,
            "titulo": "Relatório de Tarefas",
            "filtros": {
                "status": status,
                "prioridade": prioridade,
                "contato": contato_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            },
            "agora": agora,
        }

    # Renderiza o HTML do relatório
    html_renderizado = render_template(template, **contexto)

    # Gera o PDF com WeasyPrint (usa o mesmo CSS do site)
    pdf_bytes = HTML(string=html_renderizado).write_pdf()

    # Retorna o PDF para download
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{tipo}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    return response


@app.route("/contatos/novo", methods=["GET", "POST"])
def novo_contato():
    if request.method == "POST":
        contato = Contato(
            nome=request.form["nome"],
            email=request.form["email"],
            telefone=request.form["telefone"],
        )
        db.session.add(contato)
        db.session.commit()
        return redirect(url_for("contatos"))
    return render_template("contato_form.html")


@app.route("/contatos")
def contatos():
    lista = Contato.query.order_by(Contato.nome).all()
    return render_template("contatos.html", contatos=lista)


@app.route("/contatos/<int:id>/editar", methods=["GET", "POST"])
def editar_contato(id):
    contato = db.get_or_404(Contato, id)
    if request.method == "POST":
        contato.nome = request.form["nome"]
        contato.email = request.form["email"]
        contato.telefone = request.form["telefone"]
        db.session.commit()
        return redirect(url_for("contatos"))
    return render_template("contato_form.html", contato=contato)


@app.route("/contatos/<int:id>/deletar", methods=["POST"])
def deletar_contato(id):
    contato = db.get_or_404(Contato, id)
    db.session.delete(contato)
    db.session.commit()
    return redirect(url_for("contatos"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
