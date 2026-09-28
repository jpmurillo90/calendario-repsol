import os
import json
import ssl
import smtplib
from datetime import date, datetime
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

GMAIL_USUARIO = os.environ["GMAIL_USUARIO"].strip()
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
GMAIL_DESTINATARIO = os.environ["GMAIL_DESTINATARIO"].strip()
GIST_ID = os.environ["GIST_ID"].strip()
GIST_TOKEN = os.environ["GIST_TOKEN"].strip()

PRL_FILE = "prl_repsol.json"


def leer_prl_gist():
    req = Request(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"Bearer {GIST_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "gestion-tecnicos-ci-prl",
        },
    )
    with urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    archivo = data.get("files", {}).get(PRL_FILE)
    if not archivo:
        raise RuntimeError(f"No existe {PRL_FILE} en el Gist.")

    if archivo.get("truncated"):
        raw_url = archivo.get("raw_url")
        if not raw_url:
            raise RuntimeError(f"{PRL_FILE} está truncado y no tiene raw_url.")
        req_raw = Request(
            raw_url,
            headers={
                "Authorization": f"Bearer {GIST_TOKEN}",
                "User-Agent": "gestion-tecnicos-ci-prl",
            },
        )
        with urlopen(req_raw, timeout=20) as response:
            contenido = response.read().decode("utf-8")
    else:
        contenido = archivo.get("content", "{}")

    return json.loads(contenido)


def clasificar(fecha_caducidad, hoy):
    dias = (fecha_caducidad - hoy).days

    if dias < 0:
        return dias, "CADUCADO", "Revisar la situación y gestionar la renovación."
    if dias == 0:
        return dias, "CADUCA HOY", "Gestionar la cita del reconocimiento."
    if dias <= 7:
        return dias, f"CADUCA EN {dias} DÍAS", "Gestionar la cita del reconocimiento."
    if dias <= 15:
        return dias, f"CADUCA EN {dias} DÍAS", "Gestionar la cita del reconocimiento."
    if dias <= 30:
        return dias, f"CADUCA EN {dias} DÍAS", "Gestionar la cita del reconocimiento."
    if dias <= 60:
        return dias, f"CADUCA EN {dias} DÍAS", "Planificar la renovación."
    return dias, "VIGENTE", ""


def debe_avisar(dias):
    """
    GitHub Action se ejecuta L-V.
    - Caducado o <= 7 días: aviso cada día laborable.
    - 15, 30 y 60 días: aviso en esos hitos.
    """
    return dias < 0 or 0 <= dias <= 7 or dias in (15, 30, 60)


def preparar_avisos(registros):
    hoy = date.today()
    avisos = []

    for tecnico, datos in registros.items():
        fecha_txt = (datos or {}).get("fecha")
        if not fecha_txt:
            continue

        try:
            caducidad = date.fromisoformat(fecha_txt)
        except (TypeError, ValueError):
            continue

        dias, estado, accion = clasificar(caducidad, hoy)

        if debe_avisar(dias):
            avisos.append({
                "tecnico": tecnico,
                "caducidad": caducidad,
                "dias": dias,
                "estado": estado,
                "accion": accion,
                "obs": (datos or {}).get("obs", ""),
            })

    return sorted(avisos, key=lambda x: (x["dias"], x["tecnico"]))


def enviar_email(avisos):
    if not avisos:
        print("No hay avisos PRL que enviar hoy.")
        return

    asunto = f"⚠️ PRL · {len(avisos)} reconocimiento{'s' if len(avisos) != 1 else ''} requiere{'n' if len(avisos) != 1 else ''} revisión"

    lineas = [
        "GESTIÓN DE TÉCNICOS CI · AVISO AUTOMÁTICO PRL",
        "",
        f"Fecha de revisión: {date.today().strftime('%d/%m/%Y')}",
        "",
    ]

    for aviso in avisos:
        lineas.extend([
            aviso["tecnico"],
            f"Caducidad: {aviso['caducidad'].strftime('%d/%m/%Y')}",
            f"Estado: {aviso['estado']}",
            f"Acción: {aviso['accion']}",
        ])
        if aviso["obs"]:
            lineas.append(f"Observaciones: {aviso['obs']}")
        lineas.append("")

    lineas.extend([
        "Este mensaje ha sido generado automáticamente por Gestión de Técnicos CI.",
        "Revisa o actualiza la fecha del reconocimiento en la aplicación cuando corresponda.",
    ])

    email = EmailMessage()
    email["From"] = GMAIL_USUARIO
    email["To"] = GMAIL_DESTINATARIO
    email["Subject"] = asunto
    email.set_content("\n".join(lineas))

    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=20) as servidor:
        servidor.login(GMAIL_USUARIO, GMAIL_APP_PASSWORD)
        servidor.send_message(email)

    print(f"Correo enviado a {GMAIL_DESTINATARIO}: {len(avisos)} aviso(s).")


def main():
    try:
        registros = leer_prl_gist()
        avisos = preparar_avisos(registros)
        enviar_email(avisos)
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError, smtplib.SMTPException) as exc:
        print(f"ERROR: {exc}")
        raise


if __name__ == "__main__":
    main()
