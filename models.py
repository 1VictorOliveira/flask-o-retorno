from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    telefone = db.Column(db.String(20))
    tarefas = db.relationship("Tarefa", backref="contato", cascade="all, delete-orphan")

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    prazo = db.Column(db.Date, nullable=True)
    prioridade = db.Column(db.String(10), nullable=False, default="media")
    status = db.Column(db.String(20), nullable=False, default="pendente")
    contato_id = db.Column(db.Integer, db.ForeignKey("contato.id"), nullable=True)

    def __repr__(self):
        return f"<Tarefa {self.id}: {self.descricao}>"