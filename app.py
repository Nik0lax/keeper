import os
import sqlite3
from pathlib import Path
from functools import wraps
from flask import (
    Flask, g, render_template, request, redirect, url_for, flash, session, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
import config 

# Caminho raiz da aplicação (pasta onde está o app.py)
APP_DIR = Path(__file__).parent


# ---------- Factory da aplicação ----------
def create_app():
    # Cria a instância principal do Flask
    app = Flask(__name__)
    
    app.config["DATABASE"] = config.DB_FILE
    app.secret_key = config.SECRET_KEY

    app.config['VERSION'] = '1.0.0'

    @app.context_processor
    def inject_version():
        return dict(version=app.config['VERSION'])

    # Inicializa o banco dentro do contexto da aplicação
    with app.app_context():
        init_db(app.config["DATABASE"])

    # Registra as rotas (função separada para manter o código organizado)
    register_routes(app)
    return app


# ---------- Helpers do banco de dados ----------
def get_db():
    # Retorna a conexão atual, ou cria uma nova se ainda não existir
    if "db" not in g:
        con = sqlite3.connect(current_db_path())
        con.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        con.execute("PRAGMA foreign_keys = ON;")  # Garante integridade referencial
        g.db = con
    return g.db

def close_db(e=None):
    # Fecha a conexão com o banco no fim da requisição
    db = g.pop("db", None)
    if db is not None:
        db.close()

def current_db_path():
    # Retorna o caminho do banco, priorizando variável de ambiente
    return os.getenv("KEEPER_DB") or config.DB_FILE

def init_db(db_path):
    """
    Inicializa o banco de dados a partir do schema.sql caso ele não exista
    ou se estiver sem a tabela 'users'.
    """
    db_file = Path(db_path)
    should_init = False

    if not db_file.exists():
        should_init = True
    else:
        try:
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            # Verifica se a tabela 'users' existe
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if cur.fetchone() is None:
                should_init = True
            con.close()
        except Exception:
            # Se houver erro de conexão ou leitura, inicializa
            should_init = True

    if should_init:
        schema_file = APP_DIR / "schema.sql"
        if not schema_file.exists():
            raise FileNotFoundError(f"schema.sql não encontrado em {schema_file}")
        with sqlite3.connect(db_path) as conn, open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        print(f"Banco inicializado com sucesso usando {schema_file} em {db_path}")


# ---------- Helpers de autenticação ----------
def login_required(view):
    # Decorator para restringir acesso a usuários logados
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            # Redireciona pro login e guarda a rota original
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view

def get_current_user():
    # Recupera o usuário atual com base no ID da sessão
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    row = db.execute("SELECT id, username, role FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None

def create_user(username: str, password: str, role: str = "operator"):
    """
    Helper para criar usuário manualmente via shell.
    Criptografa a senha e insere no banco.
    """
    db = sqlite3.connect(current_db_path())
    db.execute("PRAGMA foreign_keys = ON;")
    ph = generate_password_hash(password)
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, ph, role)
        )
        db.commit()
        print(f"Usuário '{username}' criado com role='{role}'")
    except sqlite3.IntegrityError:
        print("Erro: username já existe")
    finally:
        db.close()

# ---------- Decorator para primeiro login ----------
def first_login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        from app import get_db  # caso precise importar
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))

        db = get_db()
        row = db.execute("SELECT first_login FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row["first_login"]:
            if request.endpoint != "alterar_senha":
                flash("Você precisa alterar sua senha antes de continuar.", "warning")
                return redirect(url_for("alterar_senha"))

        return view(*args, **kwargs)
    return wrapped_view

# ---------- Rotas ----------
def register_routes(app):
    # Fecha o banco no final de cada requisição
    app.teardown_appcontext(close_db)

    @app.route("/")
    def index():
        # Redireciona automaticamente para dashboard se logado
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            db = get_db()

            row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

            if row is None or not check_password_hash(row["password_hash"], password):
                flash("Usuário ou senha inválidos.", "danger")
                return redirect(url_for("login"))

            # Login bem-sucedido → grava sessão
            session.clear()
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            session["role"] = row["role"]

            next_page = request.args.get("next") or url_for("dashboard")
            return redirect(next_page)

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        # Limpa a sessão e redireciona pro login
        session.clear()
        flash("Você saiu do sistema.", "info")
        return redirect(url_for("login"))

    # ---------- CRUD completo de Usuários ----------
    @app.route("/usuarios", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def usuarios():
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()
        per_page = 7

        # Criar usuário
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            role = request.form.get("role", "operator").strip()

            if not username or not password:
                flash("Preencha login e senha.", "warning")
                return redirect(url_for("usuarios"))

            ph = generate_password_hash(password)
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, ph, role)
                )
                db.commit()
                flash("Usuário criado com sucesso.", "success")
            except sqlite3.IntegrityError:
                flash("Login já existe.", "warning")
            # redireciona pra primeira página por padrão
            return redirect(url_for("usuarios", page=1))

        # GET -> paginação
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        total_row = db.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        total = total_row["total"] if (hasattr(total_row, "keys") or isinstance(total_row, dict)) else total_row[0]
        total_pages = (total + per_page - 1) // per_page

        if total_pages > 0 and page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        rows = db.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY username LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }

        return render_template(
            "usuarios.html",
            usuarios=rows,
            current_user=current_user,
            pagination=pagination
        )



    @app.route("/excluir_usuario/<int:user_id>", methods=["POST"])
    @login_required
    @first_login_required
    def excluir_usuario(user_id):
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()
        if current_user["id"] == user_id:
            flash("Você não pode excluir seu próprio usuário.", "warning")
            return redirect(url_for("usuarios"))

        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        flash("Usuário excluído com sucesso.", "success")
        return redirect(url_for("usuarios"))


    @app.route("/editar_usuario/<int:user_id>", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def editar_usuario(user_id):
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()
        usuario = db.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not usuario:
            flash("Usuário não encontrado.", "warning")
            return redirect(url_for("usuarios"))

        # Resetar senha e marcar first_login=1
        if request.method == "POST":
            role = request.form.get("role", "operator")
            password = request.form.get("password", "").strip()

            if password:
                ph = generate_password_hash(password)
                db.execute(
                    "UPDATE users SET role = ?, password_hash = ?, first_login = 1 WHERE id = ?",
                    (role, ph, user_id)
                )
            else:
                db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            db.commit()
            flash("Usuário atualizado com sucesso.", "success")
            return redirect(url_for("usuarios"))

        return render_template("editar_usuario.html", usuario=usuario)
   
    @app.route("/alterar_senha", methods=["GET", "POST"])
    @login_required
    def alterar_senha():
        db = get_db()
        user = get_current_user()

        if request.method == "POST":
            senha_nova = request.form.get("password", "").strip()
            senha_confirm = request.form.get("confirm_password", "").strip()

            if not senha_nova or senha_nova != senha_confirm:
                flash("Senhas não coincidem ou estão vazias.", "warning")
                return redirect(url_for("alterar_senha"))

            ph = generate_password_hash(senha_nova)
            db.execute(
                "UPDATE users SET password_hash = ?, first_login = 0 WHERE id = ?",
                (ph, user["id"])
            )
            db.commit()
            flash("Senha alterada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        return render_template("alterar_senha.html", user=user)

    @app.route("/dashboard")
    @login_required
    @first_login_required
    def dashboard():
        """
        Painel com cards de totais.
        """
        db = get_db()
        user = get_current_user()

        # Totais básicos
        total_itens = db.execute("SELECT COUNT(*) FROM itens").fetchone()[0]
        total_movimentacoes = db.execute("SELECT COUNT(*) FROM movimentacao").fetchone()[0]
        total_localizacoes = db.execute("SELECT COUNT(*) FROM localizacoes").fetchone()[0]

        # Apenas admins veem total de usuários
        total_usuarios = 0
        if user and user.get("role") == "admin":
            total_usuarios = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        return render_template(
            "dashboard.html",
            user=user,
            totals={
                "itens": total_itens,
                "movimentacoes": total_movimentacoes,
                "localizacoes": total_localizacoes,
                "usuarios": total_usuarios
            }
        )

    # ---------- módulo CADASTRO ----------
    @app.route("/itens", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def itens():
        """
        Tela para cadastrar itens (nome + tipo) e listar os itens existentes,
        com paginação de 7 resultados por página.
        """
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()
        per_page = 7

        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            tipo = request.form.get("tipo", "").strip()
            descricao = request.form.get("descricao", "").strip()

            if not nome or not tipo:
                flash("Preencha nome e tipo do item.", "warning")
                return redirect(url_for("itens"))

            try:
                db.execute(
                    "INSERT INTO itens (nome, tipo, descricao) VALUES (?, ?, ?)",
                    (nome, tipo, descricao)
                )
                db.commit()
                flash("Item cadastrado com sucesso.", "success")
            except sqlite3.IntegrityError:
                flash("Item já existe.", "warning")
            # redireciona para a primeira página (ou trocar para última se preferir)
            return redirect(url_for("itens", page=1))

        # GET -> paginação
        # pega o número da página da query string (ex: /itens?page=2)
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        # total de itens (para calcular total de páginas)
        total_row = db.execute("SELECT COUNT(*) AS total FROM itens").fetchone()
        total = total_row["total"] if isinstance(total_row, dict) or hasattr(total_row, 'keys') else total_row[0]
        total_pages = (total + per_page - 1) // per_page  # ceil sem importar ceil (inteiro)

        # se pedir uma página além do total, ajusta
        if total_pages > 0 and page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        rows = db.execute(
            "SELECT * FROM itens ORDER BY nome LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }

        return render_template("itens.html", itens=rows, pagination=pagination)
   
    @app.route("/excluir_item/<int:item_id>", methods=["POST"])
    @login_required
    @first_login_required
    def excluir_item(item_id):
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()

        # Primeiro, buscar o item para pegar nome e tipo
        item = db.execute("SELECT nome, tipo FROM itens WHERE id = ?", (item_id,)).fetchone()
        if item:
            nome, tipo = item["nome"], item["tipo"]

            # Deletar do estoque
            db.execute("DELETE FROM estoque WHERE nome = ? AND tipo = ?", (nome, tipo))

            # Deletar do itens
            db.execute("DELETE FROM itens WHERE id = ?", (item_id,))
            db.commit()
            flash("Item e registros no estoque excluídos com sucesso.", "success")
        else:
            flash("Item não encontrado.", "warning")

        return redirect(url_for("itens"))
        
    @app.route("/localizacoes", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def localizacoes():
        """
        CRUD mínimo: cadastrar e listar localizações/setores com paginação.
        """
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))

        db = get_db()
        per_page = 7

        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            if not nome:
                flash("Nome da localização é obrigatório.", "warning")
                return redirect(url_for("localizacoes"))
            try:
                db.execute("INSERT INTO localizacoes (nome) VALUES (?)", (nome,))
                db.commit()
                flash("Localização criada.", "success")
            except sqlite3.IntegrityError:
                flash("Localização já existe.", "warning")
            # Redireciona para a primeira página após criação (padrão)
            return redirect(url_for("localizacoes", page=1))

        # GET -> paginação
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        total_row = db.execute("SELECT COUNT(*) AS total FROM localizacoes").fetchone()
        # lidar com sqlite3.Row ou tupla
        total = total_row["total"] if (hasattr(total_row, "keys") or isinstance(total_row, dict)) else total_row[0]
        total_pages = (total + per_page - 1) // per_page

        if total_pages > 0 and page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        rows = db.execute(
            "SELECT * FROM localizacoes ORDER BY nome LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }

        return render_template(
            "localizacoes.html",
            localizacoes=rows,
            pagination=pagination
        )

    @app.route("/excluir_localizacao/<int:localizacao_id>", methods=["POST"])
    @login_required
    @first_login_required
    def excluir_localizacao(localizacao_id):
        current_user = get_current_user()
        if current_user["role"] != "admin":
            flash("Acesso negado.", "danger")
            return redirect(url_for("index"))
            
        db = get_db()
        db.execute("DELETE FROM localizacoes WHERE id = ?", (localizacao_id,))
        db.commit()
        flash("Localização excluída com sucesso.", "success")
        return redirect(url_for("localizacoes"))
    # ---------- módulo estoque ----------
    
    @app.route("/estoque")
    @login_required
    @first_login_required
    def estoque():
        """Painel mostrando todos os itens e quantidade atual"""
        db = get_db()
        itens = db.execute("""
            SELECT 
                e.nome,
                e.tipo,
                e.quantidade,
                i.descricao
            FROM estoque e
            LEFT JOIN itens i ON e.nome = i.nome
            ORDER BY 
                CASE 
                    WHEN e.tipo = 'Toner' THEN 1
                    WHEN e.tipo = 'Cilindro' THEN 2
                    WHEN e.tipo = 'Etiqueta' THEN 3
                    WHEN e.tipo = 'Ribbon' THEN 4
                    ELSE 99
                END,
                e.nome ASC
        """).fetchall()
        return render_template("estoque.html", itens=itens)

    # rota: registrar movimentação (GET + POST)
    @app.route("/movimentacao", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def movimentacao():
        """
        Registrar entrada/saída.
        GET: renderiza o formulário (itens, localizacoes e últimos 5 registros).
        POST: recebe item_id, quantidade, movimento e local_id; busca nome/tipo em 'itens';
            atualiza tabela 'estoque' e insere na tabela 'movimentacao'.
        Observação: O campo 'tipo' NÃO vem do form — é determinado aqui a partir do item.
        """
        db = get_db()

        if request.method == "POST":
            # leitura segura do form
            item_id = request.form.get("item_id")
            try:
                quantidade = int(request.form.get("quantidade", 0))
            except (TypeError, ValueError):
                quantidade = 0
            movimento = (request.form.get("movimento") or "").strip()
            usuario = session.get("username")

            # validações iniciais mínimas
            if not item_id or quantidade <= 0 or movimento not in ("entrada", "saida"):
                flash("Preencha os campos corretamente.", "warning")
                return redirect(url_for("movimentacao"))

            # busca localização (opcional)
            local_id = request.form.get("local_id")  # pode vir vazio
            local_nome = None
            if local_id:
                try:
                    loc_row = db.execute("SELECT nome FROM localizacoes WHERE id = ?", (int(local_id),)).fetchone()
                except Exception:
                    loc_row = None
                if loc_row:
                    local_nome = loc_row["nome"]
                else:
                    flash("Localização selecionada inválida.", "warning")
                    return redirect(url_for("movimentacao"))

            # busca item no catálogo e pega o tipo automaticamente
            try:
                item_row = db.execute("SELECT nome, tipo FROM itens WHERE id = ?", (int(item_id),)).fetchone()
            except Exception:
                item_row = None

            if not item_row:
                flash("Item selecionado inválido.", "danger")
                return redirect(url_for("movimentacao"))

            nome = item_row["nome"]
            tipo = item_row["tipo"]  # <-- tipo determinado pelo catálogo, NÃO pelo form

            # atualiza estoque: se existe o registro, atualiza; se não existe e for entrada, cria
            row = db.execute(
                "SELECT id, quantidade FROM estoque WHERE nome = ? AND tipo = ?",
                (nome, tipo)
            ).fetchone()

            if row:
                # calcula nova quantidade dependendo do tipo de movimento
                if movimento == "entrada":
                    nova_qtd = row["quantidade"] + quantidade
                else:  # saida
                    nova_qtd = row["quantidade"] - quantidade

                if nova_qtd < 0:
                    flash("Não há estoque suficiente para esta saída.", "danger")
                    return redirect(url_for("movimentacao"))

                db.execute("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_qtd, row["id"]))
            else:
                # não existe registro no estoque
                if movimento == "saida":
                    flash("Não há estoque desse item.", "danger")
                    return redirect(url_for("movimentacao"))
                db.execute(
                    "INSERT INTO estoque (nome, tipo, quantidade) VALUES (?, ?, ?)",
                    (nome, tipo, quantidade)
                )

            # registra movimentação (guarda nome/tipo pra audit trail)
            db.execute(
                "INSERT INTO movimentacao (nome, tipo, quantidade, movimento, usuario, localizacao) VALUES (?, ?, ?, ?, ?, ?)",
                (nome, tipo, quantidade, movimento, usuario, local_nome)
            )
            db.commit()
            flash(f"Movimentação registrada: {movimento} de {quantidade}x {nome} ({tipo})" + (f" - Local: {local_nome}" if local_nome else ""), "success")
            return redirect(url_for("movimentacao"))

        # ---------- GET ----------
        itens_rows = db.execute("SELECT id, nome, tipo FROM itens ORDER BY nome").fetchall()
        local_rows = db.execute("SELECT id, nome FROM localizacoes ORDER BY nome").fetchall()

        usuario_atual = session.get("username")
        role = session.get("role", "")
        if role == "admin":
            ultimos = db.execute("SELECT * FROM movimentacao ORDER BY datahora DESC LIMIT 5").fetchall()
        else:
            ultimos = db.execute(
                "SELECT * FROM movimentacao WHERE usuario = ? ORDER BY datahora DESC LIMIT 5",
                (usuario_atual,)
            ).fetchall()

        return render_template("movimentacao.html", itens=itens_rows, localizacoes=local_rows, ultimos=ultimos) 

    # rota: excluir movimentação e restaurar estoque
    @app.route("/movimentacao/excluir/<int:mov_id>", methods=["POST"])
    @login_required
    @first_login_required
    def excluir_movimentacao(mov_id):
        db = get_db()
        # recupera movimentação
        mov = db.execute("SELECT * FROM movimentacao WHERE id = ?", (mov_id,)).fetchone()
        if not mov:
            flash("Registro não encontrado.", "warning")
            return redirect(url_for("movimentacao"))

        # busca o registro de estoque correspondente (nome + tipo)
        estoque = db.execute("SELECT id, quantidade FROM estoque WHERE nome = ? AND tipo = ?", (mov["nome"], mov["tipo"])).fetchone()

        if estoque:
            # reverte o efeito da movimentação
            if mov["movimento"] == "entrada":
                nova_qtd = estoque["quantidade"] - mov["quantidade"]
            else:  # saida
                nova_qtd = estoque["quantidade"] + mov["quantidade"]

            if nova_qtd < 0:
                # segurança: nunca deixar estoque negativo após remoção
                flash("Não é possível excluir: estoque resultante ficaria negativo.", "danger")
                return redirect(url_for("movimentacao"))

            db.execute("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_qtd, estoque["id"]))
        else:
            # se não existe registro de estoque:
            # - se a movimentação era saída, não conseguimos restaurar (erro)
            # - se era entrada, apenas ignoramos (não há nada a ajustar)
            if mov["movimento"] == "saida":
                flash("Erro ao restaurar estoque. Operação abortada.", "danger")
                return redirect(url_for("movimentacao"))
            # caso de entrada sem estoque atual: nada a fazer

        # remove a movimentação do histórico
        db.execute("DELETE FROM movimentacao WHERE id = ?", (mov_id,))
        db.commit()
        flash("Registro excluído e estoque restaurado.", "success")
        return redirect(url_for("movimentacao"))


    @app.route("/relatorio_entrada_saida", methods=["GET", "POST"])
    @login_required
    @first_login_required
    def relatorio_entrada_saida():
        """Relatório de movimentações com filtros, paginação e exportação Excel"""
        db = get_db()
        filtros = []
        params = []

        # Captura filtros (POST ou GET)
        if request.method == "POST":
            movimento = request.form.get("movimento", "")
            data_inicio = request.form.get("data_inicio", "")
            data_fim = request.form.get("data_fim", "")
        else:
            movimento = request.args.get("movimento", "")
            data_inicio = request.args.get("data_inicio", "")
            data_fim = request.args.get("data_fim", "")

        # Monta query base e params
        query_base = "SELECT * FROM movimentacao WHERE 1=1"
        if movimento in ("entrada", "saida"):
            query_base += " AND movimento=?"
            params.append(movimento)
        if data_inicio:
            query_base += " AND date(datahora) >= date(?)"
            params.append(data_inicio)
        if data_fim:
            query_base += " AND date(datahora) <= date(?)"
            params.append(data_fim)

        query_base += " ORDER BY datahora DESC"

        # Exportar Excel (respeita filtros)
        if request.args.get("export") == "excel":
            from openpyxl import Workbook
            from flask import send_file
            from io import BytesIO

            wb = Workbook()
            ws = wb.active
            ws.title = "Movimentações"

            # Cabeçalho
            ws.append(["DataHora", "Item", "Tipo", "Quantidade", "Movimento", "Usuário", "Localização"])
            for m in db.execute(query_base, params).fetchall():
                ws.append([
                    m["datahora"],
                    m["nome"],
                    m["tipo"],
                    m["quantidade"],
                    m["movimento"],
                    m["usuario"],
                    m.get("localizacao", "") if isinstance(m, dict) or hasattr(m, "keys") else m[6] if len(m) > 6 else ""
                ])

            output = BytesIO()
            wb.save(output)
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name="relatorio_movimentacoes.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Paginação para exibição normal
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1
        per_page = 10
        offset = (page - 1) * per_page

        # Total com os mesmos filtros => usamos subquery com alias para compatibilidade
        count_query = "SELECT COUNT(*) AS total FROM (" + query_base + ") AS subq"
        total_row = db.execute(count_query, params).fetchone()
        total = total_row["total"] if (hasattr(total_row, "keys") or isinstance(total_row, dict)) else total_row[0]
        total_pages = (total + per_page - 1) // per_page
        if total_pages > 0 and page > total_pages:
            page = total_pages
            offset = (page - 1) * per_page

        # Busca páginas com LIMIT/OFFSET
        paged_query = query_base + " LIMIT ? OFFSET ?"
        paged_params = params + [per_page, offset]
        movimentacoes = db.execute(paged_query, paged_params).fetchall()

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }

        return render_template(
            "relatorio_entrada_saida.html",
            movimentacoes=movimentacoes,
            filtro_movimento=movimento,
            filtro_data_inicio=data_inicio,
            filtro_data_fim=data_fim,
            pagination=pagination
        )



# ---------- Execução ----------
app = create_app()

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8020)
