# app.py
# -*- coding: utf-8 -*-

import os
import glob
import time
import threading
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template_string, flash
from werkzeug.utils import secure_filename

import serial


# =========================
# CONFIG
# =========================
SERIAL_PORT_DEFAULT = "/dev/ttyUSB0"
BAUD_RATE_DEFAULT = 4800
TIMEOUT_DEFAULT = 1
DELAY_DEFAULT = 0.10

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = Flask(__name__)
app.secret_key = "fanuc-dnc-secret-change-me"

transfer_lock = threading.Lock()


# =========================
# HTML
# =========================
HTML_INDEX = """
<!doctype html>
<html lang="th">
<head>
    <meta charset="utf-8">
    <title>Fanuc 0T G-code Transfer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 20px;
            color: #222;
        }
        .container {
            max-width: 1000px;
            margin: auto;
        }
        .card {
            background: white;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
            font-size: 28px;
        }
        h2 {
            margin-top: 0;
            font-size: 20px;
        }
        input, select, button {
            font-size: 16px;
            padding: 10px;
            margin: 5px 0;
        }
        input[type="file"] {
            width: 100%;
            background: #fafafa;
            border: 1px solid #ccc;
            border-radius: 8px;
        }
        button {
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn-upload {
            background: #2563eb;
            color: white;
        }
        .btn-send {
            background: #16a34a;
            color: white;
        }
        .btn-delete {
            background: #dc2626;
            color: white;
        }
        .warning {
            background: #fff7ed;
            border-left: 6px solid #f97316;
            padding: 12px;
            border-radius: 8px;
            line-height: 1.6;
        }
        .msg {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .success {
            background: #dcfce7;
        }
        .error {
            background: #fee2e2;
        }
        .info {
            background: #dbeafe;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #111827;
            color: white;
            text-align: left;
        }
        th, td {
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
        }
        .setting-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }
        .small {
            font-size: 13px;
            color: #555;
        }
        pre {
            background: #111827;
            color: #e5e7eb;
            padding: 14px;
            border-radius: 10px;
            overflow-x: auto;
            max-height: 280px;
        }
        .filename {
            font-weight: bold;
            font-size: 17px;
        }
    </style>
</head>
<body>
<div class="container">

    <div class="card">
        <h1>Fanuc 0T G-code Transfer</h1>
        <div class="warning">
            วิธีใช้: อัพโหลดไฟล์ G-code → ที่หน้าเครื่อง Fanuc กด <b>READ</b> ให้ขึ้น <b>LSK กระพริบ</b> → กลับมากดปุ่ม <b>ส่งเข้าเครื่อง</b>
            <br>
            ค่าเริ่มต้น: <b>7 bits / Even parity / 2 stop bits / XON-XOFF</b>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="card">
            {% for category, message in messages %}
                <div class="msg {{ category }}">{{ message }}</div>
            {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <div class="card">
        <h2>1) อัพโหลดไฟล์ G-code</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="gcode_file" required>
            <br>
            <button class="btn-upload" type="submit">อัพโหลดไฟล์</button>
        </form>
        <p class="small">
            ตั้งชื่อไฟล์แบบ O5556 ได้ ไม่จำเป็นต้องมีนามสกุล แต่ในไฟล์ควรมีโปรแกรมเช่น O5556 อยู่ด้านใน
        </p>
    </div>

    <div class="card">
        <h2>2) รายการไฟล์ที่อัพโหลดแล้ว</h2>

        {% if files %}
            <table>
                <tr>
                    <th>ไฟล์</th>
                    <th>ขนาด</th>
                    <th>วันที่</th>
                    <th>ส่งเข้า Fanuc</th>
                </tr>

                {% for f in files %}
                <tr>
                    <td>
                        <div class="filename">{{ f.name }}</div>
                        <details>
                            <summary>ดูตัวอย่างไฟล์</summary>
                            <pre>{{ f.preview }}</pre>
                        </details>
                    </td>
                    <td>{{ f.size }} bytes</td>
                    <td>{{ f.mtime }}</td>
                    <td>
                        <form method="post" action="{{ url_for('send_file_to_fanuc') }}">
                            <input type="hidden" name="filename" value="{{ f.name }}">

                            <div class="setting-row">
                                <label>Port:</label>
                                <select name="serial_port">
                                    {% for p in ports %}
                                        <option value="{{ p }}" {% if p == default_port %}selected{% endif %}>{{ p }}</option>
                                    {% endfor %}
                                </select>
                            </div>

                            <div class="setting-row">
                                <label>Baud:</label>
                                <input type="number" name="baud_rate" value="{{ default_baud }}" style="width:100px;">
                            </div>

                            <div class="setting-row">
                                <label>Delay/line:</label>
                                <input type="text" name="delay" value="{{ default_delay }}" style="width:80px;">
                                <span class="small">วินาที</span>
                            </div>

                            <button class="btn-send" type="submit"
                                onclick="return confirm('กด READ ที่หน้า Fanuc ให้ขึ้น LSK กระพริบแล้วหรือยัง?')">
                                ส่งเข้าเครื่อง
                            </button>
                        </form>

                        <form method="post" action="{{ url_for('delete_file') }}"
                              onsubmit="return confirm('ลบไฟล์นี้หรือไม่?')">
                            <input type="hidden" name="filename" value="{{ f.name }}">
                            <button class="btn-delete" type="submit">ลบไฟล์</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        {% else %}
            <p>ยังไม่มีไฟล์ G-code</p>
        {% endif %}
    </div>

</div>
</body>
</html>
"""


HTML_RESULT = """
<!doctype html>
<html lang="th">
<head>
    <meta charset="utf-8">
    <title>Transfer Result</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 20px;
            color: #222;
        }
        .container {
            max-width: 900px;
            margin: auto;
        }
        .card {
            background: white;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 3px 12px rgba(0,0,0,0.08);
        }
        pre {
            background: #111827;
            color: #e5e7eb;
            padding: 14px;
            border-radius: 10px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        a {
            display: inline-block;
            background: #2563eb;
            color: white;
            text-decoration: none;
            padding: 12px 16px;
            border-radius: 8px;
            font-weight: bold;
        }
        .ok {
            color: #16a34a;
            font-weight: bold;
        }
        .bad {
            color: #dc2626;
            font-weight: bold;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        {% if success %}
            <h1 class="ok">ส่งไฟล์สำเร็จ</h1>
        {% else %}
            <h1 class="bad">ส่งไฟล์ไม่สำเร็จ</h1>
        {% endif %}

        <p><b>ไฟล์:</b> {{ filename }}</p>
        <p><b>Port:</b> {{ serial_port }}</p>
        <p><b>Baud:</b> {{ baud_rate }}</p>
        <p><b>Delay:</b> {{ delay }} sec/line</p>
    </div>

    <div class="card">
        <h2>Log</h2>
        <pre>{{ log }}</pre>
    </div>

    <a href="{{ url_for('index') }}">กลับหน้าแรก</a>
</div>
</body>
</html>
"""


# =========================
# HELPER FUNCTIONS
# =========================
def list_serial_ports():
    patterns = [
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/ttyAMA*",
        "/dev/ttyS*"
    ]

    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))

    ports = sorted(list(set(ports)))

    if SERIAL_PORT_DEFAULT not in ports:
        ports.insert(0, SERIAL_PORT_DEFAULT)

    return ports


def get_safe_path(filename):
    filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, filename))
    upload_root = os.path.abspath(UPLOAD_DIR)

    if not file_path.startswith(upload_root):
        raise ValueError("Invalid file path")

    return file_path


def read_preview(file_path, max_lines=40):
    lines = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append("...")
                    break
                lines.append(line.rstrip("\n"))
    except Exception as e:
        lines.append("อ่านตัวอย่างไฟล์ไม่ได้: {0}".format(e))

    return "\n".join(lines)


def list_uploaded_files():
    result = []

    for name in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, name)

        if not os.path.isfile(file_path):
            continue

        stat = os.stat(file_path)

        result.append({
            "name": name,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "preview": read_preview(file_path)
        })

    result.sort(key=lambda x: x["mtime"], reverse=True)
    return result


def save_uploaded_file(upload_file):
    original_name = upload_file.filename

    if not original_name:
        raise ValueError("ไม่มีชื่อไฟล์")

    filename = secure_filename(original_name)

    # ถ้า secure_filename แล้วว่าง เช่น ชื่อไฟล์เป็นภาษาไทยล้วน
    if not filename:
        filename = "gcode_{0}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))

    file_path = os.path.join(UPLOAD_DIR, filename)

    # กันชื่อซ้ำ
    if os.path.exists(file_path):
        name, ext = os.path.splitext(filename)
        filename = "{0}_{1}{2}".format(
            name,
            datetime.now().strftime("%Y%m%d_%H%M%S"),
            ext
        )
        file_path = os.path.join(UPLOAD_DIR, filename)

    upload_file.save(file_path)
    return filename


def send_gcode_file(file_path, serial_port, baud_rate, delay, timeout):
    log_lines = []
    ser = None
    sent_count = 0

    try:
        log_lines.append("เปิดพอร์ต {0} baud {1}".format(serial_port, baud_rate))

        ser = serial.Serial(
            port=serial_port,
            baudrate=baud_rate,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_TWO,
            xonxoff=True,
            rtscts=False,
            timeout=timeout
        )

        log_lines.append("เชื่อมต่อสำเร็จ")
        log_lines.append("เริ่มส่งข้อมูล...")
        log_lines.append("")

        with open(file_path, "r", encoding="utf-8-sig", errors="strict") as file:
            for line_no, line in enumerate(file, start=1):
                clean_line = line.strip()

                if not clean_line:
                    continue

                try:
                    send_data = (clean_line + "\r\n").encode("ascii")
                except UnicodeEncodeError:
                    raise ValueError(
                        "บรรทัดที่ {0} มีตัวอักษรที่ไม่ใช่ ASCII: {1}".format(
                            line_no,
                            clean_line
                        )
                    )

                ser.write(send_data)
                ser.flush()

                sent_count += 1
                log_lines.append("LINE {0}: {1}".format(line_no, clean_line))

                time.sleep(delay)

        log_lines.append("")
        log_lines.append("ส่งเสร็จแล้ว จำนวน {0} บรรทัด".format(sent_count))
        return True, "\n".join(log_lines)

    except Exception as e:
        log_lines.append("")
        log_lines.append("ERROR: {0}".format(e))
        return False, "\n".join(log_lines)

    finally:
        if ser is not None and ser.is_open:
            ser.close()
            log_lines.append("ปิดพอร์ตแล้ว")


# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            upload_file = request.files.get("gcode_file")

            if upload_file is None or upload_file.filename == "":
                flash("กรุณาเลือกไฟล์ก่อน", "error")
                return redirect(url_for("index"))

            filename = save_uploaded_file(upload_file)
            flash("อัพโหลดไฟล์สำเร็จ: {0}".format(filename), "success")

        except Exception as e:
            flash("อัพโหลดไม่สำเร็จ: {0}".format(e), "error")

        return redirect(url_for("index"))

    return render_template_string(
        HTML_INDEX,
        files=list_uploaded_files(),
        ports=list_serial_ports(),
        default_port=SERIAL_PORT_DEFAULT,
        default_baud=BAUD_RATE_DEFAULT,
        default_delay=DELAY_DEFAULT
    )


@app.route("/send", methods=["POST"])
def send_file_to_fanuc():
    filename = request.form.get("filename", "")
    serial_port = request.form.get("serial_port", SERIAL_PORT_DEFAULT)

    try:
        baud_rate = int(request.form.get("baud_rate", BAUD_RATE_DEFAULT))
    except:
        baud_rate = BAUD_RATE_DEFAULT

    try:
        delay = float(request.form.get("delay", DELAY_DEFAULT))
    except:
        delay = DELAY_DEFAULT

    if delay < 0.01:
        delay = 0.01

    if delay > 2.0:
        delay = 2.0

    file_path = get_safe_path(filename)

    if not os.path.exists(file_path):
        flash("ไม่พบไฟล์: {0}".format(filename), "error")
        return redirect(url_for("index"))

    acquired = transfer_lock.acquire(False)

    if not acquired:
        flash("ตอนนี้กำลังส่งไฟล์อื่นอยู่ กรุณารอให้เสร็จก่อน", "error")
        return redirect(url_for("index"))

    try:
        success, log = send_gcode_file(
            file_path=file_path,
            serial_port=serial_port,
            baud_rate=baud_rate,
            delay=delay,
            timeout=TIMEOUT_DEFAULT
        )
    finally:
        transfer_lock.release()

    return render_template_string(
        HTML_RESULT,
        success=success,
        filename=filename,
        serial_port=serial_port,
        baud_rate=baud_rate,
        delay=delay,
        log=log
    )


@app.route("/delete", methods=["POST"])
def delete_file():
    filename = request.form.get("filename", "")

    try:
        file_path = get_safe_path(filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            flash("ลบไฟล์แล้ว: {0}".format(filename), "success")
        else:
            flash("ไม่พบไฟล์ที่ต้องการลบ", "error")

    except Exception as e:
        flash("ลบไฟล์ไม่สำเร็จ: {0}".format(e), "error")

    return redirect(url_for("index"))


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )