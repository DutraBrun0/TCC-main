# app.py  (SUBSTITUA TODO O ARQUIVO PELO CONTEÚDO ABAIXO)
from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_app, db
from models import (
    Usuario, Produto, Variante, Estoque, MovimentoEstoque,
    Pedido, ItemPedido,
    registrar_entrada_variante, registrar_saida_variante
)
import os
import re
from datetime import datetime

# Diretórios
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "../frontend")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=TEMPLATE_DIR)
init_app(app)

# -------------------
# Páginas (mantém as suas)
# -------------------
@app.route("/inicio")
def inicio_page():
    return render_template("inicio.html")

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/register_page")
def register_page():
    return render_template("criar_conta.html")

@app.route("/produtos")
def produtos_page():
    return render_template("produtos.html")

@app.route("/clientes")
def clientes_page():
    return render_template("clientes.html")

@app.route("/lista_cliente")
def lista_cliente_page():
    return render_template("lista_clientes.html")

@app.route("/estoque")
def estoque_page():
    return render_template("estoque.html")

@app.route("/faturamento")
def faturamento_page():
    return render_template("faturamento.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# -------------------
# Util: gerar SKU simples (base do nome + partes das opções)
# -------------------
def gerar_sku_from_fields(produto_linha: str, altura=None, largura=None, cor=None, moldura=None):
    base = re.sub(r'[^A-Za-z0-9]', '', produto_linha[:3]).upper()
    parts = [base]
    if altura:
        parts.append(str(altura).replace('.', '').replace(',', ''))
    if largura:
        parts.append(str(largura).replace('.', '').replace(',', ''))
    if cor:
        parts.append(re.sub(r'[^A-Za-z0-9]', '', cor)[:6].upper())
    if moldura:
        parts.append(re.sub(r'[^A-Za-z0-9]', '', moldura)[:4].upper())
    sku = "-".join(parts)
    return sku[:60]


# -------------------
# Rotas de autenticação / registro (mantive sua lógica)
# -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    nome = data.get("nome")
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify(status="erro", mensagem="Preencha todos os campos"), 400

    if Usuario.query.filter_by(email=email.lower()).first():
        return jsonify(status="erro", mensagem="E-mail já cadastrado"), 400

    try:
        user = Usuario(
            nome=nome.lower() if nome else None,
            perfil="cliente",
            email=email.lower(),
            senha_hash=generate_password_hash(senha)
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(status="ok", mensagem="Conta criada com sucesso!")
    except Exception as e:
        db.session.rollback()
        return jsonify(status="erro", mensagem=str(e))


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify(status="erro", mensagem="Preencha todos os campos"), 400

    user = Usuario.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify(status="erro", mensagem="Conta não encontrada"), 401

    if not check_password_hash(user.senha_hash, senha):
        return jsonify(status="erro", mensagem="Senha incorreta"), 401

    return jsonify(status="ok", mensagem="Login realizado com sucesso")


# -------------------
# Teste DB
# -------------------
@app.route("/teste_db")
def teste_db():
    try:
        db.session.execute("SELECT 1")
        return "✅ Conectado ao banco!"
    except Exception as e:
        return f"❌ Erro ao conectar: {e}"


# -------------------
# Endpoints novos: CRUD para produto/variantes e controle de estoque por SKU
# -------------------
@app.route("/produto/variantes", methods=["POST"])
def criar_produto_com_variantes():
    """
    Espera JSON:
    {
      "linha": "Espelho Lux",
      "formato": "Retangular",
      "descricao": "...",
      "imagem_url": "...",
      "variantes": [ { altura_cm, largura_cm, cor, led_direto, led_indireto, moldura, preco_base, estoque_inicial }, ... ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "payload JSON required"}), 400

    linha = data.get("linha")
    formato = data.get("formato")
    descricao = data.get("descricao")
    imagem_url = data.get("imagem_url")
    variantes = data.get("variantes", [])

    if not linha or not formato:
        return jsonify({"error": "linha and formato required"}), 400

    produto = Produto(
        linha=linha,
        formato=formato,
        descricao=descricao,
        imagem_url=imagem_url
    )
    try:
        db.session.add(produto)
        db.session.flush()  # para obter produto.id

        resposta_variantes = []
        for v in variantes:
            altura = v.get("altura_cm")
            largura = v.get("largura_cm")
            cor = v.get("cor")
            moldura = v.get("moldura")
            preco_base = v.get("preco_base", 0)
            estoque_inicial = int(v.get("estoque_inicial", 0))

            sku_base = gerar_sku_from_fields(linha, altura, largura, cor, moldura)
            sku = sku_base
            # garantir SKU único
            i = 1
            while Variante.query.filter_by(sku=sku).first():
                i += 1
                sku = f"{sku_base}-{i}"

            variante = Variante(
                produto_id=produto.id,
                altura_cm=altura,
                largura_cm=largura,
                cor=cor,
                led_direto=bool(v.get("led_direto", False)),
                led_indireto=bool(v.get("led_indireto", False)),
                moldura=moldura,
                sku=sku,
                preco_base=preco_base,
                ativo=True
            )
            db.session.add(variante)
            db.session.flush()

            # criar estoque associado
            estoque = Estoque(
                variante_id=variante.id,
                quantidade=estoque_inicial,
                minimo=int(v.get("minimo", 0))
            )
            db.session.add(estoque)

            resposta_variantes.append({
                "variante_id": variante.id,
                "sku": sku,
                "preco_base": str(preco_base),
                "estoque_inicial": estoque_inicial
            })

        db.session.commit()
        return jsonify({"produto_id": produto.id, "variantes": resposta_variantes}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/produto/catalogo", methods=["GET"])
def listar_catalogo():
    """
    Retorna todas as variantes ativas com dados do produto e estoque.
    """
    q = db.session.query(Produto, Variante, Estoque) \
        .join(Variante, Variante.produto_id == Produto.id) \
        .outerjoin(Estoque, Estoque.variante_id == Variante.id) \
        .filter(Produto.ativo == True, Variante.ativo == True) \
        .all()

    resultado = []
    for prod, var, est in q:
        resultado.append({
    "produto_id": prod.id,
    "nome_produto": f"{prod.linha} {prod.formato}",
    "linha": prod.linha,
    "formato": prod.formato,
    "variante_id": var.id,
    "sku": var.sku,
    "altura_cm": float(var.altura_cm) if var.altura_cm is not None else None,
    "largura_cm": float(var.largura_cm) if var.largura_cm is not None else None,
    "cor": var.cor,
    "moldura": var.moldura,
    "preco_base": str(var.preco_base),
    "estoque": int(est.quantidade) if est is not None else 0
})
    return jsonify(resultado)


@app.route("/estoque/variantes", methods=["GET"])
def listar_variantes_estoque():
    variantes = Variante.query.filter_by(ativo=True).all()
    resp = []
    for v in variantes:
        est = v.estoque
        resp.append({
            "variante_id": v.id,
            "produto_id": v.produto_id,
            "nome_produto": v.produto.linha,     # 🟩 AQUI!
            "formato": v.produto.formato,        # opcional
            "sku": v.sku,
            "altura_cm": float(v.altura_cm) if v.altura_cm is not None else None,
            "largura_cm": float(v.largura_cm) if v.largura_cm is not None else None,
            "cor": v.cor,
            "moldura": v.moldura,
            "preco_base": str(v.preco_base),
            "estoque": int(est.quantidade) if est else 0,
            "minimo": int(est.minimo) if est else 0
        })
    return jsonify(resp)

@app.route("/estoque/entrada_sku", methods=["POST"])
def entrada_sku():
    """
    Payload: { "variante_id": 1, "quantidade": 5, "usuario_id": 1, "motivo": "compra" }
    """
    data = request.get_json()
    variante_id = data.get("variante_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = data.get("usuario_id")
    motivo = data.get("motivo", "Entrada manual")

    if not variante_id or quantidade <= 0:
        return jsonify({"error": "variante_id and quantidade>0 required"}), 400

    try:
        novo = registrar_entrada_variante(variante_id=variante_id, quantidade=quantidade, usuario_id=usuario_id, motivo=motivo)
        return jsonify({"status": "ok", "estoque_atual": novo})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


@app.route("/estoque/saida_sku", methods=["POST"])
def saida_sku():
    """
    Payload: { "variante_id": 1, "quantidade": 2, "usuario_id": 1, "motivo": "venda" }
    """
    data = request.get_json()
    variante_id = data.get("variante_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = data.get("usuario_id")
    motivo = data.get("motivo", "Saída por pedido")

    if not variante_id or quantidade <= 0:
        return jsonify({"error": "variante_id and quantidade>0 required"}), 400

    try:
        novo = registrar_saida_variante(variante_id=variante_id, quantidade=quantidade, usuario_id=usuario_id, motivo=motivo)
        return jsonify({"status": "ok", "estoque_atual": novo})
    except ValueError as ve:
        return jsonify({"status": "erro", "mensagem": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# -------------------
# Compatibilidade: manter /estoque/entrada (produto_id) se alguém ainda usar
# -------------------
@app.route("/estoque/entrada", methods=["POST"])
def entrada_estoque_compat():
    """
    Endpoint legado: tenta localizar variante pelo produto e incrementar estoque da primeira variante.
    Payload antigo: { "produto_id": X, "quantidade": Y, "usuario_id": Z }
    """
    data = request.get_json()
    produto_id = data.get("produto_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = data.get("usuario_id")

    if not produto_id or quantidade <= 0:
        return jsonify({"status": "erro", "mensagem": "produto_id and quantidade>0 required"}), 400

    # pega primeira variante ativa do produto (comportamento de compatibilidade)
    variante = Variante.query.filter_by(produto_id=produto_id, ativo=True).first()
    if not variante:
        return jsonify({"status": "erro", "mensagem": "Nenhuma variante encontrada para o produto"}), 404

    try:
        novo = registrar_entrada_variante(variante_id=variante.id, quantidade=quantidade, usuario_id=usuario_id, motivo="Entrada compatibilidade produto")
        return jsonify({"status": "ok", "estoque_atual": novo})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


# -------------------
# Pedido confirmar (compatibilidade) — deduz estoque usando variante_id do item_pedido
# -------------------
@app.route("/pedido/confirmar", methods=["POST"])
def confirmar_pedido():
    data = request.get_json()
    item_id = data.get("item_pedido_id")
    usuario_id = data.get("usuario_id")

    if not item_id:
        return jsonify({"status": "erro", "mensagem": "item_pedido_id required"}), 400

    item = ItemPedido.query.get(item_id)
    if not item:
        return jsonify({"status": "erro", "mensagem": "Item não encontrado"}), 404

    try:
        novo = registrar_saida_variante(variante_id=item.variante_id, quantidade=int(item.quantidade), usuario_id=usuario_id, motivo="Saída por confirmação de pedido")
        return jsonify({"status": "ok", "estoque_atual": novo})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


# -------------------
# API Clientes (lista)
# -------------------
@app.route('/api/clientes', methods=['GET'])
def api_clientes():
    clientes = Usuario.query.all()
    return jsonify([
        {
            "id": c.id,
            "nome": c.nome,
            "email": c.email
        }
        for c in clientes
    ])


# -------------------
# Criar pedido via API (grava pedido, itens e atualiza estoque)
# -------------------
@app.route('/pedido/criar', methods=['POST'])
def criar_pedido():
    data = request.get_json()

    cliente_id = data.get("cliente_id")
    itens = data.get("itens", [])

    if not cliente_id:
        return jsonify({"error": "cliente_id obrigatório"}), 400
    if not itens:
        return jsonify({"error": "Nenhum item no pedido"}), 400

    try:
        pedido = Pedido(
            cliente_nome="Cliente ID " + str(cliente_id),
            cliente_contato=None,
            status="criado",
            total=0,
            criado_por=cliente_id
        )

        db.session.add(pedido)
        db.session.flush()

        total_geral = 0

        for item in itens:
            variante_id = item.get("variante_id")
            quantidade = item.get("quantidade")
            preco_unit = item.get("preco_unit")

            # Validação forte
            if not variante_id:
                return jsonify({"error": "variante_id faltando em um item"}), 400
            if not quantidade:
                return jsonify({"error": "quantidade inválida"}), 400
            if int(quantidade) <= 0:
                return jsonify({"error": "quantidade precisa ser > 0"}), 400
            if not preco_unit:
                return jsonify({"error": "preco_unit inválido"}), 400

            quantidade = int(quantidade)
            preco_unit = float(preco_unit)

            # Criar item
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                variante_id=variante_id,
                quantidade=quantidade,
                preco_unit=preco_unit,
                valor_total=preco_unit * quantidade
            )
            db.session.add(item_pedido)

            # 🔥 CHAMA A FUNÇÃO QUE REALMENTE ALTERA O ESTOQUE
            registrar_saida_variante(
                variante_id=variante_id,
                quantidade=quantidade,
                usuario_id=cliente_id,
                motivo="Venda"
            )

            total_geral += preco_unit * quantidade

        pedido.total = total_geral
        db.session.commit()

        return jsonify({
            "status": "ok",
            "pedido_id": pedido.id,
            "total": total_geral
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# -------------------
# Listar pedidos (para faturamento / dashboard)
# -------------------
@app.route('/pedido/listar', methods=['GET'])
def listar_pedidos():
    """
    Lista pedidos com itens e informações das variantes.
    """
    pedidos = Pedido.query.order_by(Pedido.created_at.desc()).limit(100).all()
    resultado = []

    for p in pedidos:
        itens_processados = []
        for item in p.itens:
            var = Variante.query.get(item.variante_id)
            itens_processados.append({
                "variante_id": item.variante_id,
                "sku": var.sku if var else None,
                "quantidade": int(item.quantidade),
                "preco_unit": float(item.preco_unit),
                "valor_total": float(item.valor_total)
            })

        resultado.append({
            "id": p.id,
            "cliente_nome": p.cliente_nome,
            "total": float(p.total or 0),
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None,
            "itens": itens_processados
        })

    return jsonify(resultado)


# -------------------
# Run
# -------------------
if __name__ == "__main__":
    app.run(debug=True)
