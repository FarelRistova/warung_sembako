# Kasir Warung Sembako

Aplikasi kasir sederhana berbasis web. Logika ditulis dengan Python (Flask + SQLite),
tampilan memakai HTML, CSS, dan sedikit JavaScript.

## Cara menjalankan

1. Pasang Python 3.9 atau lebih baru.
2. Buka terminal di folder ini, lalu jalankan:

       pip install -r requirements.txt
       python app.py

3. Buka http://127.0.0.1:5000 di browser.

Saat pertama dijalankan, file database `warung.db` dibuat otomatis
dan diisi 20 contoh barang sembako. Hapus atau ubah lewat menu **Barang**.

## Fitur

- **Kasir**: cari barang atau scan kode lalu Enter, klik barang untuk masuk keranjang,
  jumlah boleh desimal (misalnya 0,5 kg), hitung kembalian otomatis, cetak struk.
- **Barang**: tambah, ubah, hapus barang, atur harga dan stok.
- **Laporan**: omzet per hari, barang paling laku, stok yang menipis, riwayat nota.

## Pengaturan

Nama dan alamat warung di struk bisa diganti lewat variabel lingkungan:

    NAMA_WARUNG="Warung Bu Siti" ALAMAT_WARUNG="Jl. Melati 5" python app.py

Untuk membuka dari HP di jaringan Wi-Fi yang sama, ubah `host="127.0.0.1"`
di baris terakhir `app.py` menjadi `host="0.0.0.0"`, lalu buka `http://IP-KOMPUTER:5000`.

## Struktur folder

    app.py              logika, database, dan API
    templates/          halaman HTML (kasir, barang, laporan, struk)
    static/style.css    tampilan
    static/kasir.js     interaksi halaman kasir
    static/produk.js    interaksi halaman barang
