from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import shlex
import os

app = FastAPI(title="BlueOS Net Shaper")

# Serve the UI
@app.get("/")
def root():
    ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {"message": "BlueOS Net Shaper API"}

# Automatically detect interface (prefers eth0, usb0, tether0, wlan0)
PREFERRED = ["eth0", "usb0", "tether0", "wlan0"]

def detect_iface():
    try:
        out = subprocess.check_output(["ip", "-o", "link"], text=True)
        for p in PREFERRED:
            if f"{p}:" in out:
                return p
        # fallback: get first interface that is not loopback
        for line in out.splitlines():
            if ": lo:" in line: continue
            # form: '2: eth0: <BROADCAST,...>'
            parts = line.split(':')
            if len(parts) > 1:
                name = parts[1].strip()
                if name:
                    return name
    except Exception:
        pass
    return os.environ.get("IFACE", "eth0")

IFACE = detect_iface()
IFB = "ifb0"

class BWModel(BaseModel):
    rate_kbit: int

class PortMarkModel(BaseModel):
    remote_ip: str
    port: int
    mark: int
    direction: str  # "in" or "out"


def run(cmd):
    try:
        p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as e:
        raise RuntimeError(str(e))
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()

@app.get("/status")
def status():
    return {"iface": IFACE}

@app.post("/bandwidth/out/{rate_kbit}")
def set_out_bandwidth(rate_kbit: int):
    if rate_kbit <= 0:
        raise HTTPException(status_code=400, detail="rate_kbit must be > 0")
    try:
        # remove old rule
        try: run(f"tc qdisc del dev {IFACE} root")
        except: pass
        run(f"tc qdisc add dev {IFACE} root handle 1: htb default 30")
        run(f"tc class add dev {IFACE} parent 1: classid 1:1 htb rate {rate_kbit}kbit")
        run(f"tc class add dev {IFACE} parent 1:1 classid 1:30 htb rate {rate_kbit}kbit")
        return {"status": "ok", "iface": IFACE, "rate_kbit": rate_kbit}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bandwidth/clear")
def clear_bandwidth():
    try:
        run(f"tc qdisc del dev {IFACE} root")
        # try to remove ifb
        try:
            run(f"ip link set dev {IFB} down")
            run(f"ip link delete {IFB}")
        except: pass
        return {"status": "cleared"}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/loss/out/{percent}")
def loss_out(percent: int):
    if not (0 <= percent <= 100):
        raise HTTPException(status_code=400, detail="percent must be 0-100")
    try:
        run(f"tc qdisc replace dev {IFACE} root netem loss {percent}%")
        return {"status": "ok", "iface": IFACE, "loss": percent}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delay/out/{ms}")
def delay_out(ms: int):
    if ms < 0:
        raise HTTPException(status_code=400, detail="ms must be >= 0")
    try:
        run(f"tc qdisc replace dev {IFACE} root netem delay {ms}ms")
        return {"status": "ok", "iface": IFACE, "delay_ms": ms}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/loss/in/{percent}")
def loss_in(percent: int):
    if not (0 <= percent <= 100):
        raise HTTPException(status_code=400, detail="percent must be 0-100")
    try:
        # create ifb and redirect ingress to ifb
        run("modprobe ifb || true")
        # create ifb if it doesn't exist
        try:
            run(f"ip link add {IFB} type ifb")
            run(f"ip link set dev {IFB} up")
        except: pass
        try: run(f"tc qdisc del dev {IFACE} ingress")
        except: pass
        run(f"tc qdisc add dev {IFACE} ingress")
        run(f"tc filter add dev {IFACE} parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev {IFB}")
        run(f"tc qdisc replace dev {IFB} root netem loss {percent}%")
        return {"status": "ok", "iface": IFACE, "loss_in_percent": percent}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mark-and-limit")
def mark_and_limit(payload: PortMarkModel):
    """
    Mark traffic (iptables mangle) and apply tc only to packets with the mark.
    Useful for limiting only connections to a specific IP/port.
    """
    try:
        # iptables
        run(f"iptables -t mangle -A OUTPUT -p tcp -d {payload.remote_ip} --dport {payload.port} -j MARK --set-mark {payload.mark}")
        # create qdisc
        try: run(f"tc qdisc del dev {IFACE} root")
        except: pass
        run(f"tc qdisc add dev {IFACE} root handle 1: prio")
        run(f"tc qdisc add dev {IFACE} parent 1:3 netem loss 50%")
        run(f"tc filter add dev {IFACE} protocol ip parent 1:0 prio 1 handle {payload.mark} fw flowid 1:3")
        return {"status":"ok","marked":payload.dict()}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/iptables/clear")
def iptables_clear():
    try:
        run("iptables -t mangle -F")
        return {"status":"ok"}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

