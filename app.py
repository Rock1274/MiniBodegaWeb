from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import pyodbc
import base64
from functools import wraps
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import secrets
from flask_cors import CORS
from bs4 import BeautifulSoup
import time

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_1234'

# Configuración para desarrollo - deshabilitar cache
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

CORS(app)  # Permite todas las solicitudes; ajusta para producción

# Configuración para subida de archivos
UPLOAD_FOLDER = os.path.join('static', 'Paquetes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurar que el directorio existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def archivo_permitido(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_filename(name):
    import re
    # Replace invalid characters with _
    invalid_chars = r'[<>:"|?*\x00-\x1f]'
    name = re.sub(invalid_chars, '_', name)
    # Also replace / and \ with _
    name = name.replace('/', '_').replace('\\', '_')
    return name

def limpiar_imagenes_huerfanas():
    """Elimina imágenes huérfanas que no corresponden a ningún producto activo"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Descripcion FROM Paquete WHERE Papelera = 0')
        descripciones_activas = {row[0] for row in cursor.fetchall()}
        conn.close()

        archivos_esperados = {sanitize_filename(desc) + '.png' for desc in descripciones_activas}
        archivos_en_carpeta = set(os.listdir(app.config['UPLOAD_FOLDER']))

        for archivo in archivos_en_carpeta:
            if archivo.endswith('.png') and archivo != 'PorDefecto.webp' and archivo not in archivos_esperados:
                ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                try:
                    os.remove(ruta_archivo)
                    print(f"Imagen huérfana eliminada: {archivo}")
                except OSError as e:
                    print(f"Error al eliminar {archivo}: {e}")
    except Exception as e:
        print(f"Error en limpieza de imágenes huérfanas: {e}")

# Agregar filtro Jinja para sanitizar nombres de archivo
app.jinja_env.filters['sanitize'] = sanitize_filename

def is_ajax_request():
    """Detecta si la petición es AJAX desde nuestro sistema de navegación"""
    return request.headers.get('X-Custom-Ajax-Navigation') == 'true'

def render_template_ajax(template, **kwargs):
    if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
        # Devolver JSON con content y modals para AJAX
        rendered = render_template(template, **kwargs)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = rendered
        modals = soup.find(attrs={'data-modals': True})

        response_data = {
            'content': content,
            'modals': modals.prettify() if modals else ''
        }
        # Incluir kwargs adicionales en la respuesta JSON
        response_data.update(kwargs)
        response = jsonify(response_data)
        # Agregar headers estrictos para evitar cache en respuestas AJAX
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    response = make_response(render_template(template, **kwargs))
    # Agregar headers para evitar cache en respuestas HTML también
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Expires'] = '0'
    response.headers['Surrogate-Control'] = 'no-store'
    return response

def get_db_connection():
    server = os.environ.get("AZURE_SQL_SERVER")
    database = os.environ.get("AZURE_SQL_DB")
    username = os.environ.get("AZURE_SQL_USER")
    password = os.environ.get("AZURE_SQL_PASS")

    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(conn_str)

def verificar_sesion_recordada():
    """Verifica si hay una cookie de sesión recordada y restaura la sesión"""
    if 'usuario' not in session:
        # Verificar cookie de sesión recordada
        cookie_usuario = request.cookies.get('recuerdame_usuario')
        cookie_tipo = request.cookies.get('recuerdame_tipo')
        cookie_user_id = request.cookies.get('recuerdame_user_id')

        if cookie_usuario and cookie_tipo and cookie_user_id:
            # Verificar que el usuario aún existe en la base de datos
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT Id_Usuario, NUsuario, Tipo FROM Usuario WHERE NUsuario = ?', (cookie_usuario,))                
                user_verificado = cursor.fetchone()
                conn.close()

                if user_verificado:
                    # CORRECCIÓN: Usar los valores correctos de la BD en lugar de las cookies
                    session['usuario'] = user_verificado[1]  # NUsuario de BD
                    session['tipo'] = user_verificado[2]     # Tipo de BD
                    session['user_id'] = user_verificado[0]  # Id_Usuario de BD
                    print(f"Sesion restaurada automaticamente para usuario: {user_verificado[1]}")
                else:
                    # Usuario no válido, eliminar cookies
                    print("⚠️ Cookies inválidas detectadas, eliminando...")
                    # Las cookies se eliminarán automáticamente al expirar
            except Exception as e:
                print(f"Error al verificar usuario en cookies: {e}")

@app.before_request
def before_request():
    """Se ejecuta antes de cada petición para verificar sesión recordada"""
    # Solo verificar en rutas que no sean login, logout o archivos estáticos
    if request.endpoint and not request.endpoint.startswith(('login', 'logout', 'static')):
        verificar_sesion_recordada()

def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar sesión recordada antes de requerir login
        verificar_sesion_recordada()

        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def calcular_edad(fecha_nacimiento): 
    if not fecha_nacimiento:
        return ''
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = fecha_nacimiento.split(' ')[0]  # Por si viene con hora
        fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d')
    hoy = datetime.today()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return edad

def manejar_imagen_producto(descripcion, imagen=None):
    """
    Maneja la imagen de un producto. Si se proporciona una imagen, la guarda.
    Si no hay imagen y no existe una para el producto, copia la imagen por defecto.
    """
    nombre_archivo = f"{sanitize_filename(descripcion)}.png"
    ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    
    if imagen and imagen.filename != '':
        # Validar formato de archivo
        if not archivo_permitido(imagen.filename):
            raise ValueError('Formato de imagen no permitido. Usa: .png, .jpg, .jpeg, .gif o .webp')

        # Guardar la imagen subida
        try:
            imagen.save(ruta_imagen)
        except Exception as e:
            raise ValueError(f'Error al guardar la imagen: {str(e)}')
    else:
        # Si no hay imagen subida y no existe una para el producto, copiar por defecto
        if not os.path.exists(ruta_imagen):
            ruta_por_defecto = os.path.join(app.config['UPLOAD_FOLDER'], 'PorDefecto.webp')
            if os.path.exists(ruta_por_defecto):
                import shutil
                shutil.copy2(ruta_por_defecto, ruta_imagen)
    
    return nombre_archivo

def validar_email(email):
    """Valida el formato de un email usando regex"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def enviar_email_gmail(destinatario, codigo):
    """Envía un email con el código de verificación usando Gmail"""
    remitente = 'soportedebodega.cocacola@gmail.com'  # Email de soporte
    password = 'haan gkbx pchr zlvs'  # Reemplazar con el App Password de soportedebodega.cocacola@gmail.com

    if remitente == 'tu_email@gmail.com':
        print("Error: Configura las credenciales de Gmail en la función enviar_email_gmail")
        return False

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = 'Código de Verificación para Recuperar Contraseña'

    cuerpo = f'''
    Hola,

    Has solicitado recuperar tu contraseña en el sistema de MiniBodega CocaCola.

    Tu código de verificación es: {codigo}

    Este código expira en 10 minutos. Si no solicitaste este cambio, ignora este email.

    Saludos,
    Equipo de Soporte CocaCola
    soporte.cocacola@gmail.com
    '''
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        text = msg.as_string()
        server.sendmail(remitente, destinatario, text)
        server.quit()
        print(f"Email enviado a {destinatario}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Error de autenticación: {e}. Verifica el email y App Password.")
        return False
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False

#Login con funcionalidad de "Recuérdame"
# ====================================
# Esta función maneja el login y la creación de cookies persistentes
# cuando el usuario marca el checkbox "recuérdame".
#
# Funcionamiento:
# 1. Si el usuario marca "recuérdame", se crean cookies que duran 30 días
# 2. Las cookies contienen: usuario, tipo y user_id
# 3. Antes de cada petición, se verifica si hay cookies válidas
# 4. Si hay cookies válidas, se restaura la sesión automáticamente
# 5. Al hacer logout, se eliminan las cookies
#
# Seguridad:
# - Las cookies tienen httponly=True para prevenir acceso desde JavaScript
# - Se verifica que el usuario aún existe en la BD antes de restaurar sesión
# - Las cookies expiran automáticamente después de 30 días
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verificar si ya hay una sesión recordada
    verificar_sesion_recordada()

    # Si ya hay sesión activa, redirigir al index
    if 'usuario' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nusuario = request.form['nusuario']
        contrasena = request.form['contrasena']
        recuerdame = request.form.get('recuerdame')  # Checkbox "recuérdame"
        contrasena_codificada = base64.b64encode(contrasena.encode('utf-16le')).decode()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Usuario WHERE NUsuario = ? AND Contraseña = ?', (nusuario, contrasena_codificada))
        print(f"Usuario: {nusuario}, Contraseña: {contrasena_codificada}")
        user = cursor.fetchone()
        conn.close()

        if user:
            # Crear sesión normal - CORREGIDOS LOS ÍNDICES SEGÚN ESTRUCTURA DE TABLA
            session['usuario'] = user[2]  # NUsuario (índice 2)
            session['tipo'] = user[5]     # Tipo (índice 5)
            session['user_id'] = user[0]  # Id_Usuario (índice 0)

            # Si se marcó "recuérdame", crear cookies persistentes
            if recuerdame:
                # Crear respuesta con cookies
                resp = make_response(redirect(url_for('index')))

                # Cookies que duran 30 días
                expires = datetime.now() + timedelta(days=30)

                # CORREGIDOS LOS ÍNDICES PARA LAS COOKIES
                resp.set_cookie('recuerdame_usuario', user[2], expires=expires, httponly=True, secure=False)  # NUsuario
                resp.set_cookie('recuerdame_tipo', user[5], expires=expires, httponly=True, secure=False)    # Tipo
                resp.set_cookie('recuerdame_user_id', str(user[0]), expires=expires, httponly=True, secure=False)  # Id_Usuario

                print(f"Cookies de 'recordame' creadas para usuario: {user[2]}")
                return resp
            else:
                # Sin cookies, solo sesión normal
                return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')
    return render_template('Login/login.html')

@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        email = request.form['email'].strip()
        flash(f'Email ingresado: {email}', 'info')
        if not validar_email(email):
            flash('Formato de email inválido.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Email FROM Usuario WHERE Email = ?', (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            flash('Email no registrado.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        # Generar código de 6 dígitos
        codigo = ''.join(secrets.choice('0123456789') for _ in range(6))
        expiry = datetime.now() + timedelta(minutes=10)
        """ flash(f'Debug: Código generado: {codigo}', 'info') """

        # Guardar en BD (asumiendo tabla ResetTokens)
        try:
            cursor.execute('INSERT INTO ResetTokens (Email, Token, Expiry) VALUES (?, ?, ?)', (email, codigo, expiry))
            conn.commit()
        except Exception as e:
            conn.close()
            flash(f'Error al guardar en BD: {str(e)}', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        # Enviar email
        if enviar_email_gmail(email, codigo):
            session['reset_email'] = email

            cursor.execute('SELECT NombreCompleto FROM Usuario WHERE Email = ?', (email,))
            usuario = cursor.fetchone()
            usuario_nombre = usuario[0] if usuario else 'Usuario'
            conn.close()
            flash(f'Código de verificación enviado a tu email, {usuario_nombre}', 'success')
            return redirect(url_for('verificar_codigo'))
        else:
            conn.close()
            flash('Error al enviar el email. Verifica credenciales de Gmail.', 'danger')

    return render_template('Login/recuperar_contrasena.html')

@app.route('/verificar_codigo', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        email = session.get('reset_email')
        if not email:
            flash('Sesión expirada. Intenta de nuevo.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Token, Expiry FROM ResetTokens WHERE Email = ? ORDER BY Expiry DESC', (email,))
        token_data = cursor.fetchone()
        conn.close()

        if not token_data or token_data[0] != codigo or datetime.now() > token_data[1]:
            flash('Código inválido o expirado.', 'danger')
            return redirect(url_for('verificar_codigo'))

        session['reset_verified'] = True
        flash('Código verificado. Ingresa tu nueva contraseña.', 'success')
        return redirect(url_for('reset_contrasena'))

    # Para GET, verificar si hay email en sesión
    if not session.get('reset_email'):
        flash('Sesión expirada. Intenta de nuevo.', 'danger')
        return redirect(url_for('recuperar_contrasena'))

    return render_template('Login/verificar_codigo.html')

@app.route('/reset_contrasena', methods=['GET', 'POST'])
def reset_contrasena():
    if not session.get('reset_verified'):
        flash('Sesión expirada. Intenta de nuevo.', 'danger')
        return redirect(url_for('recuperar_contrasena'))

    if request.method == 'POST':
        nueva_contrasena = request.form['nueva_contrasena']
        confirmar_contrasena = request.form['confirmar_contrasena']

        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('reset_contrasena'))

        email = session.get('reset_email')
        contrasena_codificada = base64.b64encode(nueva_contrasena.encode('utf-16le')).decode()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Usuario SET Contraseña = ? WHERE Email = ?', (contrasena_codificada, email))
        conn.commit()
        conn.close()

        # Limpiar sesión
        session.pop('reset_email', None)
        session.pop('reset_verified', None)

        flash('Contraseña actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('Login/reset_contrasena.html')

# Ruta: Logout
@app.route('/logout')
def logout():
    session.clear()

    # Crear respuesta que elimina las cookies de "recuérdame"
    resp = make_response(redirect(url_for('login')))

    # Eliminar cookies configurándolas con fecha de expiración pasada
    resp.set_cookie('recuerdame_usuario', '', expires=0)
    resp.set_cookie('recuerdame_tipo', '', expires=0)
    resp.set_cookie('recuerdame_user_id', '', expires=0)

    print("Sesion cerrada y cookies de 'recordame' eliminadas")
    return resp

# Ruta: Página principal con bienvenida
@app.route('/')
@login_requerido
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener productos con inventario bajo (ejemplo: menos de 10 unidades)
    cursor.execute('''
        SELECT Descripcion, Inventario
        FROM Paquete
        WHERE Inventario < 30
        ORDER BY Inventario ASC
    ''')
    alertas_stock = cursor.fetchall()

    # Obtener lista de ventas recientes
    cursor.execute('''
        SELECT Id_Venta, Fecha, TotalVenta
        FROM Venta
        WHERE Papelera = 0
        ORDER BY Fecha ASC
    ''')
    ventas = cursor.fetchall()

    cursor.execute('SELECT Id_Paquete, Descripcion, PaquetesCompletos, ' \
    'UnidadesSobrantes, Inventario, TipoPaquete FROM Paquete WHERE Papelera = 0')
    paquetes = cursor.fetchall()

    conn.close()

    if is_ajax_request():
        rendered = render_template('bienvenida.html', alertas_stock=alertas_stock, paquetes=paquetes, ventas=ventas)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template('bienvenida.html', alertas_stock=alertas_stock, paquetes=paquetes, ventas=ventas)



# Paquetes
@app.route('/paquetes', methods=['GET', 'POST'])
@login_requerido
def ver_paquetes():
    busqueda = request.args.get('busqueda', '').strip()
    filtro = request.args.get('Filtros', 'Nombre')  # 'Nombre' por defecto
    page = request.args.get('page', 1, type=int)
    limit = 12
    offset = (page - 1) * limit
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener total de paquetes para paginación
    if busqueda:
        if filtro == 'Nombre':
            cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Descripcion LIKE ? AND Papelera = 0', (f'%{busqueda}%',))
        elif filtro == 'Inventario':
            try:
                if busqueda.startswith('='):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Inventario = ? AND Papelera = 0', (valor,))
                elif busqueda.startswith('>'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Inventario > ? AND Papelera = 0', (valor,))
                elif busqueda.startswith('<'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Inventario < ? AND Papelera = 0', (valor,))
                elif '-' in busqueda:
                    min_val, max_val = map(int, busqueda.split('-'))
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Inventario BETWEEN ? AND ? AND Papelera = 0', (min_val, max_val))
                else:
                    valor = float(busqueda)
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Inventario BETWEEN ? AND (? + 5) AND Papelera = 0', (valor, valor))
            except ValueError:
                total = 0
                paquetes = []
        elif filtro == 'TipoPaquete':
            cursor.execute('SELECT COUNT(*) FROM Paquete WHERE TipoPaquete LIKE ? AND Papelera = 0', (f'%{busqueda}%',))
        else:
            cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Papelera = 0')
    else:
        cursor.execute('SELECT COUNT(*) FROM Paquete WHERE Papelera = 0')

    total_result = cursor.fetchone()
    total = total_result[0] if total_result else 0
    total_pages = (total + limit - 1) // limit

    # Buscar paquetes con paginación
    if busqueda:
        if filtro == 'Nombre':
            cursor.execute('''
                SELECT *
                FROM Paquete
                WHERE Descripcion LIKE ? AND Papelera = 0
                ORDER BY Id_Paquete DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            ''', (f'%{busqueda}%', offset, limit))
        elif filtro == 'Inventario':
            try:
                if busqueda.startswith('='):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE Inventario = ? AND Papelera = 0 ORDER BY Id_Paquete DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (valor, offset, limit))
                elif busqueda.startswith('>'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE Inventario > ? AND Papelera = 0 ORDER BY Id_Paquete DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (valor, offset, limit))
                elif busqueda.startswith('<'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE Inventario < ? AND Papelera = 0 ORDER BY Id_Paquete DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (valor, offset, limit))
                elif '-' in busqueda:
                    min_val, max_val = map(int, busqueda.split('-'))
                    cursor.execute('SELECT * FROM Paquete WHERE Inventario BETWEEN ? AND ? AND Papelera = 0 ORDER BY Id_Paquete DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (min_val, max_val, offset, limit))
                else:
                    valor = float(busqueda)
                    cursor.execute('SELECT * FROM Paquete WHERE Inventario BETWEEN ? AND (? + 5) AND Papelera = 0 ORDER BY Id_Paquete DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (valor, valor, offset, limit))
            except ValueError:
                paquetes = []
        elif filtro == 'TipoPaquete':
            cursor.execute('''
                SELECT *
                FROM Paquete
                WHERE TipoPaquete LIKE ? AND Papelera = 0
                ORDER BY Id_Paquete DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            ''', (f'%{busqueda}%', offset, limit))
        else:
            cursor.execute('''
                SELECT *
                FROM Paquete
                WHERE Papelera = 0
                ORDER BY Id_Paquete DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            ''', (offset, limit))
    else:
        cursor.execute('''
            SELECT *
            FROM Paquete
            WHERE Papelera = 0
            ORDER BY Id_Paquete DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        ''', (offset, limit))

    paquetes = cursor.fetchall()

    # Crear paquete (si POST)
    if request.method == 'POST':
        descripcion = request.form['Descripcion']
        tipo = int(request.form['TipoPaquete'])
        inventario = 0
        unidadessobrantes = int(request.form['UnidadesSobrantes']) if request.form['UnidadesSobrantes'] else 0
        paquetescompletos = int(request.form['PaquetesCompletos']) if request.form['PaquetesCompletos'] else 0
        precio_venta = request.form['PrecioVenta_Paq']
        precio_compra = request.form['PrecioCompra_Paq']

        # Validar que las unidades sobrantes no excedan el tipo de paquete
        if unidadessobrantes > tipo:
            flash(f'❌ Las unidades sobrantes ({unidadessobrantes}) no pueden ser mayores que el tipo de paquete ({tipo})', 'danger')
            return redirect(url_for('ver_paquetes'))

        # Manejo de imagen
        imagen = request.files.get('imagen')
        try:
            nombre_archivo = manejar_imagen_producto(descripcion, imagen)
        except ValueError as e:
            flash(f'❌ {str(e)}', 'danger')
            return redirect(url_for('ver_paquetes'))

        # Inserción en la BD (NO incluye imagen, como pediste)
        cursor.execute('''
            INSERT INTO Paquete (Descripcion, TipoPaquete, Inventario, UnidadesSobrantes, PaquetesCompletos, PrecioVenta_Paq, PrecioCompra_Paq)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (descripcion, tipo, inventario, unidadessobrantes, paquetescompletos, precio_venta, precio_compra))

        conn.commit()
        conn.close()

        # Limpiar imágenes huérfanas después de crear el producto
        limpiar_imagenes_huerfanas()
        return redirect(url_for('ver_paquetes'))

    archivos_disponibles = set(os.listdir(app.config['UPLOAD_FOLDER']))
    conn.close()

    # Timestamp para evitar cache de imágenes
    timestamp = int(time.time())

    if is_ajax_request():
        rendered = render_template(
            'Productos/paquetes.html',
            paquetes=paquetes,
            busqueda=busqueda,
            lookup_files=archivos_disponibles,
            filtro=filtro,
            timestamp=timestamp,
            page=page,
            total_pages=total_pages
        )
        soup = BeautifulSoup(rendered, 'html.parser')
        content = rendered
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content,
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template(
            'Productos/paquetes.html',
            paquetes=paquetes,
            busqueda=busqueda,
            lookup_files=archivos_disponibles,
            filtro=filtro,
            timestamp=timestamp,
            page=page,
            total_pages=total_pages
        )

#Edicion de paquetes
@app.route('/editar_paquete/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_paquete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        descripcion = request.form['Descripcion']
        tipo = int(request.form['TipoPaquete'])
        inventario = 0
        unidadessobrantes = int(request.form['UnidadesSobrantes']) if request.form['UnidadesSobrantes'] else 0
        paquetescompletos = int(request.form['PaquetesCompletos']) if request.form['PaquetesCompletos'] else 0
        precio_venta = request.form['PrecioVenta_Paq']
        precio_compra = request.form['PrecioCompra_Paq']
        imagen = request.files.get('imagen')

        if unidadessobrantes > tipo:
            flash(f'❌ Las unidades sobrantes ({unidadessobrantes}) no pueden ser mayores que el tipo de paquete ({tipo})', 'danger')

            # 🚀 Si es AJAX, devolvemos JSON (NO redirect)
            if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
                return jsonify({"redirect": url_for('editar_paquete', id=id)})

            return redirect(url_for('editar_paquete', id=id))

        # Obtener descripción anterior para comparar
        cursor.execute('SELECT Descripcion FROM Paquete WHERE Id_Paquete = ? AND Papelera = 0', (id,))
        paquete_anterior = cursor.fetchone()
        descripcion_anterior = paquete_anterior[0] if paquete_anterior else None

        # Eliminar la imagen anterior si hay nueva imagen
        if imagen and imagen.filename != '':
            if descripcion_anterior:
                ruta_anterior = os.path.join(app.config['UPLOAD_FOLDER'], f"{sanitize_filename(descripcion_anterior)}.png")
                if os.path.exists(ruta_anterior):
                    try:
                        os.remove(ruta_anterior)
                    except Exception as e:
                        print(f"Error al eliminar imagen anterior: {e}")

        # Manejar renombrado de imagen si la descripción cambió
        if descripcion_anterior and descripcion_anterior != descripcion:
            nombre_archivo_anterior = f"{sanitize_filename(descripcion_anterior)}.png"
            ruta_anterior = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_anterior)

            nombre_archivo_nuevo = f"{sanitize_filename(descripcion)}.png"
            ruta_nueva = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_nuevo)

            # Si no hay nueva imagen, renombrar la existente
            if not (imagen and imagen.filename != ''):
                if os.path.exists(ruta_anterior) and not os.path.exists(ruta_nueva):
                    os.rename(ruta_anterior, ruta_nueva)

        try:
            nombre_archivo = manejar_imagen_producto(descripcion, imagen)
        except ValueError as e:
            flash(f'❌ {str(e)}', 'danger')

            if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
                return jsonify({"redirect": url_for('editar_paquete', id=id)})

            return redirect(url_for('editar_paquete', id=id))

        cursor.execute('''
            UPDATE Paquete
            SET Descripcion = ?, TipoPaquete = ?, Inventario = ?, UnidadesSobrantes = ?, PaquetesCompletos = ?, PrecioVenta_Paq = ?, PrecioCompra_Paq = ?
            WHERE Id_Paquete = ?
        ''', (descripcion, tipo, inventario, unidadessobrantes, paquetescompletos, precio_venta, precio_compra, id))

        conn.commit()
        conn.close()

        # Limpiar imágenes huérfanas después de editar el producto
        limpiar_imagenes_huerfanas()

        # 🚀 Si es AJAX, regresamos JSON limpio → JS hace navigateTo()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"redirect": url_for('ver_paquetes')})

        return redirect(url_for('ver_paquetes'))


    # Obtener paquetes para el combo
    cursor.execute('SELECT * FROM Paquete WHERE Id_Paquete = ? AND Papelera = 0', (id,))
    paquete = cursor.fetchone() 

    # Obtener lista de archivos disponibles
    archivos_disponibles = set(os.listdir(app.config['UPLOAD_FOLDER']))

    conn.close()

    # Timestamp para evitar cache de imágenes
    timestamp = int(time.time())

    if is_ajax_request():
        rendered = render_template('Productos/editar_paquetes.html', paquete=paquete, archivos_disponibles=archivos_disponibles, timestamp=timestamp)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template('Productos/editar_paquetes.html', paquete=paquete, archivos_disponibles=archivos_disponibles, timestamp=timestamp)



#Detalle Venta
@app.route('/detalles_ventas', methods=['GET', 'POST'])
@login_requerido
def ver_detalles_ventas():
    producto = request.args.get('producto', '').strip()
    id_venta = request.args.get('id_venta', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    error = None

    # Buscar detalles de ventas (por nombre de paquete si hay búsqueda)
    if producto:
        cursor.execute('''
            SELECT 
                dv.Id_DetalleVenta,
                dv.Id_Venta,
                p.Descripcion AS DescripcionPaquete,
                dv.CantidadPaquetes,
                dv.CantidadUnidades,
                dv.CantidadVendidaTotal,
                dv.PrecioUnitario,
                dv.Subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.Id_Paquete = p.Id_Paquete
            WHERE p.Descripcion LIKE ? AND dv.Papelera = 0
            ORDER BY dv.Id_Venta ASC
        ''', (f'%{producto}%',))
    elif id_venta:
        cursor.execute('''
            SELECT 
                dv.Id_DetalleVenta,
                dv.Id_Venta,
                p.Descripcion AS DescripcionPaquete,
                dv.CantidadPaquetes,
                dv.CantidadUnidades,
                dv.CantidadVendidaTotal,
                dv.PrecioUnitario,
                dv.Subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.Id_Paquete = p.Id_Paquete
            WHERE dv.Id_Venta LIKE ? AND dv.Papelera = 0
            ORDER BY dv.Id_Venta ASC
        ''', (f'%{id_venta}%',))
    else:
        cursor.execute('''
            SELECT 
                dv.Id_DetalleVenta,
                dv.Id_Venta,
                p.Descripcion AS DescripcionPaquete,
                dv.CantidadPaquetes,
                dv.CantidadUnidades,
                dv.CantidadVendidaTotal,
                dv.PrecioUnitario,
                dv.Subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.Id_Paquete = p.Id_Paquete
            WHERE dv.Papelera = 0
            ORDER BY dv.Id_Venta ASC
        ''')
    detalles_ventas = cursor.fetchall()


    # Agregar Detalle Venta
    if request.method == 'POST':
        is_htmx = request.headers.get('HX-Request')
        print(f"HTMX Request: {is_htmx}")
        try:
            id_venta = int(request.form['dv_id_venta'])
            id_paquete = int(request.form['dv_paquete_id'])
            paquetes_finales = int(request.form['dv_paquetes_finales'])
            unidades_finales = int(request.form['dv_unidades_finales'])

            # Obtener inventario actual del paquete
            cursor.execute('SELECT Inventario, TipoPaquete, PrecioVenta_Paq, Descripcion FROM Paquete WHERE Id_Paquete = ?', (id_paquete,))
            paquete = cursor.fetchone()
            if not paquete:
                raise ValueError('Paquete no encontrado')
            inventario_actual = paquete[0]
            tipo_paquete = paquete[1]
            precio_paquete = paquete[2]
            descripcion_paquete = paquete[3]


            cursor.execute('''
                INSERT INTO DetalleVenta (Id_Paquete, CantidadPaquetes, CantidadUnidades, Id_Venta)
                VALUES (?, ?, ?, ?)
            ''', (id_paquete, paquetes_finales, unidades_finales, id_venta))

            conn.commit()

            cursor.execute(
                '''
                SELECT TOP 1 
                    CantidadVendidaTotal,
                    PrecioUnitario,
                    Subtotal,
                    CantidadPaquetes,
                    CantidadUnidades,
                    Id_DetalleVenta
                FROM DetalleVenta
                WHERE Papelera = 0
                ORDER BY Id_DetalleVenta DESC;
            '''
            )
            detalle_insertado = cursor.fetchone()

            cantidad_vendida_total = detalle_insertado[0]
            precio_unitario = detalle_insertado[1]
            subtotal = detalle_insertado[2]
            cantidad_paquetes = detalle_insertado[3]
            cantidad_unidades = detalle_insertado[4]
            id = detalle_insertado[5]


            # Calcular cantidad vendida total, precio unitario y subtotal
            if is_htmx:
                # Devolver HTML de la nueva fila
                nueva_fila_html = f'''
                <tr>
                    <td class="text-center">{id_venta}</td>
                    <td>{descripcion_paquete}</td>
                    <td class="text-center">{cantidad_paquetes}</td>
                    <td class="text-center">{cantidad_unidades}</td>
                    <td class="text-center">{cantidad_vendida_total:.2f}</td>
                    <td class="text-end">C${precio_unitario:.2f}</td>
                    <td class="text-end">C${subtotal:.2f}</td>
                    <td class="text-center">
                        <a href="/editar_detalle_venta/{id}" class="btn btn-sm btn-warning">Editar</a>
                    </td>
                </tr>
                '''
                return nueva_fila_html
            else:
                flash('Detalle de venta registrado correctamente.', 'success')
                conn.close()
                return redirect(url_for('ver_detalles_ventas'))

        except ValueError as e:
            error = str(e)
            if is_htmx:
                return f'<div class="alert alert-danger">{error}</div>'
        except pyodbc.Error as e:
            error = f'Error de base de datos: {str(e)}'
            if is_htmx:
                return f'<div class="alert alert-danger">{error}</div>'


    # Cargar combos: Paquetes y ventas
    cursor.execute('SELECT Id_Paquete, Descripcion, PaquetesCompletos, UnidadesSobrantes, Inventario, TipoPaquete FROM Paquete WHERE Papelera = 0')
    paquetes = cursor.fetchall()

    cursor.execute('SELECT MAX(Id_Venta) FROM Venta WHERE Papelera = 0')
    max_id_venta_result = cursor.fetchone()
    max_id_venta = max_id_venta_result[0] if max_id_venta_result and max_id_venta_result[0] is not None else 1

    cursor.execute('SELECT Id_Venta, Fecha, TotalVenta FROM Venta WHERE Papelera = 0 ORDER BY Fecha ASC')
    ventas = cursor.fetchall()

    tiene_detalles = len(detalles_ventas) > 0
    conn.close()

    if is_ajax_request():
        rendered = render_template(
            'Ventas/detalles_ventas.html',
            detalles_ventas=detalles_ventas,
            producto=producto,
            id_venta=id_venta,
            paquetes=paquetes,
            ventas=ventas,
            max_id_venta=max_id_venta,
            error=error,
            tiene_detalles=tiene_detalles
        )
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template(
            'Ventas/detalles_ventas.html',
            detalles_ventas=detalles_ventas,
            producto=producto,
            id_venta=id_venta,
            paquetes=paquetes,
            ventas=ventas,
            max_id_venta=max_id_venta,
            error=error,
            tiene_detalles=tiene_detalles
        )



@app.route('/crear_venta', methods=['POST'])
@login_requerido
def crear_venta():
    is_htmx = request.headers.get('HX-Request')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT INTO Venta DEFAULT VALUES;')
        cursor.execute('SELECT Top 1 Id_Venta from Venta order by Id_Venta desc')
        nueva_venta_result = cursor.fetchone()
        nueva_venta_id = int(nueva_venta_result[0]) if nueva_venta_result and nueva_venta_result[0] is not None else 1

        # Obtener la venta insertada para la fila
        cursor.execute('SELECT Id_Venta, Fecha, TotalVenta FROM Venta WHERE Id_Venta = ?', (nueva_venta_id,))
        venta = cursor.fetchone()

        conn.commit()

        if is_htmx:
            # Devolver HTML de la nueva fila para la tabla en ver_ventas.html
            fecha = venta[1].strftime('%Y-%m-%d') if venta[1] else 'N/A'
            total_venta = f"C${venta[2]:.2f}" if venta[2] else 'C$0.00'
            nueva_fila_html = f'''
            <tr class="text-center">
                <td>{venta[0]}</td>
                <td>{fecha}</td>
                <td>{total_venta}</td>
            </tr>
            '''
            return nueva_fila_html
        else:
            flash(f'Venta creada exitosamente. ID: {nueva_venta_id}', 'success')
            return redirect(url_for('ver_detalles_ventas'))

    except Exception as e:
        conn.rollback()
        if is_htmx:
            return f'<div class="alert alert-danger">Error al crear la venta: {str(e)}</div>'
        else:
            flash(f'Ocurrió un error al crear la venta: {str(e)}', 'danger')
            return redirect(url_for('ver_detalles_ventas'))

    finally:
        cursor.close()
        conn.close()



@app.route('/editar_detalle_venta/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_detalle_venta(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT
                    dv.Id_DetalleVenta,
                    dv.Id_Paquete,
                    dv.Id_Venta,
                    p.TipoPaquete AS TipoPaquete,
                    p.PaquetesCompletos AS PaquetesCompletos,
                    p.UnidadesSobrantes AS UnidadesSobrantes,
                    p.Inventario AS Inventario,
                    p.Descripcion AS Descripcion,
                    dv.CantidadPaquetes,
                    dv.CantidadUnidades
                    FROM DetalleVenta dv
                    inner join Paquete p on dv.Id_Paquete = p.Id_Paquete
                    WHERE Id_DetalleVenta = ? AND dv.Papelera = 0''', (id,))
    detalle = cursor.fetchone()

    # Convertir detalle a dict para serialización JSON
    if detalle:
        detalle = dict(zip([col[0] for col in cursor.description], detalle))

    # Obtener paquetes para el combo
    cursor.execute('SELECT Id_Paquete, Descripcion, PaquetesCompletos, UnidadesSobrantes, Inventario FROM Paquete WHERE Papelera = 0')
    paquetes = cursor.fetchall()

    # Convertir paquetes a lista de dicts para serialización JSON
    paquetes = [dict(zip([col[0] for col in cursor.description], row)) for row in paquetes]

    cursor.execute('SELECT MAX(Id_Venta) FROM Venta WHERE Papelera = 0')
    max_id_venta_result = cursor.fetchone()
    max_id_venta = max_id_venta_result[0] if max_id_venta_result and max_id_venta_result[0] is not None else 1


    if not detalle:
        cursor.close()
        conn.close()
        flash('Detalle de venta no encontrado.', 'danger')
        return redirect(url_for('ver_detalles_ventas'))

    if request.method == 'POST':
        try:
            id_venta = int(request.form['id_venta'])
            id_paquete = int(request.form['paquete_id'])
            cantidad_paquetes = int(request.form['cantidad_paquetes'])
            cantidad_unidades = int(request.form['cantidad_unidades'])
            # Si quieres actualizar precio unitario y subtotal, también agregar aquí y en el form

            # Actualizamos solo los campos que sí están en DetalleVenta
            cursor.execute('''
                UPDATE DetalleVenta
                SET Id_Venta = ?, Id_Paquete = ?, CantidadPaquetes = ?, CantidadUnidades = ?
                WHERE Id_DetalleVenta = ?
            ''', (id_venta, id_paquete, cantidad_paquetes, cantidad_unidades, id))

            conn.commit()
            flash('Detalle de venta actualizado correctamente.', 'success')
            return redirect(url_for('ver_detalles_ventas'))

        except Exception as e:
            flash(f'Error al actualizar el detalle: {str(e)}', 'danger')


    cursor.close()
    conn.close()

    return render_template_ajax(
        'Ventas/editar_detalle_venta.html',
        detalle=detalle,
        paquetes=paquetes,
        max_id_venta=max_id_venta)

""" @app.route('/eliminar_detalle_venta/<int:id>', methods=['POST'])
@login_requerido
def eliminar_detalle_venta(id):
    print(id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM DetallesDeVentas WHERE Id_DetallesDeVentas = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_detalles_ventas'))

 """

#Compras
@app.route("/compras")
@login_requerido
def ver_compras():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer compras con proveedor y fecha
    cursor.execute("""
        SELECT C.Id_Compra, C.FechaDeCompra, P.NombreProveedor
        FROM Compras C
        LEFT JOIN Proveedor P ON C.Id_Proveedor = P.Id_Proveedor
        ORDER BY C.Id_Compra DESC
    """)
    compras = cursor.fetchall()

    lista_compras = []
    for compra in compras:
        id_compra = compra[0]
        fecha = compra[1]
        proveedor = compra[2] if compra[2] else "Sin proveedor"

        # Ejecutar el procedimiento almacenado para calcular el total
        cursor.execute("EXEC ObtenerTotalFactura @Id_Compra = ?", id_compra)
        resultado = cursor.fetchone()

        if resultado and resultado[1] is not None:
            total = float(resultado[1])  # Convertir Decimal a float
        else:
            total = 0.0

        lista_compras.append((id_compra, fecha, proveedor, total))

    cursor.close()
    conn.close()

    return render_template_ajax("Compras/compras.html", compras=lista_compras)


# -----------------------
# 2. Mostrar formulario de nueva compra
# -----------------------
@app.route('/crear_compra', methods=['GET'])
@login_requerido
def crear_compra():
    return render_template('Compras/crear_compra.html')


# -----------------------
# 2.1 Confirmar y crear compra en BD
# -----------------------
@app.route('/crear_compra/confirmar', methods=['POST'])
@login_requerido
def confirmar_crear_compra():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Compras (Id_Proveedor) OUTPUT INSERTED.Id_Compra VALUES (1)")
    nueva_compra_id = cursor.fetchone()[0]
    conn.commit()

    cursor.close()
    conn.close()

    flash('Compra iniciada, agregue productos al carrito')
    return redirect(url_for('carrito', id_compra=nueva_compra_id))

# -----------------------
# 3. Ver carrito / agregar productos
# -----------------------
@app.route('/carrito/<int:id_compra>', methods=['GET'])
@login_requerido
def carrito(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la compra
    cursor.execute("SELECT Id_Compra, FechaDeCompra, Id_Proveedor FROM Compras WHERE Id_Compra = ?", (id_compra,))
    compra = cursor.fetchone()
    if not compra:
        flash('Compra no encontrada')
        cursor.close()
        conn.close()
        return redirect(url_for('ver_compras'))

    # Buscar productos
    buscar = request.args.get('buscar', '').strip()
    if buscar:
        cursor.execute("""
            SELECT Id_Paquete, Descripcion, PrecioCompra_Paq
            FROM Paquete
            WHERE Papelera = 0 AND Descripcion LIKE ?
        """, (f"%{buscar}%",))
    else:
        cursor.execute("""
            SELECT Id_Paquete, Descripcion, PrecioCompra_Paq
            FROM Paquete
            WHERE Papelera = 0
        """)
    paquetes = cursor.fetchall()

    # Obtener detalles del carrito
    cursor.execute('''
        SELECT 
            dc.Id_DetalleDeCompra, p.Descripcion AS Producto, dc.Cantidad, dc.TotalConIVA
        FROM DetallesDeCompras dc
        JOIN Paquete p ON dc.Id_Paquete = p.Id_Paquete
        WHERE dc.Id_Compra = ?
    ''', (id_compra,))
    carrito = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('Compras/carrito.html', compra=compra, paquetes=paquetes, carrito=carrito, buscar=buscar)

# -----------------------
# 4. Agregar producto al carrito
# -----------------------
@app.route('/carrito/<int:id_compra>/agregar', methods=['POST'])
@login_requerido
def agregar_al_carrito(id_compra):
    id_paquete = request.form.get('id_paquete')
    cantidad = int(request.form.get('cantidad', 1))

    if cantidad < 1:
        flash('La cantidad debe ser al menos 1')
        return redirect(url_for('carrito', id_compra=id_compra))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar que existe
    cursor.execute("SELECT PrecioCompra_Paq FROM Paquete WHERE Id_Paquete = ?", (id_paquete,))
    paquete = cursor.fetchone()
    if not paquete:
        flash('Producto no encontrado')
        cursor.close()
        conn.close()
        return redirect(url_for('carrito', id_compra=id_compra))

    # Revisar si ya existe en carrito
    cursor.execute("""
        SELECT Id_DetalleDeCompra, Cantidad 
        FROM DetallesDeCompras 
        WHERE Id_Compra = ? AND Id_Paquete = ?
    """, (id_compra, id_paquete))
    detalle = cursor.fetchone()
    if detalle:
        nueva_cantidad = detalle[1] + cantidad
        cursor.execute("UPDATE DetallesDeCompras SET Cantidad = ? WHERE Id_DetalleDeCompra = ?", (nueva_cantidad, detalle[0]))
    else:
        cursor.execute("""
            INSERT INTO DetallesDeCompras (Id_Compra, Id_Paquete, Cantidad)
            VALUES (?, ?, ?)
        """, (id_compra, id_paquete, cantidad))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Producto agregado al carrito')
    return redirect(url_for('carrito', id_compra=id_compra))

# -----------------------
# 5. Eliminar producto del carrito
# -----------------------
@app.route('/carrito/<int:id_compra>/eliminar/<int:id_detalle>', methods=['GET'])
@login_requerido
def eliminar_detalle(id_compra, id_detalle):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DetallesDeCompras WHERE Id_DetalleDeCompra = ?", (id_detalle,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Producto eliminado del carrito')
    return redirect(url_for('carrito', id_compra=id_compra))
# -----------------------
# 6. Finalizar compra (MODIFICADA: SP actualiza PaquetesCompletos, trigger recalcula Inventario)
# -----------------------
@app.route('/carrito/<int:id_compra>/finalizar', methods=['GET'])
@login_requerido
def finalizar_compra(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Ejecutar el procedimiento para obtener el total
        cursor.execute("EXEC ObtenerTotalFactura @Id_Compra = ?", (id_compra,))
        resultado = cursor.fetchone()

        if resultado is None or resultado[1] is None:
            flash('No se puede finalizar una compra sin productos')
            return redirect(url_for('carrito', id_compra=id_compra))

        total = float(resultado[1])  # resultado[1] es el total

        # Verificar que hay productos
        cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = ?", (id_compra,))
        count_detalles = cursor.fetchone()[0]
        if count_detalles == 0:
            flash('No hay productos en el carrito')
            return redirect(url_for('carrito', id_compra=id_compra))

        # Depuración: Ver PaquetesCompletos e Inventario antes
        cursor.execute("SELECT p.Id_Paquete, p.Descripcion, p.PaquetesCompletos, p.Inventario FROM Paquete p INNER JOIN DetallesDeCompras dc ON p.Id_Paquete = dc.Id_Paquete WHERE dc.Id_Compra = ?", (id_compra,))
        estado_antes = cursor.fetchall()
        print(f"Estado ANTES de finalizar compra {id_compra}: {estado_antes}")

        # Llamar al SP para actualizar PaquetesCompletos (trigger recalculará Inventario)
        cursor.execute("EXEC FinalizarCompraSumarInventario @Id_Compra = ?", (id_compra,))
        print(f"SP ejecutado para compra {id_compra} (actualizó PaquetesCompletos)")

        # Depuración: Ver PaquetesCompletos e Inventario después
        cursor.execute("SELECT p.Id_Paquete, p.Descripcion, p.PaquetesCompletos, p.Inventario FROM Paquete p INNER JOIN DetallesDeCompras dc ON p.Id_Paquete = dc.Id_Paquete WHERE dc.Id_Compra = ?", (id_compra,))
        estado_despues = cursor.fetchall()
        print(f"Estado DESPUÉS de finalizar compra {id_compra}: {estado_despues}")

        # Comparar para confirmar cambios
        cambios = []
        for antes, despues in zip(estado_antes, estado_despues):
            if antes[2] != despues[2] or antes[3] != despues[3]:  # PaquetesCompletos o Inventario cambió
                cambios.append(f"Paquete {despues[0]} ({despues[1]}): PaquetesCompletos {antes[2]} -> {despues[2]}, Inventario {antes[3]} -> {despues[3]}")
        if cambios:
            print(f"Cambios detectados: {cambios}")
        else:
            print("No se detectaron cambios")

        conn.commit()  # Confirmar cambios

        flash(f'Compra finalizada correctamente. Total: C${total:.2f}')
        return redirect(url_for('ver_compras'))

    except Exception as e:
        print(f"Error en finalizar_compra: {e}")
        conn.rollback()
        flash('Error al finalizar la compra')
        return redirect(url_for('carrito', id_compra=id_compra))
    finally:
        cursor.close()
        conn.close()

# -----------------------
# 7. Cancelar compra
# -----------------------
@app.route('/carrito/<int:id_compra>/cancelar', methods=['GET'])
@login_requerido
def cancelar_compra(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si tiene detalles
    cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = ?", (id_compra,))
    tiene_detalles = cursor.fetchone()[0]

    if tiene_detalles > 0:
        flash('No se puede cancelar, la compra ya tiene productos')
    else:
        cursor.execute("DELETE FROM Compras WHERE Id_Compra = ?", (id_compra,))
        conn.commit()
        flash('Compra cancelada correctamente')

    cursor.close()
    conn.close()
    return redirect(url_for('ver_compras'))

# -----------------------
# 7.1 Cancelar compra automáticamente si el usuario se va sin finalizar
# -----------------------
@app.route('/carrito/<int:id_compra>/cancelar_exit', methods=['POST'])
def cancelar_compra_exit(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si la compra tiene productos
    cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = ?", (id_compra,))
    tiene_detalles = cursor.fetchone()[0]

    # Solo borrar si está vacía
    if tiene_detalles == 0:
        cursor.execute("DELETE FROM Compras WHERE Id_Compra = ?", (id_compra,))
        conn.commit()

    cursor.close()
    conn.close()
    return ('', 204)  # Sin contenido (no rompe la navegación)


# -----------------------
    # 8. Ver detalles de una compra
# -----------------------
@app.route('/detalles_compras/<int:id_compra>', methods=['GET'])
@login_requerido
def detalles_compras(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer la compra
    cursor.execute("""
        SELECT Id_Compra, FechaDeCompra, Id_Proveedor
        FROM Compras 
        WHERE Id_Compra = ?
    """, (id_compra,))
    compra = cursor.fetchone()

    if not compra:
        flash('Compra no encontrada', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('ver_compras'))

    # Traer detalles de la compra
    cursor.execute('''
        SELECT 
            p.Descripcion AS Producto, 
            dc.Cantidad, 
            dc.PrecioAntDes, 
            dc.TotalAntDes, 
            dc.DescuentoTotal, 
            dc.TotalConDes, 
            dc.TotalConIva
        FROM DetallesDeCompras dc
        JOIN Paquete p ON dc.Id_Paquete = p.Id_Paquete
        WHERE dc.Id_Compra = ?
    ''', (id_compra,))
    detalles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('Compras/detalles_compra.html', compra=compra, detalles=detalles)


# Nomina
@app.route('/ver_nomina', methods=['GET', 'POST'])
@login_requerido
def ver_nomina():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los empleados activos para el select
    cursor.execute('''
        SELECT 
            Id_Empleado,
            PNombre, SNombre, PApellido, SApellido,
            Estado
        FROM Empleado 
        WHERE Papelera = 0 AND Estado = 'Activo'
        ORDER BY PNombre, PApellido
    ''')
    
    columnas = [col[0] for col in cursor.description]
    empleados_raw = cursor.fetchall()
    empleados = []
    
    for emp_raw in empleados_raw:
        emp = dict(zip(columnas, emp_raw))
        # Combinar nombres y apellidos
        nombres = f"{emp.get('PNombre', '')} {emp.get('SNombre', '')}".strip()
        apellidos = f"{emp.get('PApellido', '')} {emp.get('SApellido', '')}".strip()
        emp['Nombres'] = nombres
        emp['Apellidos'] = apellidos
        empleados.append(emp)

    conn.close()
    return render_template_ajax('Empleados/ver_nomina.html', empleados=empleados)





@app.route('/crear_nota/<int:id>', methods=['GET', 'POST'])
@login_requerido
def crear_nota(id):
    if request.method == 'POST':
        asunto = request.form['asunto'].strip()
        fecha = request.form['fecha']
        
        if not asunto:
            flash('El asunto es obligatorio.', 'danger')
            return redirect(url_for('crear_nota'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO Notas (Asunto, FechaDelAsunto, Id_Empleado)
                VALUES (?, ?, ?)
            ''', (asunto, fecha, id))
            
            conn.commit()
            conn.close()
            flash('Nota creada exitosamente.', 'success')
            return redirect(url_for('crear_nota', id=id))
            
        except Exception as e:
            conn.close()
            flash('Error al crear la nota.', 'danger')
            return redirect(url_for('crear_nota', id=id))
    
    # GET - Mostrar página con notas existentes
    conn = get_db_connection()
    cursor = conn.cursor()
    

    
    # Obtener todas las notas del empleado actual
    cursor.execute('''
        SELECT n.Id_Nota, n.Asunto, n.FechaDelAsunto, n.Id_Empleado,
               e.PNombre, e.SNombre, e.PApellido, e.SApellido, n.Estado
        FROM Notas n
        LEFT JOIN Empleado e ON n.Id_Empleado = e.Id_Empleado
        WHERE n.Id_Empleado = ?
        ORDER BY n.FechaDelAsunto DESC, n.Id_Nota DESC
    ''', (id,))
    
    columnas = [col[0] for col in cursor.description]
    notas_raw = cursor.fetchall()
    notas = []
    
    for nota_raw in notas_raw:
        nota = dict(zip(columnas, nota_raw))
        # Combinar nombre del empleado
        nombres = f"{nota.get('PNombre', '')} {nota.get('SNombre', '')}".strip()
        apellidos = f"{nota.get('PApellido', '')} {nota.get('SApellido', '')}".strip()
        nota['nombre_empleado'] = f"{nombres} {apellidos}".strip()
        notas.append(nota)
    
    conn.close()
    
    # Fecha actual para el formulario
    from datetime import date
    fecha_actual = date.today().strftime('%Y-%m-%d')
    
    return render_template_ajax('Empleados/crear_nota.html', notas=notas, fecha_actual=fecha_actual, empleado_id=id)

@app.route('/marcar_nota', methods=['POST'])
@login_requerido
def marcar_nota():
    data = request.get_json()
    nota_id = data.get('nota_id')
    completada = data.get('completada', False)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que la nota existe
        cursor.execute('SELECT Id_Empleado FROM Notas WHERE Id_Nota = ?', (nota_id,))
        nota = cursor.fetchone()
        
        if not nota:
            conn.close()
            return jsonify({'success': False, 'message': 'Nota no encontrada'})
        
        # Actualizar el estado en la columna Estado
        nuevo_estado = 'Completada' if completada else 'Pendiente'
        cursor.execute('UPDATE Notas SET Estado = ? WHERE Id_Nota = ?', (nuevo_estado, nota_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/eliminar_nota', methods=['POST'])
@login_requerido
def eliminar_nota():
    data = request.get_json()
    nota_id = data.get('nota_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que la nota existe
        cursor.execute('SELECT Id_Empleado FROM Notas WHERE Id_Nota = ?', (nota_id,))
        nota = cursor.fetchone()
        
        if not nota:
            conn.close()
            return jsonify({'success': False, 'message': 'Nota no encontrada'})
        
        # Eliminar la nota
        cursor.execute('DELETE FROM Notas WHERE Id_Nota = ?', (nota_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/crear_empleado', methods=['GET', 'POST'])
@login_requerido
def crear_empleado():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        primer_nombre = request.form['primer_nombre']
        segundo_nombre = request.form.get('segundo_nombre', '')
        primer_apellido = request.form['primer_apellido']
        segundo_apellido = request.form.get('segundo_apellido', '')
        
        # Combinar nombres y apellidos
        nombres = f"{primer_nombre} {segundo_nombre}".strip()
        apellidos = f"{primer_apellido} {segundo_apellido}".strip()
        
        cedula = request.form['cedula']
        estado = request.form['estado']
        estado_civil = request.form['estado_civil']
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        fecha_inicontrato = request.form['fecha_Inicontrato']
        fecha_fincontrato = request.form['fecha_Fincontrato']
        direccion = request.form['direccion']
        num_inss = request.form['num']
        num_ruc = request.form['num2']
        salarioBase = request.form['salarioBase'] or 0
        supervisor = request.form['supervisor'] or None

        cursor.execute('''
            INSERT INTO Empleado (PNombre, SNombre, PApellido, SApellido, NumCedula, EstadoCivil, Sexo, 
                                 FechaDeNacimiento, FechaDeInicioContrato, FechaDeFinContrato, Direccion, 
                                 NumInss, RUC, SalarioBase, Supervisor, Estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, estado_civil, sexo,
              fecha_nacimiento, fecha_inicontrato, fecha_fincontrato, direccion, num_inss, num_ruc, salarioBase, supervisor, estado))
        conn.commit()
        conn.close()
        
        flash('Empleado creado exitosamente.', 'success')
        return redirect(url_for('ver_empleados'))

    # Obtener supervisores para el combo
    cursor.execute('SELECT Id_Empleado, PNombre, SNombre, PApellido, SApellido FROM Empleado WHERE Papelera = 0')
    supervisores_raw = cursor.fetchall()
    
    # Procesar supervisores
    supervisores = []
    for sup in supervisores_raw:
        supervisor_dict = {
            'Id_Empleado': sup[0],
            'PNombre': sup[1],
            'SNombre': sup[2],
            'PApellido': sup[3],
            'SApellido': sup[4],
            'Nombres': f"{sup[1]} {sup[2]}".strip(),
            'Apellidos': f"{sup[3]} {sup[4]}".strip()
        }
        supervisores.append(supervisor_dict)

    conn.close()
    return render_template_ajax('Empleados/crear_empleado.html', supervisores=supervisores)


@app.route('/empleados', methods=['GET'])
@login_requerido
def ver_empleados():
    busqueda = request.args.get('busqueda', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar empleados
    if busqueda:
        cursor.execute('''
            SELECT 
                e.Id_Empleado,
                e.PNombre,
                e.SNombre,
                e.PApellido,
                e.SApellido,
                e.FechaDeNacimiento,
                e.FechaDeInicioContrato,
                e.FechaDeFinContrato AS FechaDeFinContrato,
                e.Direccion,
                e.Estado,
                s.PNombre AS SupervisorPNombre,
                s.SNombre AS SupervisorSNombre,
                s.PApellido AS SupervisorPApellido,
                s.SApellido AS SupervisorSApellido,
                e.NumCedula,
                e.EstadoCivil,
                e.Sexo,
                e.NumInss,
                e.RUC,
                e.SalarioBase
            FROM Empleado e
            LEFT JOIN Empleado s ON e.Supervisor = s.Id_Empleado
            WHERE (e.PNombre LIKE ? OR e.SNombre LIKE ? OR e.PApellido LIKE ? OR e.SApellido LIKE ? OR e.Direccion LIKE ?) AND e.Papelera = 0
            ORDER BY e.Id_Empleado ASC
        ''', (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
    else:
        cursor.execute('''
            SELECT 
                e.Id_Empleado,
                e.PNombre,
                e.SNombre,
                e.PApellido,
                e.SApellido,
                e.FechaDeNacimiento,
                e.FechaDeInicioContrato,
                e.FechaDeFinContrato AS FechaDeFinContrato,
                e.Direccion,
                e.Estado,
                s.PNombre AS SupervisorPNombre,
                s.SNombre AS SupervisorSNombre,
                s.PApellido AS SupervisorPApellido,
                s.SApellido AS SupervisorSApellido,
                e.NumCedula,
                e.EstadoCivil,
                e.Sexo,
                e.NumInss,
                e.RUC,
                e.SalarioBase
            FROM Empleado e
            LEFT JOIN Empleado s ON e.Supervisor = s.Id_Empleado
            WHERE e.Papelera = 0
            ORDER BY e.Id_Empleado ASC
        ''')

    columnas = [col[0] for col in cursor.description]
    empleados = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    for emp in empleados:
        # Combinar nombres y apellidos
        nombres = f"{emp.get('PNombre', '')} {emp.get('SNombre', '')}".strip()
        apellidos = f"{emp.get('PApellido', '')} {emp.get('SApellido', '')}".strip()
        emp['Nombres'] = nombres
        emp['Apellidos'] = apellidos
        
        # Combinar nombres del supervisor
        if emp.get('SupervisorPNombre'):
            supervisor_nombres = f"{emp.get('SupervisorPNombre', '')} {emp.get('SupervisorSNombre', '')}".strip()
            supervisor_apellidos = f"{emp.get('SupervisorPApellido', '')} {emp.get('SupervisorSApellido', '')}".strip()
            emp['NombreSupervisor'] = supervisor_nombres
            emp['ApellidoSupervisor'] = supervisor_apellidos
        
        emp['Edad'] = calcular_edad(emp['FechaDeNacimiento'])
        emp['FechaDeContrato'] = emp.get('FechaDeInicioContrato', '')
        emp['FechaDeFinContrato'] = emp.get('FechaDeFinContrato', '')

    conn.close()
    return render_template_ajax(
        'Empleados/empleados.html',
        empleados=empleados,
        busqueda=busqueda
    )


@app.route('/editar_empleado/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_empleado(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener el empleado usando consulta explícita para asegurar todas las columnas
    cursor.execute('''
        SELECT Id_Empleado, PNombre, SNombre, PApellido, SApellido, EstadoCivil, Sexo, 
               FechaDeNacimiento, FechaDeInicioContrato, FechaDeFinContrato, RUC, SalarioBase,
               NumCedula, NumInss, Estado, Direccion, Supervisor, Papelera
        FROM Empleado 
        WHERE Id_Empleado = ? AND Papelera = 0
    ''', (id,))
    empleado_raw = cursor.fetchone()

    # Obtener supervisores para el combo (excluyendo el mismo empleado)
    cursor.execute('SELECT Id_Empleado, PNombre, SNombre, PApellido, SApellido FROM Empleado WHERE Id_Empleado != ? AND Papelera = 0', (id,))
    supervisores_raw = cursor.fetchall()

    if not empleado_raw:
        conn.close()
        flash('Empleado no encontrado.', 'danger')
        return redirect(url_for('ver_empleados'))

    # Convertir empleado a diccionario usando nombres de columna explícitos
    columnas = ['Id_Empleado', 'PNombre', 'SNombre', 'PApellido', 'SApellido', 'EstadoCivil', 'Sexo', 
                'FechaDeNacimiento', 'FechaDeInicioContrato', 'FechaDeFinContrato', 'RUC', 'SalarioBase',
                'NumCedula', 'NumInss', 'Estado', 'Direccion', 'Supervisor', 'Papelera']
    empleado = dict(zip(columnas, empleado_raw))
    
    # Combinar nombres y apellidos para el empleado
    empleado['Nombres'] = f"{empleado.get('PNombre', '')} {empleado.get('SNombre', '')}".strip()
    empleado['Apellidos'] = f"{empleado.get('PApellido', '')} {empleado.get('SApellido', '')}".strip()

    # Procesar supervisores
    supervisores = []
    for sup in supervisores_raw:
        supervisor_dict = {
            'Id_Empleado': sup[0],
            'PNombre': sup[1],
            'SNombre': sup[2],
            'PApellido': sup[3],
            'SApellido': sup[4],
            'Nombres': f"{sup[1]} {sup[2]}".strip(),
            'Apellidos': f"{sup[3]} {sup[4]}".strip()
        }
        supervisores.append(supervisor_dict)

    if request.method == 'POST':
        primer_nombre = request.form['primer_nombre']
        segundo_nombre = request.form.get('segundo_nombre', '')
        primer_apellido = request.form['primer_apellido']
        segundo_apellido = request.form.get('segundo_apellido', '')
        cedula = request.form['cedula']
        estado = request.form['estado']
        estado_civil = request.form['estado_civil']
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        fecha_inicontrato = request.form['fecha_Inicontrato']
        fecha_fincontrato = request.form['fecha_Fincontrato']
        direccion = request.form['direccion']
        num_inss = request.form['num']
        num_ruc = request.form['num2']
        salarioBase = request.form['salarioBase'] or 0
        supervisor = request.form['supervisor'] or None
        cursor.execute('''
            UPDATE Empleado
            SET PNombre=?, SNombre=?, PApellido=?, SApellido=?, NumCedula=?, EstadoCivil=?, Sexo=?, 
                FechaDeNacimiento=?, FechaDeInicioContrato=?, FechaDeFinContrato=?, Direccion=?, 
                NumInss=?, RUC=?, SalarioBase=?, Supervisor=?, Estado=?
            WHERE Id_Empleado=?
        ''', (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, estado_civil, sexo,
              fecha_nacimiento, fecha_inicontrato, fecha_fincontrato, direccion, num_inss, num_ruc, salarioBase, supervisor, estado, id))
        conn.commit()
        conn.close()
        flash('Empleado actualizado exitosamente.', 'success')
        return redirect(url_for('ver_empleados'))

    conn.close()
    return render_template_ajax('Empleados/editar_empleado.html', empleado=empleado, supervisores=supervisores)


#Ganancia Diaria
@app.route('/ganancia_diaria')
@login_requerido
def ganancia_diaria():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer todas las ganancias
    cursor.execute('''
        SELECT gd.Id_Venta, gd.Fecha, gd.TotalVenta, gd.GananciaCalculada
        FROM GananciaDiaria gd
        WHERE gd.Papelera = 0
        ORDER BY gd.Id_Venta ASC
    ''')
    ganancias = cursor.fetchall()

    # Obtener ventas disponibles para mostrar o calcular
    cursor.execute('SELECT Id_Venta FROM Venta WHERE Papelera = 0 ORDER BY Id_Venta ASC')
    ventas = cursor.fetchall()

    fechas = [row.Fecha.strftime('%Y-%m-%d') for row in ganancias if row.GananciaCalculada is not None]
    valores = [float(row.GananciaCalculada) for row in ganancias if row.GananciaCalculada is not None]

    conn.close()

    if is_ajax_request():
        rendered = render_template('Ventas/ganancia_diaria.html', ganancias=ganancias, ventas=ventas, fechas=fechas, valores=valores)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else '',
            'fechas': fechas,
            'valores': valores
        })
    else:
        return render_template('Ventas/ganancia_diaria.html', ganancias=ganancias, ventas=ventas, fechas=fechas, valores=valores)


@app.route('/calcular_ganancia/<int:id_venta>', methods=['POST'])
@login_requerido
def calcular_ganancia(id_venta):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('EXEC CalcularGananciaDiaria ?', (id_venta,))
        conn.commit()
        flash(f'Ganancia calculada para venta #{id_venta}', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al calcular ganancia: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('ganancia_diaria'))


# Función de debug detallada para verificar funcionalidad de "recuérdame"
@app.route('/debug_recuerdame')
def debug_recuerdame():
    """Página de debug detallada para verificar el funcionamiento de 'recuérdame'"""

    # Obtener todas las cookies
    all_cookies = {}
    for cookie_name in request.cookies:
        all_cookies[cookie_name] = request.cookies[cookie_name]

    # Información específica de cookies de recuerdame
    cookies_info = {
        'recuerdame_usuario': request.cookies.get('recuerdame_usuario', 'NO EXISTE'),
        'recuerdame_tipo': request.cookies.get('recuerdame_tipo', 'NO EXISTE'),
        'recuerdame_user_id': request.cookies.get('recuerdame_user_id', 'NO EXISTE'),
    }

    # Información de sesión
    session_info = {
        'usuario': session.get('usuario', 'NO EXISTE'),
        'tipo': session.get('tipo', 'NO EXISTE'),
        'user_id': session.get('user_id', 'NO EXISTE'),
        'session_keys': list(session.keys()),
    }

    # Verificar usuario en BD si hay cookies
    db_status = "No hay cookies para verificar"
    if cookies_info['recuerdame_usuario'] != 'NO EXISTE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT Id_Usuario, NUsuario, Tipo FROM Usuario WHERE NUsuario = ?',
                         (cookies_info['recuerdame_usuario'],))
            user_from_db = cursor.fetchone()
            conn.close()

            if user_from_db:
                db_status = f"✅ Usuario encontrado en BD: ID={user_from_db[0]}, Usuario={user_from_db[1]}, Tipo={user_from_db[2]}"
            else:
                db_status = "❌ Usuario NO encontrado en base de datos"
        except Exception as e:
            db_status = f"❌ Error al consultar BD: {e}"

    # Estado general
    has_valid_cookies = all(cookie != 'NO EXISTE' for cookie in cookies_info.values())
    has_session = session_info['usuario'] != 'NO EXISTE'

    status_message = ""
    if has_session:
        status_message = "✅ Sesión activa - Usuario logueado"
    elif has_valid_cookies:
        status_message = "🔄 Cookies válidas encontradas - Debería restaurar sesión automáticamente"
    else:
        status_message = "❌ No hay sesión ni cookies válidas"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔍 Debug - Recuérdame</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .success {{ background: #d4edda; border-color: #c3e6cb; }}
            .warning {{ background: #fff3cd; border-color: #ffeaa7; }}
            .error {{ background: #f8d7da; border-color: #f5c6cb; }}
            .info {{ background: #d1ecf1; border-color: #bee5eb; }}
            pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
            .status {{ font-size: 18px; font-weight: bold; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Debug - Funcionalidad "Recuérdame"</h1>

            <div class="status {'success' if has_session else 'warning' if has_valid_cookies else 'error'}">
                {status_message}
            </div>

            <div class="section info">
                <h2>🍪 Cookies de "Recuérdame"</h2>
                <pre>{cookies_info}</pre>
                <p><strong>Estado:</strong> {'✅ Cookies completas' if has_valid_cookies else '❌ Cookies incompletas'}</p>
            </div>

            <div class="section info">
                <h2>📋 Sesión Actual</h2>
                <pre>{session_info}</pre>
                <p><strong>Estado:</strong> {'✅ Sesión activa' if has_session else '❌ Sin sesión'}</p>
            </div>

            <div class="section info">
                <h2>🗄️ Verificación en Base de Datos</h2>
                <p>{db_status}</p>
            </div>

            <div class="section info">
                <h2>🍪 Todas las Cookies del Navegador</h2>
                <pre>{all_cookies}</pre>
            </div>

            <div class="section">
                <h2>🧪 Acciones de Prueba</h2>
                <p>
                    <a href="{url_for('login')}" style="color: #007bff; text-decoration: none;">🔐 Ir a Login</a> |
                    <a href="{url_for('index')}" style="color: #28a745; text-decoration: none;">🏠 Ir al Inicio</a> |
                    <a href="{url_for('logout')}" style="color: #dc3545; text-decoration: none;">🚪 Hacer Logout</a>
                </p>
            </div>

            <div class="section">
                <h2>📝 Instrucciones para Probar</h2>
                <ol>
                    <li>Ve a <a href="{url_for('login')}">/login</a></li>
                    <li>Marca el checkbox "Recuérdame"</li>
                    <li>Inicia sesión</li>
                    <li>Cierra COMPLETAMENTE el navegador</li>
                    <li>Vuelve a abrir y ve directamente a <a href="{url_for('login')}">/login</a></li>
                    <li>Si funciona, deberías ser redirigido automáticamente</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """

#Ejecucion

if __name__ == '__main__':
    print("Iniciando servidor con funcionalidad de 'Recordame'")
    print("Instrucciones:")
    print("   1. Ve a /login")
    print("   2. Marca el checkbox 'Recordame'")
    print("   3. Inicia sesion")
    print("   4. Cierra el navegador")
    print("   5. Vuelve a abrir y ve directamente a cualquier pagina")
    print("   6. Deberias estar logueado automaticamente")
    print("   7. Ve a /debug_recuerdame para verificar el estado detallado")
    app.run(host='0.0.0.0', debug=True)
