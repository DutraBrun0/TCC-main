# models.py  (SUBSTITUA TODO O ARQUIVO PELO CONTEÚDO ABAIXO)
from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================
# 👤 Tabela de Usuários
# ==========================
class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    senha_hash = db.Column(db.Text, nullable=False)
    perfil = db.Column(db.String(50), default=None)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_senha(self, senha: str):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Usuario {self.nome}>"


# ==========================
# 📦 Tabela de Produto
# ==========================
class Produto(db.Model):
    __tablename__ = "produto"

    id = db.Column(db.Integer, primary_key=True)
    linha = db.Column(db.String(255), nullable=False)
    formato = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text)
    imagem_url = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    variantes = db.relationship("Variante", backref="produto", lazy=True)

    def __repr__(self):
        return f"<Produto {self.linha} - {self.formato}>"


# ==========================
# 🆕 Tabela: Variante
# ==========================
class Variante(db.Model):
    __tablename__ = "variante"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    altura_cm = db.Column(db.Numeric(7,2), nullable=True)
    largura_cm = db.Column(db.Numeric(7,2), nullable=True)
    cor = db.Column(db.String(100), nullable=True)
    led_direto = db.Column(db.Boolean, default=False)
    led_indireto = db.Column(db.Boolean, default=False)
    moldura = db.Column(db.String(100), nullable=True)
    sku = db.Column(db.String(100), nullable=False, unique=True, index=True)
    preco_base = db.Column(db.Numeric(12,2), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    estoque = db.relationship("Estoque", uselist=False, backref="variante", lazy=True)
    itens_pedido = db.relationship("ItemPedido", backref="variante", lazy=True)

    def __repr__(self):
        return f"<Variante SKU:{self.sku} Produto:{self.produto_id}>"


# ==========================
# 📦 Estoque
# ==========================
class Estoque(db.Model):
    __tablename__ = "estoque"

    id = db.Column(db.Integer, primary_key=True)
    variante_id = db.Column(db.Integer, db.ForeignKey("variante.id"), nullable=False, unique=True)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    minimo = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    movimentos = db.relationship("MovimentoEstoque", backref="estoque", lazy=True)

    def __repr__(self):
        return f"<Estoque Variante:{self.variante_id} Qty:{self.quantidade}>"


# ==========================
# 🧾 Movimento de Estoque
# ==========================
class MovimentoEstoque(db.Model):
    __tablename__ = "movimento_estoque"

    id = db.Column(db.Integer, primary_key=True)
    estoque_id = db.Column(db.Integer, db.ForeignKey("estoque.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    observacao = db.Column(db.Text)

    def __repr__(self):
        return f"<MovimentoEstoque Estoque:{self.estoque_id} Qtd:{self.quantidade}>"


# ==========================
# 🧾 Tabela Pedido
# ==========================
class Pedido(db.Model):
    __tablename__ = "pedido"

    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(255), nullable=False)
    cliente_contato = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('criado','aprovado','em_producao','em_logistica','entregue','finalizado'),
                            default='criado', nullable=False)
    total = db.Column(db.Numeric(14,2), nullable=False, default=0.00)
    criado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    itens = db.relationship("ItemPedido", backref="pedido", lazy=True)

    def __repr__(self):
        return f"<Pedido {self.id} - {self.cliente_nome}>"


# ==========================
# 🧾 ItemPedido
# ==========================
class ItemPedido(db.Model):
    __tablename__ = "item_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    variante_id = db.Column(db.Integer, db.ForeignKey("variante.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unit = db.Column(db.Numeric(12,2), nullable=False)
    valor_total = db.Column(db.Numeric(12,2), nullable=False)
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f"<ItemPedido Pedido:{self.pedido_id} Variante:{self.variante_id}>"


# ==========================
# Funções Utilitárias de Estoque (MODIFICADAS PARA TRANSAÇÃO SEGURA)
# ==========================

def registrar_entrada_variante(variante_id: int, quantidade: int, usuario_id: int = None, motivo: str = "Entrada manual", commit=False):
    """
    Registra entrada no estoque.
    IMPORTANTE: Por padrão, NÃO commita (commit=False). Quem chamar deve dar db.session.commit().
    """
    estoque = Estoque.query.filter_by(variante_id=variante_id).first()
    if not estoque:
        estoque = Estoque(variante_id=variante_id, quantidade=0, minimo=0)
        db.session.add(estoque)
        db.session.flush()

    # registra movimento
    mov = MovimentoEstoque(
        estoque_id=estoque.id,
        usuario_id=usuario_id,
        quantidade=quantidade,
        motivo=motivo,
        data=datetime.utcnow()
    )
    db.session.add(mov)

    # atualiza estoque
    estoque.quantidade = estoque.quantidade + int(quantidade)
    estoque.updated_at = datetime.utcnow()

    # Só salva se for explicitamente solicitado (útil para rotas simples de ajuste manual)
    if commit:
        db.session.commit()
        
    return int(estoque.quantidade)


def registrar_saida_variante(variante_id, quantidade, usuario_id=None, motivo="Saída", commit=False):
    """
    Registra saída do estoque.
    IMPORTANTE: Por padrão, NÃO commita. Isso permite que seja usada dentro do loop de Pedido.
    """
    variante = Variante.query.get(variante_id)
    if not variante:
        raise ValueError("Variante não encontrada")

    estoque = Estoque.query.filter_by(variante_id=variante_id).first()
    if not estoque:
        raise ValueError("Estoque não encontrado para esta variante")

    quantidade = int(quantidade)

    # 🛑 impedir estoque negativo
    if quantidade > estoque.quantidade:
        raise ValueError(
            f"Estoque insuficiente. Disponível: {estoque.quantidade}, solicitado: {quantidade}"
        )

    # reduzir estoque
    estoque.quantidade -= quantidade
    estoque.updated_at = datetime.utcnow()

    # registrar movimento
    movimento = MovimentoEstoque(
        estoque_id=estoque.id,
        usuario_id=usuario_id if usuario_id else None,
        quantidade=quantidade,
        motivo=motivo,
        data=datetime.utcnow()
    )

    db.session.add(movimento)
    
    # IMPORTANTE: Apenas Flush, não Commit, a menos que forçado.
    # Isso garante que o Pedido possa comitar tudo de uma vez.
    db.session.flush() 

    if commit:
        db.session.commit()

    return estoque.quantidade