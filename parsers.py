"""
Parsers bancarios — todos los bancos argentinos soportados
"""
import re
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

MONTO_RE = re.compile(r'\$\s*([\d\.]+,\d{2})')
PAGE_NUM  = re.compile(r'^\d+\s*[-–]\s*\d+$')

def pm(s):
    if not s and s != 0: return None
    try: return float(str(s).replace('.','').replace(',','.').strip())
    except: return None

def pm_punto(s):
    if not s: return None
    try: return float(str(s).replace(',','').strip())
    except: return None

def normalizar_fecha(f):
    f = f.replace('-','/')
    p = f.split('/')
    if len(p) == 3:
        d, m, a = p
        if len(a) == 2: a = '20' + a
        return f"{d.zfill(2)}/{m.zfill(2)}/{a}"
    elif len(p) == 2:
        d, m = p
        return f"{d.zfill(2)}/{m.zfill(2)}/{datetime.now().year}"
    return f

CATEGORIAS_REGLAS = [
    (r'deposito efvo|deposito de efectivo|acreditacion|pago.*recibido|transporte integrados|credito transf|transf recibida|traspaso de saldo|credito recaudacion', 'Ventas / Ingresos'),
    (r'transferencia de terceros|transferencia recibida', 'Transferencias recibidas'),
    (r'pago.*haberes|debito.*haberes|deb lote haberes|haberes ol|569 debito', 'Haberes / Sueldos pagados'),
    (r'honorario|remuner', 'Sueldos y salarios'),
    (r'impuesto|ley 25\.?413|imp\.ley|imp s/deb|imp s/cred|afip|arba|agip|iibb|ingresos brutos|iva|percepcion|monotributo|autonomo|dgr|sircreb|recaudacion|sellos|debito 0,6|credito 0,6', 'Impuestos y tasas'),
    (r'telecom|telefon|internet|cablevision|metrogas|edesur|edenor|movistar|claro|fibertel|telmov|personal cel', 'Servicios públicos'),
    (r'alquiler|\balq\b|expensa|consorcio', 'Alquileres y expensas'),
    (r'seguro|aseguradora|federacion patron|galeno|holando|nacion seguros|sancor coop|medife|obra social|osde|prepaga|hospital|clinica', 'Salud / Seguros'),
    (r'comision|comisión|com transf|iva tasa general|intereses sobre saldo|servicio de cuenta|extraccion bca|mant mens|mantenimiento', 'Gastos bancarios'),
    (r'retiro de efectivo|extraccion.*santander|extraccion elec\+cash|debito extr efvo', 'Retiros de efectivo'),
    (r'\becheq\b|cheque p/camara|cheque rechazado|cheque debitado', 'Cheques emitidos'),
    (r'transferencia realizada|debito transf|debin:|500 transferencia|pago visa empresa', 'Transferencias emitidas'),
    (r'ypf|shell|axion|petrobras|gnc|caminos del|peaje|autopista|aubasa', 'Combustible y peajes'),
    (r'farmacia|farmplus|open farma', 'Farmacia'),
    (r'supermercado|super r |caamano|la economia|tendy|maspuros|ecosuper', 'Supermercado'),
    (r'restaurant|cafe|sirona|rosetta|starbucks|mcdonalds|pizza|mirasoles|el colonial|torito|empanada', 'Gastronomía'),
    (r'deb\.? autom|debito automatico|prosegur|automovil club|\baca\b', 'Débitos automáticos'),
    (r'pago con visa|pago visa|compra debito|compra con tarjeta|compra electron', 'Compras con tarjeta débito'),
    (r'fondos embargados|embargo afip|multa cheque', 'Embargos'),
]

PLAN_DEFAULT = {
    'Ventas / Ingresos':          ('1.1.1 Banco', '4.1.1 Ventas e Ingresos'),
    'Transferencias recibidas':   ('1.1.1 Banco', '4.1.2 Otras entradas'),
    'Haberes / Sueldos pagados':  ('5.1.1 Sueldos y salarios', '1.1.1 Banco'),
    'Sueldos y salarios':         ('5.1.1 Sueldos y salarios', '1.1.1 Banco'),
    'Impuestos y tasas':          ('5.2.1 Impuestos y tasas', '1.1.1 Banco'),
    'Servicios públicos':         ('5.3.1 Servicios públicos', '1.1.1 Banco'),
    'Alquileres y expensas':      ('5.3.2 Alquileres y expensas', '1.1.1 Banco'),
    'Salud / Seguros':            ('5.3.3 Salud y seguros', '1.1.1 Banco'),
    'Gastos bancarios':           ('5.4.1 Gastos bancarios', '1.1.1 Banco'),
    'Retiros de efectivo':        ('3.1.1 Cuentas socios / Caja', '1.1.1 Banco'),
    'Cheques emitidos':           ('5.9.2 Cheques emitidos', '1.1.1 Banco'),
    'Transferencias emitidas':    ('5.9.1 Proveedores varios', '1.1.1 Banco'),
    'Débitos automáticos':        ('5.9.3 Débitos automáticos', '1.1.1 Banco'),
    'Compras con tarjeta débito': ('5.9.4 Compras tarjeta débito', '1.1.1 Banco'),
    'Combustible y peajes':       ('5.9.5 Combustible y peajes', '1.1.1 Banco'),
    'Farmacia':                   ('5.9.6 Farmacia', '1.1.1 Banco'),
    'Supermercado':               ('5.9.7 Supermercado', '1.1.1 Banco'),
    'Gastronomía':                ('5.9.8 Gastronomía', '1.1.1 Banco'),
    'Embargos':                   ('5.9.9 Embargos judiciales', '1.1.1 Banco'),
    'Sin clasificar':             ('9.9.9 Sin clasificar', '1.1.1 Banco'),
}

def categorizar(desc):
    d = (desc or '').lower()
    for pat, cat in CATEGORIAS_REGLAS:
        try:
            if re.search(pat, d): return cat
        except: pass
    return 'Sin clasificar'

def cuentas_para(cat, tipo):
    c = PLAN_DEFAULT.get(cat, PLAN_DEFAULT['Sin clasificar'])
    if tipo == 'Crédito': return '1.1.1 Banco', c[1]
    return c[0], '1.1.1 Banco'

def mov(fecha, comp, desc, tipo, debito, credito, saldo):
    cat = categorizar(desc)
    cd, ch = cuentas_para(cat, tipo)
    return {
        'fecha': normalizar_fecha(fecha) if fecha else '',
        'comprobante': comp or '',
        'descripcion': desc or '',
        'tipo': tipo,
        'debito': debito,
        'credito': credito,
        'saldo': saldo,
        'categoria': cat,
        'cuenta_debe': cd,
        'cuenta_haber': ch,
    }

def detectar_banco(texto):
    t = texto.lower()
    if 'santander' in t: return 'santander'
    if 'galicia' in t: return 'galicia'
    if 'frances' in t or 'francés' in t or 'bbva' in t: return 'frances'
    if 'icbc' in t or 'industrialandcommercialbank' in t: return 'icbc'
    if 'columbia' in t or ('cuentas corrientes en pesos' in t and 'sucursal 1' in t): return 'columbia'
    if 'provincia' in t or 'bapro' in t or 'region y casa matriz la plata' in t: return 'bapro'
    if 'ciudad' in t and ('banco' in t or 'florida 302' in t): return 'ciudad'
    if 'itau' in t or 'itaú' in t: return 'itau'
    if 'mercado pago' in t or 'mercadopago' in t or 'mercado libre s.r.l' in t: return 'mercadopago'
    if 'credicoop' in t: return 'credicoop'
    if 'macro' in t: return 'macro'
    if 'nacion' in t or 'nación' in t: return 'nacion'
    return 'generico'

def leer_pdf(ruta):
    paginas, total = [], ''
    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ''
            paginas.append(t)
            total += t + '\n'
    return paginas, total

# ── SANTANDER ────────────────────────────────────────────────
SANT_SKIP = {
    'Salvo error','Banco Santander','CBU:','Período','Emisión','Desde:','Hasta:',
    'Total en pesos','Saldo total','Detalle','Movimientos en pesos','Fecha Comp',
    'Cuenta Corriente','correlativo','Ningún','tampoco','Legales','Intercambio',
    'Garantía','Acuerdo','Impuestos al débit','Depósito de cheque','ECHEQs',
    'Fondos Comunes','Unidad de Inform','Por depósitos','Por extracción',
    'Cheques paga','Movimientos por','Chequeras','Corte a pedido','Orden de no',
    'Certificación','Análisis de','Registración','Gestión de cheq','Por cada mov',
    'Servicio de Tarj','Por mantenimiento','Localidades con','Localidades sin',
    'retencion impuesto','Retención Régimen','devolucion impuesto','alicuota',
    'Servicio de cuenta:','susceptible de','Total retencion','Por retencion',
    'Total Retención','Total devolucion','Por devolucion','Importe no susc',
}

def parse_santander(paginas):
    COMP_RE = re.compile(r'^(\d{4,10})\s+(.+)')
    FECHA_S = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.*)')
    raw = []; fecha_ctx = None
    for texto in paginas:
        if not texto: continue
        lines = [l.strip() for l in texto.split('\n')]
        i = 0
        while i < len(lines):
            line = lines[i]; i += 1
            if not line or PAGE_NUM.match(line): continue
            if any(s in line for s in SANT_SKIP): continue
            montos = MONTO_RE.findall(line)
            if not montos:
                fm = FECHA_S.match(line)
                if fm and not fm.group(2).strip(): fecha_ctx = fm.group(1)
                continue
            rest = line; fecha = None
            fm = FECHA_S.match(rest)
            if fm: fecha = fm.group(1); fecha_ctx = fecha; rest = fm.group(2).strip()
            else: fecha = fecha_ctx
            comp = ''; cm = COMP_RE.match(rest)
            if cm: comp = cm.group(1); rest = cm.group(2).strip()
            desc = MONTO_RE.sub('', rest).strip(' -–')
            desc = re.sub(r'\s+', ' ', desc).strip()
            vals = [pm(m) for m in montos]
            sub = ''
            if i < len(lines):
                nxt = lines[i].strip()
                if (nxt and not MONTO_RE.search(nxt) and not PAGE_NUM.match(nxt)
                        and not any(s in nxt for s in SANT_SKIP) and len(nxt) > 3
                        and not re.match(r'^\d{2}/\d{2}/\d{2}$', nxt)):
                    sub = nxt; i += 1
            if fecha and vals and desc:
                raw.append({'fecha': fecha,'comp': comp,'desc': desc,'sub': sub,'vals': vals})
    result = []; saldo_prev = None
    for m in raw:
        desc_full = m['desc']
        if m['sub'] and not re.match(r'^\d{2}/\d{2}/\d{2}$', m['sub'].strip()):
            desc_full = m['desc'] + ' — ' + m['sub']
        if re.search(r'saldo inicial', desc_full, re.I): continue
        if any(x in desc_full.lower() for x in ['total retencion','por retencion','total retenc','por devolucion','importe no susc']): continue
        vals = m['vals']; debito = credito = saldo = None
        if len(vals) >= 2:
            importe, saldo = vals[0], vals[-1]
            if saldo_prev is not None:
                diff = round(saldo - saldo_prev, 2)
                if abs(diff - importe) < 2: credito = importe
                elif abs(diff + importe) < 2: debito = importe
                else:
                    if re.search(r'credito 0,6|recibido|deposito efvo|transf recibida|credito transf|reintegro|acreditacion', desc_full.lower()): credito = importe
                    else: debito = importe
            else:
                if re.search(r'credito|recibido|deposito|transf recibida|acreditacion|reintegro', desc_full.lower()): credito = importe
                else: debito = importe
            saldo_prev = saldo
        else:
            importe = vals[0]
            if re.search(r'credito|recibido|deposito|transf recibida|acreditacion|reintegro', desc_full.lower()): credito = importe
            else: debito = importe
        tipo = 'Crédito' if credito else 'Débito'
        result.append(mov(m['fecha'], m['comp'], desc_full, tipo, debito, credito, saldo))
    return result

def parse_galicia(paginas):
    LINE_RE = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([+\-])\s+\$\s*([\d\.]+,\d{2})\s+\$\s*(-?[\d\.]+,\d{2})\s*$')
    result = []
    for texto in paginas:
        if not texto: continue
        lines = [l.strip() for l in texto.split('\n')]
        i = 0
        while i < len(lines):
            line = lines[i]; i += 1
            if not line or any(x in line for x in ['Office Banking','CBU:','Fecha Desc']): continue
            m = LINE_RE.match(line)
            if not m: continue
            fecha = m.group(1); desc = m.group(2).strip()
            signo = m.group(3); importe = pm(m.group(4)); saldo = pm(m.group(5))
            while i < len(lines) and lines[i].strip() and not re.match(r'^\d{2}/\d{2}/\d{4}', lines[i]) and not MONTO_RE.search(lines[i]):
                sub = lines[i].strip()
                if len(sub) > 2 and not sub.isdigit(): desc = desc + ' — ' + sub
                i += 1
            tipo = 'Crédito' if signo == '+' else 'Débito'
            result.append(mov(fecha, '', desc, tipo, importe if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
    return result

def parse_frances(paginas):
    CUENTA_RE = re.compile(r'^(\d{2}/\d{2})(?:/\d{2,4})?\s+(?:D\s+)?(?:\d+\s+)?(.+?)\s+(-?[\d\.]+,\d{2})\s+([\d\.]+,\d{2})\s*$')
    TARJETA_RE = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+\*+\s+\*+\s+\*+\s+\d{4}\s+(.+?)\s+\d+\s+\$\s*(-[\d\.]+,\d{2})\s*$')
    result = []; anio = str(datetime.now().year)
    for texto in paginas:
        if not texto: continue
        for line in texto.split('\n'):
            line = line.strip()
            if not line or any(x in line for x in ['FECHA','SALDO','CONCEPTO','RESUMEN','cid:']): continue
            mt = TARJETA_RE.match(line)
            if mt:
                result.append(mov(mt.group(1), '', mt.group(2).strip(), 'Débito', abs(pm(mt.group(3))), None, None))
                continue
            mc = CUENTA_RE.match(line)
            if mc:
                partes = mc.group(1).split('/')
                fecha = f"{partes[0].zfill(2)}/{partes[1].zfill(2)}/{anio}"
                valor = pm(mc.group(3)); saldo = pm(mc.group(4))
                tipo = 'Débito' if valor < 0 else 'Crédito'
                result.append(mov(fecha, '', mc.group(2).strip(), tipo, abs(valor) if tipo=='Débito' else None, valor if tipo=='Crédito' else None, saldo))
    return result

def parse_icbc(paginas):
    FECHA_ICBC = re.compile(r'^(\d{2}-\d{2})\s+(.+?)\s+([\d\.]+,\d{2})(-?)\s*$')
    result = []; anio = str(datetime.now().year)
    for texto in paginas:
        if not texto: continue
        lines = [l.strip() for l in texto.split('\n')]
        i = 0
        while i < len(lines):
            line = lines[i]; i += 1
            if not line or any(x in line for x in ['FECHA CONCEPTO','SALDO ULTIMO','TOT.IMP','Florida 99','C.U.I.T.N°']): continue
            if re.match(r'^_{5,}', line): continue
            mi = FECHA_ICBC.match(line)
            if not mi: continue
            d, mo_n = mi.group(1).split('-')
            fecha = f"{d.zfill(2)}/{mo_n.zfill(2)}/{anio}"
            desc = mi.group(2).strip(); importe = pm(mi.group(3)); es_deb = mi.group(4) == '-'
            if i < len(lines):
                nxt = lines[i].strip()
                if nxt and len(nxt) > 2 and not any(x in nxt for x in ['FECHA','SALDO','C.U.I.T']) and not re.match(r'^\d{2}-\d{2}', nxt):
                    desc = desc + ' — ' + nxt; i += 1
            tipo = 'Débito' if es_deb else 'Crédito'
            result.append(mov(fecha, '', desc, tipo, importe if tipo=='Débito' else None, importe if tipo=='Crédito' else None, None))
    return result

def parse_ciudad(paginas):
    MESES = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
    result = []; saldo_prev = None
    for texto in paginas:
        if not texto: continue
        for line in texto.split('\n'):
            line = line.strip()
            if not line or any(x in line for x in ['FECHA CONCEPTO','SALDO ANTERIOR','HOJA NRO','CUIT:','RESUMEN DE CUENTA','SALDO FINAL DEL DIA','SALDO FINAL AL']): continue
            m = re.match(r'^(\d{2}-[A-Z]{3}-\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([\d\.]+,\d{2})', line)
            if not m: continue
            partes = m.group(1).split('-'); mes_num = MESES.get(partes[1],'01')
            fecha = f"{partes[0].zfill(2)}/{mes_num}/{partes[2]}"
            desc = m.group(2).strip(); importe = pm(m.group(3)); saldo = pm(m.group(4))
            if saldo_prev is not None and saldo is not None:
                diff = round(saldo - saldo_prev, 2)
                tipo = 'Crédito' if abs(diff - importe) < 5 else 'Débito'
            else:
                tipo = 'Crédito' if re.search(r'transferencia.*\d{10}|recaudacion|cr\.tra', desc.lower()) else 'Débito'
            if saldo: saldo_prev = saldo
            result.append(mov(fecha, '', desc, tipo, importe if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
    return result

def parse_bapro(paginas):
    SKIP_B = {'Fecha Concepto','SALDO ANTERIOR','Extracto de Cuenta','REGION Y CASA','CBU:','Cantidad de Titulares','Emitido el','Frecuencia'}
    result = []
    for texto in paginas:
        if not texto: continue
        lines = [l.strip() for l in texto.split('\n')]
        i = 0
        while i < len(lines):
            line = lines[i]; i += 1
            if not line or any(s in line for s in SKIP_B): continue
            if not re.match(r'^\d{2}/\d{2}/\d{4}', line): continue
            fecha = line[:10]; resto = line[10:].strip()
            m = re.match(r'(.+?)\s+(-?[\d]+\.[\d]{2})\s+\d{2}-\d{2}\s+([\d]+\.[\d]{2})\s*$', resto)
            if not m: m = re.match(r'(.+?)\s+(-?[\d]+\.[\d]{2})\s*$', resto)
            if not m: continue
            desc = m.group(1).strip(); importe = float(m.group(2))
            saldo = float(m.group(3)) if len(m.groups()) >= 3 and m.group(3) else None
            if i < len(lines):
                nxt = lines[i].strip()
                if nxt and not re.match(r'\d{2}/\d{2}/\d{4}', nxt) and len(nxt) < 25 and not re.search(r'[\d.]{8,}', nxt):
                    desc = desc + ' — ' + nxt; i += 1
            tipo = 'Débito' if importe < 0 else 'Crédito'
            result.append(mov(fecha, '', desc, tipo, abs(importe) if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
    return result

def parse_columbia(paginas):
    MONTO2 = re.compile(r'(\d[\d,]*\.\d{2})')
    result = []; saldo_prev = None
    for texto in paginas:
        if not texto: continue
        for line in texto.split('\n'):
            line = line.strip()
            if not line or any(x in line for x in ['FECHA DESCRIPCION','SALDO INICIAL','SALDO FINAL DEL DIA','SALDO FINAL AL','HOJA','CUIT:','NOTA:']): continue
            m_fecha = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            if not m_fecha: continue
            fecha = m_fecha.group(1); resto = m_fecha.group(2).strip()
            montos = MONTO2.findall(resto)
            if not montos: continue
            desc = MONTO2.sub('', resto).strip().rstrip('0').strip()
            desc = re.sub(r'\s+', ' ', desc).strip(' 0-')
            importe = pm_punto(montos[0])
            saldo = pm_punto(montos[-1]) if len(montos) >= 2 else None
            if importe is None: continue
            if saldo_prev is not None and saldo is not None:
                diff = round(saldo - saldo_prev, 2)
                tipo = 'Crédito' if abs(diff - importe) < 5 else 'Débito'
            else:
                tipo = 'Débito' if re.search(r'n/d|impuesto|comision|multa|debito fiscal|retencion|iibb|debin', desc.lower()) else 'Crédito'
            if saldo: saldo_prev = saldo
            result.append(mov(fecha, '', desc, tipo, importe if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
    return result

def parse_mercadopago(paginas):
    MOV_DESC_RE = re.compile(r'^(\d{2}-\d{2}-\d{4})\s+(.+?)\s+(\d{9,15})\s+\$\s*(-?[\d\.]+,\d{2})\s+\$\s*([\d\.]+,\d{2})\s*$')
    MOV_RE = re.compile(r'^(\d{2}-\d{2}-\d{4})\s+(\d{9,15})\s+\$\s*(-?[\d\.]+,\d{2})\s+\$\s*([\d\.]+,\d{2})\s*$')
    result = []; desc_acum = []
    for texto in paginas:
        if not texto: continue
        for line in texto.split('\n'):
            line = line.strip()
            if not line or any(x in line for x in ['RESUMEN DE CUENTA','CVU:','Periodo:','Entradas:','DETALLE','Mercado Libre','Fecha de generación']): continue
            md = MOV_DESC_RE.match(line)
            if md:
                fecha = md.group(1).replace('-','/'); desc = md.group(2).strip()
                importe = pm(md.group(4)); saldo = pm(md.group(5))
                tipo = 'Crédito' if importe and importe > 0 else 'Débito'
                result.append(mov(fecha, md.group(3), desc, tipo, abs(importe) if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
                desc_acum = []; continue
            mo = MOV_RE.match(line)
            if mo:
                fecha = mo.group(1).replace('-','/'); importe = pm(mo.group(3)); saldo = pm(mo.group(4))
                desc = ' '.join(desc_acum).strip() or 'Movimiento'
                tipo = 'Crédito' if importe and importe > 0 else 'Débito'
                result.append(mov(fecha, mo.group(2), desc, tipo, abs(importe) if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
                desc_acum = []; continue
            if not re.match(r'^\d{2}-\d{2}-\d{4}', line) and not MONTO_RE.search(line):
                desc_acum.append(line)
            else:
                desc_acum = []
    return result

def parse_generico(paginas):
    FECHA_RE2 = re.compile(r'\b(\d{2}[-/]\d{2}[-/]?\d{0,4})\b')
    result = []; saldo_prev = None
    for texto in paginas:
        if not texto: continue
        for line in texto.split('\n'):
            line = line.strip()
            fechas = FECHA_RE2.findall(line); montos = MONTO_RE.findall(line)
            if not fechas or not montos: continue
            fecha = fechas[0]; importe = pm(montos[0]); saldo = pm(montos[1]) if len(montos) > 1 else None
            desc = MONTO_RE.sub('', FECHA_RE2.sub('', line)).strip()
            desc = re.sub(r'\s+', ' ', desc).strip(' -–')
            if not desc or len(desc) < 3 or not importe: continue
            tipo = 'Crédito' if (saldo_prev and saldo and saldo > saldo_prev) else 'Débito'
            if saldo: saldo_prev = saldo
            result.append(mov(fecha, '', desc, tipo, importe if tipo=='Débito' else None, importe if tipo=='Crédito' else None, saldo))
    return result

PARSERS = {
    'santander':   parse_santander,
    'galicia':     parse_galicia,
    'frances':     parse_frances,
    'icbc':        parse_icbc,
    'ciudad':      parse_ciudad,
    'bapro':       parse_bapro,
    'provincia':   parse_bapro,
    'columbia':    parse_columbia,
    'mercadopago': parse_mercadopago,
    'itau':        parse_generico,
    'credicoop':   parse_generico,
    'macro':       parse_generico,
    'nacion':      parse_generico,
    'generico':    parse_generico,
}
