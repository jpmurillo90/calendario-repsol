import os,json,calendar,smtplib,ssl,urllib.request
from datetime import date,datetime,timedelta
from email.message import EmailMessage

GIST_ID=os.environ['GIST_ID']; TOKEN=os.environ['GIST_TOKEN']
MODE=os.environ.get('RESUMEN_MODO','semanal').lower()
URL=f'https://api.github.com/gists/{GIST_ID}'
req=urllib.request.Request(URL,headers={'Authorization':f'Bearer {TOKEN}','Accept':'application/vnd.github+json'})
with urllib.request.urlopen(req,timeout=20) as r: gist=json.load(r)
def load(name,default):
    f=gist.get('files',{}).get(name)
    if not f:return default
    if f.get('truncated') and f.get('raw_url'):
        q=urllib.request.Request(f['raw_url'],headers={'Authorization':f'Bearer {TOKEN}'})
        with urllib.request.urlopen(q,timeout=20) as rr:return json.load(rr)
    return json.loads(f.get('content') or json.dumps(default))

cfg=load('config_notificaciones_repsol.json',{})
flag='resumen_coordinacion_semanal' if MODE=='semanal' else 'resumen_coordinacion_mensual'
if not cfg.get(flag,False):
    print('Resumen desactivado en configuración:',flag); raise SystemExit(0)
tecnicos=load('tecnicos_repsol.json',{}); datos=load('datos_tecnicos_repsol.json',{}); guardias=load('guardias_repsol.json',[]); prl=load('prl_repsol.json',{}); seg=load('seguimiento_ci_repsol.json',{})
hoy=date.today()
if MODE=='semanal':
    fin=(hoy-timedelta(days=hoy.weekday()))-timedelta(days=1); ini=fin-timedelta(days=6); periodo=f'{ini:%d/%m/%Y} – {fin:%d/%m/%Y}'
else:
    primero=date(hoy.year,hoy.month,1); fin=primero-timedelta(days=1); ini=date(fin.year,fin.month,1); periodo=fin.strftime('%m/%Y')

def parse_key(k):
    p=k.split('|')
    if len(p)==3:p=['2026']+p
    try:return date(int(p[0]),int(p[2]),int(p[3])),p[1]
    except:return None,None
def tipo(v):return v.get('tipo','') if isinstance(v,dict) else str(v or '')
aus=[]
for k,v in datos.items():
    f,t=parse_key(k)
    if f and ini<=f<=fin and tipo(v):aus.append((f,t,tecnicos.get(t,{}).get('ci',''),tipo(v)))
gs=[]
for g in guardias:
    try:gi=date.fromisoformat(g['inicio']);gf=date.fromisoformat(g['fin'])
    except:continue
    if gi<=fin and gf>=ini:gs.append(g)
pr=[]
for t,p in prl.items():
    try:f=date.fromisoformat(p.get('fecha',''));dias=(f-hoy).days
    except:f=None;dias=None
    if dias is None or dias<=60:pr.append((tecnicos.get(t,{}).get('ci',''),t,f,dias))
centros=sorted({x.get('ci','') for x in tecnicos.values() if x.get('ci')})
def dia_seg(ci,f):
    raw=(seg.get('diario',{}).get(ci,{}).get(f.isoformat(),{}) if isinstance(seg,dict) and 'diario' in seg else seg.get(f'{f.isoformat()}|{ci}',{}))
    out={'Parches':0,'AV':0,'BCK':0}
    aliases={'Parches':'Parches','AV':'Antivirus','BCK':'Backup'}
    for g in out:
        obj=raw.get(g,{})
        if isinstance(obj,dict) and any(r in obj for r in ('RS','RC','RCorp')):out[g]=sum(int(obj.get(r,0) or 0) for r in ('RS','RC','RCorp'))
        else:
            h=raw.get(aliases[g],{})
            out[g]=int(h.get('total',0) or 0) if isinstance(h,dict) else int(h or 0)
    return out
rows=[]
for ci in centros:
    acc={'Parches':0,'AV':0,'BCK':0}; f=ini
    while f<=fin:
        d=dia_seg(ci,f)
        for k in acc:acc[k]+=d[k]
        f+=timedelta(days=1)
    rows.append((ci,acc,sum(acc.values())))
css='body{font-family:Arial;background:#f5f8fa;color:#102a3a;padding:26px}.hero{background:#0d5869;color:#fff;padding:25px;border-radius:15px}.k{display:inline-block;background:#fff;border:1px solid #dbe4ea;border-radius:12px;padding:14px;margin:12px 8px 12px 0;min-width:150px}.n{font-size:25px;font-weight:800}table{border-collapse:collapse;width:100%;background:#fff;margin:12px 0 24px}th,td{border:1px solid #dbe4ea;padding:8px}th{background:#edf4f7}.muted{color:#718692;font-size:12px}'
total=sum(x[2] for x in rows)
out=[f'<html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="hero"><small>GESTIÓN TÉCNICOS CI · REPSOL</small><h1>Resumen de coordinación</h1><div>{periodo}</div></div>',f'<div class="k">Actividad<div class="n">{total}</div></div><div class="k">Ausencias/marcas<div class="n">{len(aus)}</div></div><div class="k">Guardias<div class="n">{len(gs)}</div></div><div class="k">PRL atención<div class="n">{len(pr)}</div></div><h2>Seguimiento operativo</h2><table><tr><th>CI</th><th>Parches</th><th>Antivirus</th><th>Backup</th><th>Total</th></tr>']
for ci,d,t in rows:out.append(f'<tr><td>{ci}</td><td>{d["Parches"]}</td><td>{d["AV"]}</td><td>{d["BCK"]}</td><td><b>{t}</b></td></tr>')
out.append('</table><h2>Ausencias y permisos</h2><table><tr><th>Fecha</th><th>CI</th><th>Técnico</th><th>Tipo</th></tr>')
for f,t,ci,tp in sorted(aus):out.append(f'<tr><td>{f:%d/%m/%Y}</td><td>{ci}</td><td>{t}</td><td>{tp}</td></tr>')
out.append('</table><h2>Guardias</h2><table><tr><th>CI</th><th>Técnico</th><th>Periodo</th></tr>')
for g in gs:out.append(f'<tr><td>{g.get("centro","")}</td><td>{g.get("tecnico","")}</td><td>{g.get("inicio","")} → {g.get("fin","")}</td></tr>')
out.append('</table><h2>PRL que requiere atención</h2><table><tr><th>CI</th><th>Técnico</th><th>Caducidad</th><th>Estado</th></tr>')
for ci,t,f,d in pr:out.append(f'<tr><td>{ci}</td><td>{t}</td><td>{f.strftime("%d/%m/%Y") if f else "Sin fecha"}</td><td>{"Sin fecha" if d is None else ("Caducado" if d<0 else str(d)+" días")}</td></tr>')
out.append(f'</table><p class="muted">Generado {datetime.now():%d/%m/%Y %H:%M}</p></body></html>'); html=''.join(out)
user=os.environ['GMAIL_USUARIO']; pwd=os.environ['GMAIL_APP_PASSWORD'].replace(' ',''); dest=os.environ['GMAIL_DESTINATARIO']
msg=EmailMessage();msg['From']=user;msg['To']=dest;msg['Subject']=f'Resumen de coordinación · {MODE.capitalize()} · {periodo}';msg.set_content('Resumen de coordinación en formato HTML.');msg.add_alternative(html,subtype='html')
with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context()) as smtp:smtp.login(user,pwd);smtp.send_message(msg)
print('Enviado',MODE,'a',dest)
