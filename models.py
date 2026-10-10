from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    telefone = db.Column(db.String(20))
    tarefas = db.relationship("Tarefa", backref="contato", cascade="all, delete-orphan")

class Tarefa(db.Model):
    STATUS_PENDENTE = "pendente"
    STATUS_CONCLUIDA = "concluida"
    STATUS_ATRASADA = "atrasada"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    prazo = db.Column(db.Date, nullable=True)
    prioridade = db.Column(db.String(10), nullable=False, default="media")
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDENTE)
    contato_id = db.Column(db.Integer, db.ForeignKey("contato.id"), nullable=True)

    def __repr__(self):
        return f"<Tarefa {self.id}: {self.descricao}>"

    def verificar_atraso(self, hoje=None):
        """Compara o prazo com a data/hora atual e marca como atrasada.

        Retorna True se o status foi alterado. Tarefas com status
        "concluida" nunca são marcadas como atrasadas, mesmo com
        o prazo vencido.
        """
        if hoje is None:
            hoje = datetime.now().date()
        if (
            self.prazo is not None
            and self.prazo < hoje
            and self.status != self.STATUS_CONCLUIDA
        ):
            self.status = self.STATUS_ATRASADA
            return True
        return False

    @classmethod
    def verificar_atrasadas(cls):
        """Checa o prazo de todas as tarefas e salva as alterações no banco.

        Retorna a quantidade de tarefas recém-marcadas como atrasadas.
        """
        hoje = datetime.now().date()
        atrasadas = 0
        for tarefa in cls.query.all():
            if tarefa.verificar_atraso(hoje):
                atrasadas += 1
        if atrasadas:
            db.session.commit()
        return atrasadas