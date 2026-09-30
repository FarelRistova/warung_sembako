(() => {
  const $ = s => document.querySelector(s);

  let produk = [];
  let kategoriAktif = 'Semua';
  let bayar = 0;
  let sedangProses = false;
  const cart = new Map(); // id -> { ...produk, qty }

  // ---------- Data ----------
  async function muatProduk() {
    const res = await fetch('/api/produk');
    produk = await res.json();
    renderChips();
    renderGrid();
    // Sinkronkan keranjang dengan data terbaru (harga/stok bisa berubah)
    for (const [id, item] of cart) {
      const baru = produk.find(p => p.id === id);
      if (!baru) cart.delete(id);
      else cart.set(id, { ...baru, qty: Math.min(item.qty, baru.stok) });
    }
    renderCart();
  }

  // ---------- Katalog ----------
  function renderChips() {
    const daftar = ['Semua', ...new Set(produk.map(p => p.kategori))].sort((a, b) =>
      a === 'Semua' ? -1 : b === 'Semua' ? 1 : a.localeCompare(b, 'id'));
    if (!daftar.includes(kategoriAktif)) kategoriAktif = 'Semua';
    $('#chips').innerHTML = daftar.map(k =>
      `<button type="button" role="tab" class="chip ${k === kategoriAktif ? 'aktif' : ''}" data-k="${esc(k)}"
               aria-selected="${k === kategoriAktif}">${esc(k)}</button>`).join('');
  }

  function renderGrid() {
    const q = $('#cari').value.trim().toLowerCase();
    const hasil = produk.filter(p =>
      (kategoriAktif === 'Semua' || p.kategori === kategoriAktif) &&
      (!q || p.nama.toLowerCase().includes(q) || (p.kode || '').toLowerCase().includes(q)));

    if (!hasil.length) {
      $('#grid').innerHTML = `<p class="kosong">Tidak ada barang yang cocok. Coba kata kunci lain, atau tambah barang di menu Barang.</p>`;
      return;
    }

    $('#grid').innerHTML = hasil.map(p => {
      const habis = p.stok <= 0;
      const menipis = !habis && p.stok <= p.stok_min;
      const di = cart.get(p.id);
      return `
      <button type="button" class="kartu ${habis ? 'habis' : ''}" data-id="${p.id}" ${habis ? 'disabled' : ''}>
        ${di ? `<span class="lencana">${angka(di.qty)}</span>` : ''}
        <span class="kartu-nama">${esc(p.nama)}</span>
        <span class="kartu-stok ${habis || menipis ? 'rendah' : ''}">
          ${habis ? 'Stok habis' : `Sisa ${angka(p.stok)} ${esc(p.satuan)}`}
        </span>
        <span class="label-harga"><b>${rp(p.harga)}</b><small>/ ${esc(p.satuan)}</small></span>
      </button>`;
    }).join('');
  }

  // ---------- Keranjang ----------
  function tambah(id, jumlah = 1) {
    const p = produk.find(x => x.id === id);
    if (!p) return;
    const sekarang = cart.get(id)?.qty || 0;
    const baru = sekarang + jumlah;
    if (baru > p.stok + 1e-9) {
      toast(`Stok ${p.nama} hanya ${angka(p.stok)} ${p.satuan}.`, 'galat');
      return;
    }
    cart.set(id, { ...p, qty: baru });
    renderCart();
    renderGrid();
  }

  function ubahQty(id, qty) {
    const item = cart.get(id);
    if (!item) return;
    if (!(qty > 0)) { cart.delete(id); }
    else if (qty > item.stok + 1e-9) {
      toast(`Stok ${item.nama} hanya ${angka(item.stok)} ${item.satuan}.`, 'galat');
      item.qty = item.stok;
    } else { item.qty = qty; }
    renderCart();
    renderGrid();
  }

  const totalBelanja = () =>
    [...cart.values()].reduce((s, i) => s + Math.round(i.harga * i.qty), 0);

  function renderCart() {
    const ul = $('#cart');
    if (!cart.size) {
      ul.innerHTML = `<li class="cart-kosong">Belum ada barang.<br>Klik barang di sebelah kiri untuk menambahkan.</li>`;
    } else {
      ul.innerHTML = [...cart.values()].map(i => `
        <li class="item" data-id="${i.id}">
          <div class="item-info">
            <strong>${esc(i.nama)}</strong>
            <span>${rp(i.harga)} / ${esc(i.satuan)}</span>
          </div>
          <div class="qty">
            <button type="button" data-aksi="kurang" aria-label="Kurangi">−</button>
            <input type="number" min="0" step="any" value="${i.qty}" aria-label="Jumlah ${esc(i.nama)}">
            <button type="button" data-aksi="tambah" aria-label="Tambah">+</button>
          </div>
          <div class="item-sub">${rp(Math.round(i.harga * i.qty))}</div>
          <button type="button" class="hapus" data-aksi="hapus" aria-label="Hapus ${esc(i.nama)}">×</button>
        </li>`).join('');
    }
    hitung();
  }

  function hitung() {
    const total = totalBelanja();
    const selisih = bayar - total;
    $('#total').textContent = rp(total);

    const baris = $('#baris-kembali');
    if (total === 0) {
      $('#label-kembali').textContent = 'Kembalian';
      $('#kembali').textContent = rp(0);
      baris.className = 'baris-kembali';
    } else if (selisih >= 0) {
      $('#label-kembali').textContent = 'Kembalian';
      $('#kembali').textContent = rp(selisih);
      baris.className = 'baris-kembali cukup';
    } else {
      $('#label-kembali').textContent = 'Kurang';
      $('#kembali').textContent = rp(-selisih);
      baris.className = 'baris-kembali kurang';
    }
    $('#proses').disabled = sedangProses || total === 0 || bayar < total;
  }

  function setBayar(n) {
    bayar = Math.max(0, Math.floor(n) || 0);
    $('#bayar').value = bayar ? bayar.toLocaleString('id-ID') : '';
    hitung();
  }

  // ---------- Bayar ----------
  async function prosesBayar() {
    if ($('#proses').disabled) return;
    sedangProses = true; hitung();
    try {
      const res = await fetch('/api/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [...cart.values()].map(i => ({ id: i.id, qty: i.qty })),
          bayar
        })
      });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Transaksi gagal.', 'galat'); return; }

      $('#sukses-nota').textContent = `Nota ${data.no_nota} · Total ${rp(data.total)}`;
      $('#sukses-kembali').textContent = rp(data.kembali);
      $('#sukses-cetak').href = `/struk/${data.id}?print=1`;
      $('#sukses').showModal();

      cart.clear();
      setBayar(0);
      await muatProduk();
    } catch (e) {
      toast('Tidak bisa terhubung ke server. Pastikan aplikasi masih berjalan.', 'galat');
    } finally {
      sedangProses = false; hitung();
    }
  }

  // ---------- Event ----------
  $('#cari').addEventListener('input', renderGrid);
  $('#cari').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const q = e.target.value.trim().toLowerCase();
    if (!q) return;
    // Enter: kalau kode cocok persis (scanner barcode), langsung masukkan
    const cocok = produk.find(p => (p.kode || '').toLowerCase() === q) ||
      (produk.filter(p => p.nama.toLowerCase().includes(q)).length === 1 &&
        produk.find(p => p.nama.toLowerCase().includes(q)));
    if (cocok && cocok.stok > 0) { tambah(cocok.id); e.target.value = ''; renderGrid(); }
    else if (!cocok) toast('Barang tidak ditemukan.', 'galat');
  });

  $('#chips').addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b) return;
    kategoriAktif = b.dataset.k; renderChips(); renderGrid();
  });

  $('#grid').addEventListener('click', e => {
    const k = e.target.closest('.kartu'); if (k) tambah(Number(k.dataset.id));
  });

  $('#cart').addEventListener('click', e => {
    const tombol = e.target.closest('[data-aksi]'); if (!tombol) return;
    const id = Number(tombol.closest('.item').dataset.id);
    const item = cart.get(id);
    if (tombol.dataset.aksi === 'tambah') tambah(id, 1);
    if (tombol.dataset.aksi === 'kurang') ubahQty(id, item.qty - 1);
    if (tombol.dataset.aksi === 'hapus') ubahQty(id, 0);
  });
  $('#cart').addEventListener('change', e => {
    if (e.target.matches('input')) ubahQty(Number(e.target.closest('.item').dataset.id), parseFloat(e.target.value));
  });

  $('#kosongkan').addEventListener('click', () => { cart.clear(); setBayar(0); renderCart(); renderGrid(); });

  $('#bayar').addEventListener('input', e => setBayar(Number(e.target.value.replace(/\D/g, ''))));
  $('#bayar').addEventListener('keydown', e => { if (e.key === 'Enter') prosesBayar(); });
  $('#cepat').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    setBayar(b.dataset.nominal === 'pas' ? totalBelanja() : Number(b.dataset.nominal));
  });
  $('#proses').addEventListener('click', prosesBayar);

  $('#sukses-tutup').addEventListener('click', () => { $('#sukses').close(); $('#cari').focus(); });
  $('#sukses').addEventListener('close', () => $('#cari').focus());

  // Pintasan keyboard: "/" untuk mencari
  document.addEventListener('keydown', e => {
    if (e.key === '/' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      e.preventDefault(); $('#cari').focus();
    }
  });

  muatProduk();
})();
