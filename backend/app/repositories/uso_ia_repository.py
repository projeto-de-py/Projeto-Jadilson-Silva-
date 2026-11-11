"""Padrao Repository: registro de uso da IA (somente insercao)."""

from sqlalchemy.orm import Session

from app.models.uso_ia import UsoIA


class UsoIARepository:
    def __init__(self, db: Session):
        self.db = db

    def registrar(self, **dados) -> UsoIA:
        registro = UsoIA(**dados)
        self.db.add(registro)
        self.db.commit()
        return registro
