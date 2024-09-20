from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from comunidadeinteligente import app, database, bcrypt
from comunidadeinteligente.forms import FormLogin, FormCriarConta, FormEditarPerfil, FormCriarPost
from comunidadeinteligente.models import Usuario, Post
from flask_login import login_user, logout_user, current_user, login_required
import secrets
import os
from PIL import Image

# Página inicial (GET)
@app.route('/', methods=['GET'])
def home():
    posts = Post.query.order_by(Post.id.desc())
    return render_template('home.html', posts=posts)

# Página de contato (GET)
@app.route('/contato', methods=['GET'])
def contato():
    return render_template('contato.html')

# Página de usuários (GET) - Requer login
@app.route('/usuarios', methods=['GET'])
@login_required
def usuarios():
    lista_usuarios = Usuario.query.all()
    return render_template('usuarios.html', lista_usuarios=lista_usuarios)

# Login (GET e POST) - Alteração feita
@app.route('/login', methods=['GET', 'POST'])
def login():
    form_login = FormLogin()
    form_criarconta = FormCriarConta()
    if form_login.validate_on_submit() and 'botao_submit_login' in request.form:
        usuario = Usuario.query.filter_by(email=form_login.email.data).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form_login.senha.data):
            login_user(usuario, remember=form_login.lembrar_dados.data)
            flash(f'Login feito com sucesso no e-mail: {form_login.email.data}', 'alert-success')
            par_next = request.args.get('next')
            return redirect(par_next) if par_next else redirect(url_for('home'))
        else:
            flash(f'Falha no Login. E-mail ou Senha Incorretos', 'alert-danger')
    if form_criarconta.validate_on_submit() and 'botao_submit_criarconta' in request.form:
        senha_cript = bcrypt.generate_password_hash(form_criarconta.senha.data)
        usuario = Usuario(
            username=form_criarconta.username.data,
            email=form_criarconta.email.data,
            senha=senha_cript,
            cep=form_criarconta.cep.data,  # CEP e endereço adicionados
            endereco=form_criarconta.endereco.data
        )
        database.session.add(usuario)
        database.session.commit()
        flash(f'Conta criada para o e-mail: {form_criarconta.email.data}', 'alert-success')
        return redirect(url_for('home'))
    return render_template('login.html', form_login=form_login, form_criarconta=form_criarconta)

# Logout (GET) - Requer login
@app.route('/sair', methods=['GET'])
@login_required
def sair():
    logout_user()
    flash(f'Logout Feito com Sucesso', 'alert-success')
    return redirect(url_for('home'))

# Exibir perfil (GET) - Requer login
@app.route('/perfil', methods=['GET'])
@login_required
def perfil():
    foto_perfil = url_for('static', filename='fotos_perfil/{}'.format(current_user.foto_perfil))
    return render_template('perfil.html', foto_perfil=foto_perfil)

# Criar post (GET e POST) - Requer login
@app.route('/post/criar', methods=['GET', 'POST'])
@login_required
def criar_post():
    form = FormCriarPost()
    if form.validate_on_submit():
        post = Post(titulo=form.titulo.data, corpo=form.corpo.data, autor=current_user)
        database.session.add(post)
        database.session.commit()
        flash('Post Criado com Sucesso', 'alert-success')
        return redirect(url_for('home'))
    return render_template('criarpost.html', form=form)

# Atualizar post (PUT) - Requer login
@app.route('/post/<int:post_id>', methods=['GET', 'PUT'])
@login_required
def exibir_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user == post.autor:
        form = FormCriarPost()
        if request.method == 'GET':
            form.titulo.data = post.titulo
            form.corpo.data = post.corpo
        elif request.method == 'PUT' and form.validate_on_submit():
            post.titulo = form.titulo.data
            post.corpo = form.corpo.data
            database.session.commit()
            flash('Post Atualizado com Sucesso', 'alert-success')
            return redirect(url_for('home'))
    else:
        abort(403)
    return render_template('post.html', post=post, form=form)

# Deletar post (DELETE e POST) - Requer login
@app.route('/post/<int:post_id>/excluir', methods=['POST', 'DELETE'])
@login_required
def excluir_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user == post.autor:
        database.session.delete(post)
        database.session.commit()
        flash('Post Excluído com Sucesso', 'alert-success')  # Mostra mensagem de sucesso
        return redirect(url_for('home'))  # Redireciona para a página inicial
    else:
        abort(403)



# Editar perfil (GET e POST) - Requer login
@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    form = FormEditarPerfil()
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.username = form.username.data
        if form.foto_perfil.data:
            nome_imagem = salvar_imagem(form.foto_perfil.data)
            current_user.foto_perfil = nome_imagem
        current_user.cursos = atualizar_cursos(form)
        database.session.commit()
        flash('Perfil atualizado com Sucesso', 'alert-success')
        return redirect(url_for('perfil'))
    elif request.method == "GET":
        form.email.data = current_user.email
        form.username.data = current_user.username
    foto_perfil = url_for('static', filename='fotos_perfil/{}'.format(current_user.foto_perfil))
    return render_template('editarperfil.html', foto_perfil=foto_perfil, form=form)

# Função auxiliar para salvar imagens
def salvar_imagem(imagem):
    codigo = secrets.token_hex(8)
    nome, extensao = os.path.splitext(imagem.filename)
    nome_arquivo = nome + codigo + extensao
    caminho_completo = os.path.join(app.root_path, 'static/fotos_perfil', nome_arquivo)
    tamanho = (400, 400)
    imagem_reduzida = Image.open(imagem)
    imagem_reduzida.thumbnail(tamanho)
    imagem_reduzida.save(caminho_completo)
    return nome_arquivo

# Função auxiliar para atualizar cursos
def atualizar_cursos(form):
    lista_cursos = []
    for campo in form:
        if 'curso_' in campo.name and campo.data:
            lista_cursos.append(campo.label.text)
    return ';'.join(lista_cursos)


