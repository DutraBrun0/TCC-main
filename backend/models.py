from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash


# ==========================
# 👤 Tabela de Usuários
# ==========================
class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    perfil = db.Column(db.String(50))
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    pedidos = db.relationship("Pedido", backref="usuario", lazy=True)
    entradas = db.relationship("EntradaEstoque", backref="usuario", lazy=True)

    # --- 🔒 Funções de segurança ---
    def set_senha(self, senha: str):
        """Gera o hash seguro da senha antes de salvar."""
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        """Compara a senha digitada com o hash salvo."""
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Usuario {self.nome}>"


# ==========================
# 📦 Tabela de Produtos
# ==========================
class Produto(db.Model):
    __tablename__ = "produto"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.Enum('insumo', 'produto_final'), nullable=False)
    preco_unit = db.Column(db.Numeric(14, 2), nullable=False)
    unidade_medida = db.Column(db.String(50))

    itens_pedido = db.relationship("ItemPedido", backref="produto", lazy=True)
    estoque = db.relationship("Estoque", uselist=False, backref="produto", lazy=True)

    def __repr__(self):
        return f"<Produto {self.nome}>"


# ==========================
# 🧾 Tabela de Pedidos
# ==========================
class Pedido(db.Model):
    __tablename__ = "pedido"

    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(255), nullable=False)
    cliente_contato = db.Column(db.String(255))
    status = db.Column(
        db.Enum('criado', 'aprovado', 'em_producao', 'em_logistica', 'entregue', 'finalizado'),
        default='criado',
        nullable=False
    )
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0.00)
    criado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    itens = db.relationship("ItemPedido", backref="pedido", lazy=True)

    def __repr__(self):
        return f"<Pedido {self.id} - {self.cliente_nome}>"


# ==========================
# 🧱 Tabela de Itens do Pedido
# ==========================
class ItemPedido(db.Model):
    __tablename__ = "item_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Numeric(14, 2), nullable=False)
    preco_unit = db.Column(db.Numeric(14, 2), nullable=False)
    total_item = db.Column(db.Numeric(14, 2), nullable=False)

    def __repr__(self):
        return f"<ItemPedido Pedido:{self.pedido_id} Produto:{self.produto_id}>"


# ==========================
# 📦 Tabela de Estoque
# ==========================
class Estoque(db.Model):
    __tablename__ = "estoque"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade_atual = db.Column(db.Numeric(14, 2), nullable=False, default=0.00)
    ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entradas = db.relationship("EntradaEstoque", backref="estoque", lazy=True)

    def __repr__(self):
        return f"<Estoque Produto:{self.produto_id} Quantidade:{self.quantidade_atual}>"


# ==========================
# 🧾 Tabela de Entradas de Estoque
# ==========================
class EntradaEstoque(db.Model):
    __tablename__ = "entrada_estoque"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Numeric(14, 2), nullable=False)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    estoque_id = db.Column(db.Integer, db.ForeignKey("estoque.id"))

    def __repr__(self):
        return f"<EntradaEstoque Produto:{self.produto_id} Quantidade:{self.quantidade}>"


# ==========================
# 🛠 Funções auxiliares de estoque
# ==========================
def registrar_entrada(produto_id: int, quantidade: float, usuario_id: int, motivo: str = "Entrada manual") -> float:
    """Registra entrada de produto e atualiza estoque."""
    estoque = Estoque.query.filter_by(produto_id=produto_id).first()

    if not estoque:
        estoque = Estoque(produto_id=produto_id, quantidade_atual=0)
        db.session.add(estoque)
        db.session.commit()  # gera ID do estoque

    entrada = EntradaEstoque(
        produto_id=produto_id,
        estoque_id=estoque.id,
        quantidade=quantidade,
        criado_por=usuario_id,
        data_entrada=datetime.utcnow()
    )
    db.session.add(entrada)

    estoque.quantidade_atual += quantidade
    estoque.ultima_atualizacao = datetime.utcnow()

    db.session.commit()
    return float(estoque.quantidade_atual)


def registrar_saida(item_pedido_id: int, usuario_id: int) -> float:
    """Deduz do estoque os itens de um pedido."""
    item = ItemPedido.query.get(item_pedido_id)
    if not item:
        raise ValueError("Item do pedido não encontrado.")

    estoque = Estoque.query.filter_by(produto_id=item.produto_id).first()
    if not estoque or estoque.quantidade_atual < item.quantidade:
        raise ValueError("Estoque insuficiente.")

    entrada = EntradaEstoque(
        produto_id=item.produto_id,
        estoque_id=estoque.id,
        quantidade=-item.quantidade,  # negativo para saída
        criado_por=usuario_id,
        data_entrada=datetime.utcnow()
    )
    db.session.add(entrada)

    estoque.quantidade_atual -= item.quantidade
    estoque.ultima_atualizacao = datetime.utcnow()

    db.session.commit()
    return float(estoque.quantidade_atual)
