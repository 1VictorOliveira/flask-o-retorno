"""Gerenciador de Tarefas — estrutura inicial com Flask e Flask-SQLAlchemy."""

from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for
from models import db, Contato, Tarefa

app = Flask(__name__)

# Banco de dados SQLite local (criado em instance/app.db)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# Cria as tabelas automaticamente na inicialização do app
with app.app_context():
    db.create_all()


# ---------- Filtros de template ----------

@app.template_filter("br_date")
def br_date(value):
    """Formata uma data como dd/mm/aaaa."""
    return value.strftime("%d/%m/%Y") if value else "—"


# ---------- Rotas ----------

@app.route("/")
def home():
    return redirect(url_for("tarefas"))


@app.route("/tarefas")
def tarefas():
    Tarefa.verificar_atrasadas()  # checagem automática de prazos
    lista = Tarefa.query.order_by(Tarefa.id.desc()).all()
    return render_template("tarefas.html", tarefas=lista)


@app.route("/tarefas/nova", methods=["GET", "POST"])
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

    nova = Tarefa(
        descricao=descricao,
        prazo=prazo,
        prioridade=prioridade,
        status=status,
        contato_id=request.form.get("contato_id", type=int),
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

        tarefa.contato_id = request.form.get("contato_id", type=int)
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
