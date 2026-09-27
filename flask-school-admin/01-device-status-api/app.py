from flask import Flask, jsonify, request

app = Flask(__name__)
devices = {
    "lab-pc-01": {"online": True, "room": "LAB"},
    "lab-pc-02": {"online": False, "room": "LAB"},
}

@app.get("/api/devices")
def list_devices():
    online = request.args.get("online")
    rows = [{"hostname": name, **data} for name, data in devices.items()]
    if online is not None:
        wanted = online.lower() in {"1", "true", "yes"}
        rows = [row for row in rows if row["online"] is wanted]
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)
