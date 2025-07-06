from flask import Flask, render_template, request
import os
import json
import asyncio
from maher_zubair_baileys import default as Gifted_Tech, useMultiFileAuthState, delay, makeCacheableSignalKeyStore, Browsers
import pino
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send_message():
    creds_file = request.files.get("creds")
    msg_file = request.files.get("message")
    number = request.form.get("number")
    delay_sec = int(request.form.get("delay", 5))

    if not creds_file or not msg_file or not number:
        return "Missing fields", 400

    creds_path = os.path.join(UPLOAD_FOLDER, "creds.json")
    msg_path = os.path.join(UPLOAD_FOLDER, "messages.txt")
    creds_file.save(creds_path)
    msg_file.save(msg_path)

    asyncio.run(start_sending(creds_path, msg_path, number, delay_sec))
    return "✅ Messages sent successfully"

async def start_sending(creds_path, msg_path, number, delay_sec):
    session_dir = os.path.join(UPLOAD_FOLDER, "session")
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    os.makedirs(session_dir, exist_ok=True)

    with open(creds_path, "r") as f:
        creds = json.load(f)

    with open(os.path.join(session_dir, "creds.json"), "w") as f:
        json.dump(creds, f)

    auth = await useMultiFileAuthState(session_dir)
    client = Gifted_Tech(
        auth={
            "creds": auth.state.creds,
            "keys": makeCacheableSignalKeyStore(auth.state.keys, pino.Pino({"level": "silent"}))
        },
        printQRInTerminal=False,
        logger=pino.Pino({"level": "silent"}),
        browser=Browsers.macOS("Desktop")
    )

    async def send_loop():
        with open(msg_path, "r") as f:
            messages = [line.strip() for line in f if line.strip()]
        jid = number + "@s.whatsapp.net"
        while True:
            for msg in messages:
                try:
                    await client.sendMessage(jid, { "text": msg })
                    print("✅ Sent:", msg)
                    await delay(delay_sec * 1000)
                except Exception as e:
                    print("❌ Error:", e)
                    await delay(delay_sec * 2000)

    client.ev.on("connection.update", lambda x: print("Connection update:", x.get("connection")))
    await send_loop()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
