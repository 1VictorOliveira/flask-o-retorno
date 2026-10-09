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
    lista = Tarefa.query.order_by(Tarefa.id.desc()).all()
    return render_template("tarefas.html", tarefas=lista)


@app.route("/tarefas/nova", methods=["POST"])
def nova_tarefa():
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

    nova = Tarefa(
        descricao=descricao,
        prazo=prazo,
        prioridade=prioridade,
        status="pendente",
    )
    db.session.add(nova)
    db.session.commit()
    return redirect(url_for("tarefas"))


@app.route("/tarefas/<int:id>/deletar", methods=["POST"])
def deletar_tarefa(id):
    tarefa = db.get_or_404(Tarefa, id)
    db.session.delete(tarefa)
    db.session.commit()
    return redirect(url_for("tarefas"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
