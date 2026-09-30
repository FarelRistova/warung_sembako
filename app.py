"""
Sistem Kasir Warung Sembako
---------------------------
Backend: Flask + SQLite (database otomatis dibuat di file warung.db)
Jalankan: python app.py  lalu buka http://127.0.0.1:5000
"""
import os
import sqlite3
from datetime import datetime, date

from flask import Flask, g, jsonify, render_template, request, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "warung.db")

# Ganti nama warung lewat variabel lingkungan NAMA_WARUNG, atau edit langsung di sini.
NAMA_WARUNG = os.environ.get("NAMA_WARUNG", "Warung Sembako Berkah")
ALAMAT_WARUNG = os.environ.get("ALAMAT_WARUNG", "Jl. Mawar No. 12")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SKEMA = """
CREATE TABLE IF NOT EXISTS produk (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kode      TEXT UNIQUE,
    nama      TEXT NOT NULL,
    kategori  TEXT NOT NULL DEFAULT 'Lainnya',
    satuan    TEXT NOT NULL DEFAULT 'pcs',
    harga     INTEGER NOT NULL CHECK (harga >= 0),
    stok      REAL NOT NULL DEFAULT 0,
    stok_min  REAL NOT NULL DEFAULT 5,
    aktif     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transaksi (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    no_nota  TEXT NOT NULL UNIQUE,
    waktu    TEXT NOT NULL,
    total    INTEGER NOT NULL,
    bayar    INTEGER NOT NULL,
    kembali  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transaksi_item (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id  INTEGER NOT NULL REFERENCES transaksi(id),
    produk_id     INTEGER,
    nama          TEXT NOT NULL,
    satuan        TEXT NOT NULL,
    harga         INTEGER NOT NULL,
    qty           REAL NOT NULL,
    subtotal      INTEGER NOT NULL
);
"""

# (kode, nama, kategori, satuan, harga, stok, stok_min)
CONTOH_PRODUK = [
    ("BRS-5", "Beras Premium 5 kg", "Beras", "karung", 68000, 24, 5),
    ("BRS-1", "Beras Medium (eceran)", "Beras", "kg", 13500, 60, 10),
    ("MYK-1", "Minyak Goreng 1 L", "Minyak", "botol", 18000, 30, 6),
    ("MYK-2", "Minyak Goreng 2 L", "Minyak", "botol", 35000, 18, 4),
    ("GLA-1", "Gula Pasir", "Bumbu & Gula", "kg", 17500, 40, 8),
    ("GRM-1", "Garam Halus", "Bumbu & Gula", "bungkus", 3000, 50, 10),
    ("TPG-1", "Tepung Terigu 1 kg", "Tepung", "bungkus", 12000, 25, 6),
    ("TLR-1", "Telur Ayam", "Lauk", "kg", 29000, 20, 5),
    ("MIE-1", "Mie Instan Goreng", "Mie", "bungkus", 3500, 120, 20),
    ("MIE-2", "Mie Instan Kuah", "Mie", "bungkus", 3200, 100, 20),
    ("KCP-1", "Kecap Manis 275 ml", "Bumbu & Gula", "botol", 14500, 15, 4),
    ("SRD-1", "Sarden Kaleng", "Kalengan", "kaleng", 11500, 12, 4),
    ("TEH-1", "Teh Celup isi 25", "Minuman", "kotak", 7500, 22, 5),
    ("KPI-1", "Kopi Sachet", "Minuman", "renceng", 12000, 30, 6),
    ("SUSU-1", "Susu Kental Manis", "Minuman", "kaleng", 13000, 20, 5),
    ("SBN-1", "Sabun Mandi", "Kebersihan", "pcs", 4500, 40, 8),
    ("DTG-1", "Deterjen Bubuk 800 g", "Kebersihan", "bungkus", 16500, 14, 4),
    ("KRP-1", "Kerupuk Putih", "Camilan", "bungkus", 6000, 3, 5),
    ("KDL-1", "Kacang Hijau", "Kacang", "kg", 24000, 10, 3),
    ("BWM-1", "Bawang Merah", "Sayur & Bumbu Dapur", "kg", 38000, 8, 3),
]


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SKEMA)
    jumlah = db.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
    if jumlah == 0:
        db.executemany(
            "INSERT INTO produk (kode, nama, kategori, satuan, harga, stok, stok_min) "
            "VALUES (?,?,?,?,?,?,?)",
            CONTOH_PRODUK,
        )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Filter template
# ---------------------------------------------------------------------------
@app.template_filter("rp")
def format_rupiah(nilai):
    return "Rp " + f"{int(round(nilai or 0)):,}".replace(",", ".")


@app.template_filter("angka")
def format_angka(nilai):
    teks = f"{float(nilai):.3f}".rstrip("0").rstrip(".")
    if "." in teks:
        depan, belakang = teks.split(".")
        return f"{int(depan):,}".replace(",", ".") + "," + belakang
    return f"{int(teks):,}".replace(",", ".")


@app.template_filter("waktu")
def format_waktu(teks):
    return datetime.fromisoformat(teks).strftime("%d/%m/%Y %H:%M")


@app.context_processor
def data_umum():
    return {"nama_warung": NAMA_WARUNG, "alamat_warung": ALAMAT_WARUNG}


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------
@app.route("/")
def halaman_kasir():
    return render_template("kasir.html")


@app.route("/produk")
def halaman_produk():
    return render_template("produk.html")


@app.route("/riwayat")
def halaman_riwayat():
    db = get_db()
    tanggal = request.args.get("tanggal") or date.today().isoformat()
    try:
        date.fromisoformat(tanggal)
    except ValueError:
        tanggal = date.today().isoformat()

    ringkas = db.execute(
        "SELECT COUNT(*) AS jumlah, COALESCE(SUM(total),0) AS omzet "
        "FROM transaksi WHERE date(waktu) = ?",
        (tanggal,),
    ).fetchone()
    rata = ringkas["omzet"] / ringkas["jumlah"] if ringkas["jumlah"] else 0

    daftar = db.execute(
        "SELECT t.*, "
        "  (SELECT group_concat(nama || ' ×' || "
        "     CASE WHEN qty = CAST(qty AS INTEGER) THEN CAST(qty AS INTEGER) ELSE qty END, ', ') "
        "   FROM transaksi_item WHERE transaksi_id = t.id) AS isi "
        "FROM transaksi t WHERE date(t.waktu) = ? ORDER BY t.id DESC",
        (tanggal,),
    ).fetchall()

    terlaris = db.execute(
        "SELECT i.nama, i.satuan, SUM(i.qty) AS qty, SUM(i.subtotal) AS nilai "
        "FROM transaksi_item i JOIN transaksi t ON t.id = i.transaksi_id "
        "WHERE date(t.waktu) = ? GROUP BY i.nama, i.satuan "
        "ORDER BY nilai DESC LIMIT 5",
        (tanggal,),
    ).fetchall()

    menipis = db.execute(
        "SELECT * FROM produk WHERE aktif = 1 AND stok <= stok_min ORDER BY stok ASC"
    ).fetchall()

    return render_template(
        "riwayat.html",
        tanggal=tanggal,
        ringkas=ringkas,
        rata=rata,
        daftar=daftar,
        terlaris=terlaris,
        menipis=menipis,
    )


@app.route("/struk/<int:trx_id>")
def halaman_struk(trx_id):
    db = get_db()
    trx = db.execute("SELECT * FROM transaksi WHERE id = ?", (trx_id,)).fetchone()
    if trx is None:
        abort(404)
    item = db.execute(
        "SELECT * FROM transaksi_item WHERE transaksi_id = ? ORDER BY id", (trx_id,)
    ).fetchall()
    return render_template("struk.html", trx=trx, item=item)


# ---------------------------------------------------------------------------
# API Produk
# ---------------------------------------------------------------------------
def baris_ke_dict(baris):
    return {k: baris[k] for k in baris.keys()}


def baca_produk(data):
    """Validasi input produk. Mengembalikan (nilai, pesan_error)."""
    nama = str(data.get("nama", "")).strip()
    if not nama:
        return None, "Nama barang wajib diisi."
    try:
        harga = int(data.get("harga"))
        stok = float(data.get("stok", 0))
        stok_min = float(data.get("stok_min", 5))
    except (TypeError, ValueError):
        return None, "Harga dan stok harus berupa angka."
    if harga < 0 or stok < 0 or stok_min < 0:
        return None, "Harga dan stok tidak boleh negatif."
    kode = str(data.get("kode", "")).strip() or None
    return {
        "kode": kode,
        "nama": nama,
        "kategori": str(data.get("kategori", "")).strip() or "Lainnya",
        "satuan": str(data.get("satuan", "")).strip() or "pcs",
        "harga": harga,
        "stok": stok,
        "stok_min": stok_min,
    }, None


@app.get("/api/produk")
def api_daftar_produk():
    baris = get_db().execute(
        "SELECT * FROM produk WHERE aktif = 1 ORDER BY nama COLLATE NOCASE"
    ).fetchall()
    return jsonify([baris_ke_dict(b) for b in baris])


@app.post("/api/produk")
def api_tambah_produk():
    nilai, error = baca_produk(request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error), 400
    db = get_db()
    try:
        with db:
            cur = db.execute(
                "INSERT INTO produk (kode, nama, kategori, satuan, harga, stok, stok_min) "
                "VALUES (:kode, :nama, :kategori, :satuan, :harga, :stok, :stok_min)",
                nilai,
            )
    except sqlite3.IntegrityError:
        return jsonify(error="Kode barang sudah dipakai barang lain."), 400
    return jsonify(id=cur.lastrowid), 201


@app.put("/api/produk/<int:pid>")
def api_ubah_produk(pid):
    nilai, error = baca_produk(request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error), 400
    nilai["id"] = pid
    db = get_db()
    try:
        with db:
            cur = db.execute(
                "UPDATE produk SET kode=:kode, nama=:nama, kategori=:kategori, "
                "satuan=:satuan, harga=:harga, stok=:stok, stok_min=:stok_min "
                "WHERE id=:id AND aktif=1",
                nilai,
            )
    except sqlite3.IntegrityError:
        return jsonify(error="Kode barang sudah dipakai barang lain."), 400
    if cur.rowcount == 0:
        return jsonify(error="Barang tidak ditemukan."), 404
    return jsonify(ok=True)


@app.delete("/api/produk/<int:pid>")
def api_hapus_produk(pid):
    # Tidak dihapus permanen supaya riwayat transaksi tetap utuh.
    db = get_db()
    with db:
        cur = db.execute(
            "UPDATE produk SET aktif = 0, kode = NULL WHERE id = ? AND aktif = 1", (pid,)
        )
    if cur.rowcount == 0:
        return jsonify(error="Barang tidak ditemukan."), 404
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# API Transaksi
# ---------------------------------------------------------------------------
@app.post("/api/checkout")
def api_checkout():
    data = request.get_json(silent=True) or {}
    daftar = data.get("items") or []
    try:
        bayar = int(data.get("bayar"))
    except (TypeError, ValueError):
        return jsonify(error="Jumlah bayar tidak valid."), 400

    if not daftar:
        return jsonify(error="Keranjang masih kosong."), 400

    # Gabungkan baris dengan produk yang sama
    jumlah = {}
    for it in daftar:
        try:
            pid, qty = int(it["id"]), float(it["qty"])
        except (KeyError, TypeError, ValueError):
            return jsonify(error="Data keranjang tidak valid."), 400
        if qty <= 0:
            return jsonify(error="Jumlah barang harus lebih dari 0."), 400
        jumlah[pid] = jumlah.get(pid, 0) + qty

    db = get_db()
    baris_nota, total = [], 0
    # Harga dan stok selalu diambil dari database, bukan dari browser.
    for pid, qty in jumlah.items():
        p = db.execute("SELECT * FROM produk WHERE id = ? AND aktif = 1", (pid,)).fetchone()
        if p is None:
            return jsonify(error="Ada barang yang sudah tidak tersedia."), 400
        if qty > p["stok"] + 1e-9:
            return jsonify(error=f"Stok {p['nama']} tidak cukup (sisa {p['stok']:g} {p['satuan']})."), 400
        sub = int(round(p["harga"] * qty))
        total += sub
        baris_nota.append((p, qty, sub))

    if bayar < total:
        return jsonify(error="Uang bayar kurang dari total belanja."), 400

    sekarang = datetime.now()
    with db:
        urutan = db.execute(
            "SELECT COUNT(*) FROM transaksi WHERE date(waktu) = ?",
            (sekarang.date().isoformat(),),
        ).fetchone()[0] + 1
        no_nota = f"{sekarang:%y%m%d}-{urutan:04d}"

        cur = db.execute(
            "INSERT INTO transaksi (no_nota, waktu, total, bayar, kembali) VALUES (?,?,?,?,?)",
            (no_nota, sekarang.isoformat(timespec="seconds"), total, bayar, bayar - total),
        )
        trx_id = cur.lastrowid
        for p, qty, sub in baris_nota:
            db.execute(
                "INSERT INTO transaksi_item (transaksi_id, produk_id, nama, satuan, harga, qty, subtotal) "
                "VALUES (?,?,?,?,?,?,?)",
                (trx_id, p["id"], p["nama"], p["satuan"], p["harga"], qty, sub),
            )
            db.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (qty, p["id"]))

    return jsonify(id=trx_id, no_nota=no_nota, total=total, bayar=bayar, kembali=bayar - total), 201


init_db()

if __name__ == "__main__":
    # host="0.0.0.0" supaya bisa dibuka dari HP/komputer lain di jaringan yang sama.
    app.run(host="127.0.0.1", port=5000, debug=True)
