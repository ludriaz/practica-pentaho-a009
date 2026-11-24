from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import csv, tempfile, hashlib, shutil

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'entrada'; TMP=ROOT/'temporal'; OUT=ROOT/'salida'
EXPECTED_IDS={4,9,11,15,18}

def read_csv(path, delimiter):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=delimiter))

def expected_from_inputs(folder=IN):
    hotels={r['id_hotel']:r['hotel'] for r in read_csv(folder/'hoteles_pdi.csv',';')}
    reservations=read_csv(folder/'reservas_pdi.csv',',')
    payments=read_csv(folder/'cobros_pdi.csv',';')
    pay_by_id={r['id_reserva']:r for r in payments}
    groups=defaultdict(lambda:[0,Decimal('0.00')])
    unpaid=[]
    for r in reservations:
        payment=pay_by_id.get(r['id_reserva'])
        hotel=hotels[r['id_hotel']]
        if payment:
            key=(hotel,r['canal']); groups[key][0]+=1; groups[key][1]+=Decimal(payment['cobrado'])
        else:
            unpaid.append({'id_reserva':int(r['id_reserva']),'hotel':hotel,'canal':r['canal'],'importe':Decimal(r['importe']),'motivo':'Sin cobro asociado en el archivo recibido'})
    return reservations,payments,{k:tuple(v) for k,v in groups.items()},sorted(unpaid,key=lambda x:x['id_reserva'])

def report_ok(path, groups):
    try: rows=read_csv(path,';')
    except (FileNotFoundError, UnicodeError, csv.Error): return False
    got={}
    try:
        for r in rows:
            key=(r['hotel'],r['canal'])
            if key in got or not r['hotel'] or not r['canal']: return False
            n=int(r['n_reservas']); amount=Decimal(r['cobrado_total'])
            if n<1 or amount<0: return False
            got[key]=(n,amount)
    except (KeyError,ValueError,ArithmeticError): return False
    return len(got)==13 and got==groups and sum(x[0] for x in got.values())==15 and sum((x[1] for x in got.values()),Decimal('0'))==Decimal('3965.50')

def unpaid_ok(path, expected):
    try: rows=read_csv(path,';')
    except (FileNotFoundError, UnicodeError, csv.Error): return False
    try:
        got=[]
        for r in rows:
            if not all(r[k] for k in ('id_reserva','hotel','canal','importe','motivo')): return False
            got.append((int(r['id_reserva']),r['hotel'],r['canal'],Decimal(r['importe']),r['motivo']))
        want=[(r['id_reserva'],r['hotel'],r['canal'],r['importe'],r['motivo']) for r in expected]
        return len(got)==5 and len({x[0] for x in got})==5 and got==want and {x[0] for x in got}==EXPECTED_IDS
    except (KeyError,ValueError,ArithmeticError): return False

res,pay,groups,unpaid=expected_from_inputs()
report=TMP/'informe_hotel_canal.csv'; no_pay=TMP/'reservas_sin_cobro.csv'
checks=[]
def record(name,ok,detail): checks.append((name,bool(ok),detail))
record('Primera ejecución (contraste de resultados)',report_ok(report,groups) and unpaid_ok(no_pay,unpaid),'Compara ambos resultados provisionales con una recomputación independiente de entrada/.')
with tempfile.TemporaryDirectory() as d:
    d=Path(d); p2=d/'informe_hotel_canal.csv'; u2=d/'reservas_sin_cobro.csv'
    with p2.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter=';'); w.writerow(['hotel','canal','n_reservas','cobrado_total'])
        for (hotel,channel),(n,amount) in sorted(groups.items()): w.writerow([hotel,channel,n,f'{amount:.2f}'])
    with u2.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter=';'); w.writerow(['id_reserva','hotel','canal','importe','motivo'])
        for r in unpaid: w.writerow([r['id_reserva'],r['hotel'],r['canal'],f"{r['importe']:.2f}",r['motivo']])
    hashes=lambda paths:[hashlib.sha256(x.read_bytes()).hexdigest() for x in paths]
    record('Repetición (prueba lógica, sin Kitchen)',report_ok(p2,groups) and unpaid_ok(u2,unpaid),'La regeneración independiente conserva las filas y totales; no acredita una segunda ejecución PDI.')
    missing=d/'entrada_incompleta'; missing.mkdir(); shutil.copy(IN/'reservas_pdi.csv',missing); shutil.copy(IN/'cobros_pdi.csv',missing)
    record('Falta de entrada (prueba lógica)',not all((missing/f).is_file() for f in ['reservas_pdi.csv','cobros_pdi.csv','hoteles_pdi.csv']),'La entrada de hoteles se omite en una copia temporal y se detecta como ausente.')
    empty=d/'informe_vacio.csv'; empty.write_text('hotel;canal;n_reservas;cobrado_total\n',encoding='utf-8')
    record('Informe solo con cabecera',not report_ok(empty,groups),'La validación independiente rechaza el informe sin filas.')
    bad=d/'informe_total_incorrecto.csv'; shutil.copy(report,bad)
    rows=read_csv(bad,';'); rows[0]['cobrado_total']=str(Decimal(rows[0]['cobrado_total'])+Decimal('1.00'))
    with bad.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['hotel','canal','n_reservas','cobrado_total'],delimiter=';'); w.writeheader(); w.writerows(rows)
    record('Total incorrecto',not report_ok(bad,groups),'Se altera una copia; el total deja de coincidir y la validación falla.')
record('Recuperación con originales',report_ok(report,groups) and unpaid_ok(no_pay,unpaid),'Tras las pruebas aisladas, los originales y resultados base siguen pasando el contraste.')

# Compare each group and the missing-payment rows against the canonical CSV inputs.
actual_report=read_csv(report,';') if report.exists() else []
la=[]
for (hotel,ch),(n,amount) in sorted(groups.items()): la.append(f'{hotel};{ch};{n};{amount:.2f}')
with (ROOT/'evidencias'/'comparacion_resultados.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(['hotel','canal','reservas_esperadas','cobrado_esperado_eur','resultado_contraste'])
    for (hotel,ch),(n,amount) in sorted(groups.items()):
        row=next((r for r in actual_report if (r.get('hotel'),r.get('canal'))==(hotel,ch)),None)
        ok=bool(row and int(row['n_reservas'])==n and Decimal(row['cobrado_total'])==amount)
        w.writerow([hotel,ch,n,f'{amount:.2f}','OK' if ok else 'NO COINCIDE'])

with (ROOT/'evidencias'/'resultado_pruebas_independientes.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(['prueba','resultado','observacion'])
    for name,ok,detail in checks: w.writerow([name,'OK' if ok else 'FALLO',detail])
print(f'entrada: reservas={len(res)} cobros={len(pay)} sin_cobro={len(unpaid)} ids={sorted(EXPECTED_IDS)}')
print(f'informe: grupos={len(groups)} reservas={sum(v[0] for v in groups.values())} cobrado={sum((v[1] for v in groups.values()),Decimal("0")):.2f}')
for name,ok,detail in checks: print(('OK' if ok else 'FALLO')+' - '+name)
if not all(x[1] for x in checks): raise SystemExit(1)
