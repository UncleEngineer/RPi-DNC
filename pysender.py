import serial
import time
from pathlib import Path

PORT = "COM5"          # แก้เป็น COM ของ USB-RS232
BAUD = 4800            # ให้ตรงกับ Fanuc parameter #0552
GCODE_FILE = "test.nc"

def normalize_gcode(text: str) -> bytes:
    # แปลง line ending ให้สม่ำเสมอ
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # ใส่ % หัวท้าย ถ้ายังไม่มี
    if not lines[0].startswith("%"):
        lines.insert(0, "%")
    if not lines[-1].startswith("%"):
        lines.append("%")

    # Fanuc รุ่นเก่าชอบ ASCII + CRLF
    output = "\r\n".join(lines) + "\r\n"
    return output.encode("ascii", errors="ignore")

def main():
    data = normalize_gcode(Path(GCODE_FILE).read_text(encoding="utf-8"))

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        bytesize=serial.SEVENBITS,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_TWO,
        timeout=0.2,
        write_timeout=2,
        xonxoff=True,     # ใช้ XON/XOFF
        rtscts=False,
        dsrdtr=False,
    )

    print(f"Opened {PORT} at {BAUD} 7E2")
    print("ตั้งหน้าเครื่องเป็น EDIT > PRGRM > INPUT / READ แล้วให้ LSK กระพริบก่อน")
    input("พร้อมแล้วกด Enter เพื่อส่ง...")

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # ส่งทีละบรรทัด ช้า ๆ กัน buffer เครื่องเก่าล้น
    for line in data.splitlines(keepends=True):
        ser.write(line)
        ser.flush()
        print(line.decode("ascii", errors="ignore").rstrip())
        time.sleep(0.03)  # ถ้ายัง error ให้เพิ่มเป็น 0.05-0.10

    time.sleep(0.5)
    ser.close()
    print("ส่งเสร็จแล้ว ดูที่หน้าเครื่องว่ามี O-number เข้าไปหรือยัง")

if __name__ == "__main__":
    main()