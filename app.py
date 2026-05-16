"""
CONTIX — Backend Flask
Base de datos SQLite, API REST para el frontend HTML
"""
import os, re, json, io
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static', static_url_path='')

# ── BASE DE DATOS ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / 'contix.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

db = SQLAlchemy(app)

# ── MODELOS ────────────────────────────────────────────────
class Empresa(db.Model):
    id         = db.Column(db.String(32), primary_key=True)
    nombre     = db.Column(db.String(200), nullable=False)
    cuit       = db.Column(db.String(20))
    iva        = db.Column(db.String(50))
    color      = db.Column(db.String(10), default='#1F3864')
    plan          = db.Column(db.Text, default='{}')   # JSON
    reglas        = db.Column(db.Text, default='[]')   # JSON
    cuentas_onvio = db.Column(db.Text, default='[]')   # JSON - plan ONVIO
    creado     = db.Column(db.DateTime, default=datetime.utcnow)
    periodos   = db.relationship('Periodo', backref='empresa', lazy=True, cascade='all, delete-orphan')

class Periodo(db.Model):
    id          = db.Column(db.String(32), primary_key=True)
    empresa_id  = db.Column(db.String(32), db.ForeignKey('empresa.id'), nullable=False)
    nombre      = db.Column(db.String(100))
    banco       = db.Column(db.String(100))
    movimientos = db.Column(db.Text, default='[]')  # JSON
    creado      = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ── DEFAULTS ───────────────────────────────────────────────
PLAN_DEFAULT = {
    'Ventas / Ingresos':            {'debe': '1.1.1 Banco', 'haber': '4.1.1 Ventas e Ingresos'},
    'Transferencias recibidas':     {'debe': '1.1.1 Banco', 'haber': '4.1.2 Otras entradas'},
    'Haberes / Sueldos pagados':    {'debe': '5.1.1 Sueldos y salarios', 'haber': '1.1.1 Banco'},
    'Impuestos y tasas':            {'debe': '5.2.1 Impuestos y tasas', 'haber': '1.1.1 Banco'},
    'Servicios públicos':           {'debe': '5.3.1 Servicios públicos', 'haber': '1.1.1 Banco'},
    'Alquileres y expensas':        {'debe': '5.3.2 Alquileres y expensas', 'haber': '1.1.1 Banco'},
    'Salud / Seguros':              {'debe': '5.3.3 Salud y seguros', 'haber': '1.1.1 Banco'},
    'Gastos bancarios':             {'debe': '5.4.1 Gastos bancarios', 'haber': '1.1.1 Banco'},
    'Retiros de efectivo':          {'debe': '3.1.1 Cuentas socios / Caja', 'haber': '1.1.1 Banco'},
    'Cheques emitidos':             {'debe': '5.9.2 Cheques emitidos', 'haber': '1.1.1 Banco'},
    'Transferencias emitidas':      {'debe': '5.9.1 Proveedores varios', 'haber': '1.1.1 Banco'},
    'Débitos automáticos':          {'debe': '5.9.3 Débitos automáticos', 'haber': '1.1.1 Banco'},
    'Compras con tarjeta débito':   {'debe': '5.9.4 Compras tarjeta débito', 'haber': '1.1.1 Banco'},
    'Combustible y peajes':         {'debe': '5.9.5 Combustible y peajes', 'haber': '1.1.1 Banco'},
    'Supermercado':                 {'debe': '5.9.7 Supermercado', 'haber': '1.1.1 Banco'},
    'Gastronomía':                  {'debe': '5.9.8 Gastronomía', 'haber': '1.1.1 Banco'},
    'Embargos':                     {'debe': '5.9.9 Embargos judiciales', 'haber': '1.1.1 Banco'},
    'Sin clasificar':               {'debe': '9.9.9 Sin clasificar', 'haber': '1.1.1 Banco'},
}

REGLAS_DEFAULT = [
    {'patron': 'deposito efvo|acreditacion|pago.*recibido|transporte integrados|credito transf|transf recibida', 'cat': 'Ventas / Ingresos'},
    {'patron': 'transferencia de terceros|transferencia recibida', 'cat': 'Transferencias recibidas'},
    {'patron': 'haberes|sueldo|honorario|remuner', 'cat': 'Haberes / Sueldos pagados'},
    {'patron': 'impuesto|ley 25.413|afip|arba|agip|iibb|ingresos brutos|iva|percepcion|monotributo|autonomo|dgr|sellos', 'cat': 'Impuestos y tasas'},
    {'patron': 'telecom|telefon|internet|cablevision|metrogas|edesur|edenor|movistar|claro|fibertel|telmov', 'cat': 'Servicios públicos'},
    {'patron': 'alquiler|expensa|consorcio', 'cat': 'Alquileres y expensas'},
    {'patron': 'seguro|aseguradora|federacion patron|galeno|osde|prepaga|hospital|clinica', 'cat': 'Salud / Seguros'},
    {'patron': 'comision|com transf|servicio de cuenta|extraccion bca|mantenimiento', 'cat': 'Gastos bancarios'},
    {'patron': 'retiro de efectivo|extraccion.*santander|debito extr efvo', 'cat': 'Retiros de efectivo'},
    {'patron': 'cheque', 'cat': 'Cheques emitidos'},
    {'patron': 'transferencia realizada|debito transf|debin', 'cat': 'Transferencias emitidas'},
    {'patron': 'ypf|shell|axion|petrobras|gnc|caminos del|peaje|autopista', 'cat': 'Combustible y peajes'},
    {'patron': 'supermercado|super r |caamano|la economia|tendy', 'cat': 'Supermercado'},
    {'patron': 'restaurant|cafe|sirona|pizza|mirasoles|el colonial|empanada|mcdonalds', 'cat': 'Gastronomía'},
    {'patron': 'debito automatico|deb autom', 'cat': 'Débitos automáticos'},
    {'patron': 'compra con tarjeta|compra electron|tarjeta de debito', 'cat': 'Compras con tarjeta débito'},
    {'patron': 'fondos embargados|embargo', 'cat': 'Embargos'},
]

# ── HELPERS ────────────────────────────────────────────────
def gen_id():
    import uuid
    return uuid.uuid4().hex[:16]

def empresa_to_dict(e):
    return {
        'id': e.id, 'nombre': e.nombre, 'cuit': e.cuit or '',
        'iva': e.iva or 'Responsable Inscripto', 'color': e.color or '#1F3864',
        'plan': json.loads(e.plan or '{}') or PLAN_DEFAULT,
        'reglas': json.loads(e.reglas or '[]') or REGLAS_DEFAULT,
        'cuentas_onvio': json.loads(e.cuentas_onvio or '[]'),
        'n_periodos': len(e.periodos),
    }

def periodo_to_dict(p, include_movs=True):
    d = {
        'id': p.id, 'empresa_id': p.empresa_id,
        'nombre': p.nombre or '', 'banco': p.banco or '',
        'creado': p.creado.isoformat() if p.creado else '',
        'actualizado': p.actualizado.isoformat() if p.actualizado else '',
        'n_movimientos': len(json.loads(p.movimientos or '[]')),
    }
    if include_movs:
        d['movimientos'] = json.loads(p.movimientos or '[]')
    return d

# ── API: EMPRESAS ───────────────────────────────────────────
@app.route('/api/empresas', methods=['GET'])
def get_empresas():
    return jsonify([empresa_to_dict(e) for e in Empresa.query.order_by(Empresa.creado).all()])

@app.route('/api/empresas', methods=['POST'])
def create_empresa():
    data = request.json
    if not data.get('nombre'):
        return jsonify({'error': 'Nombre requerido'}), 400
    e = Empresa(
        id=gen_id(), nombre=data['nombre'], cuit=data.get('cuit',''),
        iva=data.get('iva','Responsable Inscripto'), color=data.get('color','#1F3864'),
        plan=json.dumps(PLAN_DEFAULT), reglas=json.dumps(REGLAS_DEFAULT),
    )
    db.session.add(e); db.session.commit()
    return jsonify(empresa_to_dict(e)), 201

@app.route('/api/empresas/<id>', methods=['PUT'])
def update_empresa(id):
    e = Empresa.query.get_or_404(id)
    data = request.json
    if 'nombre'  in data: e.nombre = data['nombre']
    if 'cuit'    in data: e.cuit   = data['cuit']
    if 'iva'     in data: e.iva    = data['iva']
    if 'color'   in data: e.color  = data['color']
    if 'plan'          in data: e.plan          = json.dumps(data['plan'])
    if 'reglas'        in data: e.reglas        = json.dumps(data['reglas'])
    if 'cuentas_onvio' in data: e.cuentas_onvio = json.dumps(data['cuentas_onvio'])
    db.session.commit()
    return jsonify(empresa_to_dict(e))

@app.route('/api/empresas/<id>', methods=['DELETE'])
def delete_empresa(id):
    e = Empresa.query.get_or_404(id)
    db.session.delete(e); db.session.commit()
    return jsonify({'ok': True})

# ── API: PERÍODOS ───────────────────────────────────────────
@app.route('/api/empresas/<empresa_id>/periodos', methods=['GET'])
def get_periodos(empresa_id):
    periodos = Periodo.query.filter_by(empresa_id=empresa_id).order_by(Periodo.creado).all()
    return jsonify([periodo_to_dict(p, include_movs=False) for p in periodos])

@app.route('/api/empresas/<empresa_id>/periodos', methods=['POST'])
def create_periodo(empresa_id):
    Empresa.query.get_or_404(empresa_id)
    data = request.json
    p = Periodo(
        id=gen_id(), empresa_id=empresa_id,
        nombre=data.get('nombre',''), banco=data.get('banco',''),
        movimientos='[]',
    )
    db.session.add(p); db.session.commit()
    return jsonify(periodo_to_dict(p)), 201

@app.route('/api/periodos/<id>', methods=['GET'])
def get_periodo(id):
    p = Periodo.query.get_or_404(id)
    return jsonify(periodo_to_dict(p))

@app.route('/api/periodos/<id>', methods=['PUT'])
def update_periodo(id):
    p = Periodo.query.get_or_404(id)
    data = request.json
    if 'nombre'      in data: p.nombre      = data['nombre']
    if 'banco'       in data: p.banco       = data['banco']
    if 'movimientos' in data: p.movimientos = json.dumps(data['movimientos'])
    p.actualizado = datetime.utcnow()
    db.session.commit()
    return jsonify(periodo_to_dict(p))

@app.route('/api/periodos/<id>', methods=['DELETE'])
def delete_periodo(id):
    p = Periodo.query.get_or_404(id)
    db.session.delete(p); db.session.commit()
    return jsonify({'ok': True})

# ── API: PROCESAR PDF ───────────────────────────────────────
@app.route('/api/procesar-pdf', methods=['POST'])
def procesar_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No se recibió archivo PDF'}), 400
    pdf_file = request.files['pdf']
    banco    = request.form.get('banco', '')

    # Guardar PDF temporalmente
    tmp_path = Path('/tmp') / pdf_file.filename
    pdf_file.save(tmp_path)

    try:
        # Importar parsers
        from parsers import leer_pdf, detectar_banco, PARSERS, parse_generico, categorizar, cuentas_para, PLAN_DEFAULT as PD

        paginas, texto = leer_pdf(str(tmp_path))
        banco_det = banco.lower() if banco else detectar_banco(texto)
        parser = PARSERS.get(banco_det, parse_generico)
        movimientos = parser(paginas)

        return jsonify({
            'banco': banco_det,
            'movimientos': movimientos,
            'total': len(movimientos),
        })
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500
    finally:
        if tmp_path.exists(): tmp_path.unlink()

# ── API: EXPORTAR EXCEL ─────────────────────────────────────
@app.route('/api/exportar-excel/<periodo_id>', methods=['GET'])
def exportar_excel(periodo_id):
    p = Periodo.query.get_or_404(periodo_id)
    e = Empresa.query.get(p.empresa_id)
    movimientos = json.loads(p.movimientos or '[]')

    from excel_gen import generar_excel
    buf = io.BytesIO()
    generar_excel(movimientos, buf, empresa=e.nombre if e else '', banco=p.banco or '', archivo=p.nombre or '')
    buf.seek(0)

    nombre = f"{(e.nombre if e else 'empresa').replace(' ','_')}_{(p.nombre or 'periodo').replace(' ','_')}_contable.xlsx"
    return send_file(buf, as_attachment=True, download_name=nombre,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ── FRONTEND ────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
