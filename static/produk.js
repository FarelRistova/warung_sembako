(() => {
  const $ = s => document.querySelector(s);
  let produk = [];
  let editId = null;

  async function muat() {
    const res = await fetch('/api/produk');
    produk = await res.json();
    render();
    $('#daftar-kategori').innerHTML =
      [...new Set(produk.map(p => p.kategori))].map(k => `<option value="${esc(k)}">`).join('');
  }

  function render() {
    const q = $('#cari-barang').value.trim().toLowerCase();
    const hasil = produk.filter(p =>
      !q || [p.nama, p.kode || '', p.kategori].some(t => t.toLowerCase().includes(q)));

    const menipis = produk.filter(p => p.stok <= p.stok_min).length;
    $('#ringkas-barang').textContent =
      `${produk.length} barang` + (menipis ? ` · ${menipis} perlu dibeli lagi` : '');

    if (!hasil.length) {
      $('#isi-tabel').innerHTML =
        `<tr><td colspan="5" class="kosong">${q ? 'Tidak ada barang yang cocok.' : 'Belum ada barang. Klik “Tambah barang” untuk mulai.'}</td></tr>`;
      return;
    }

    $('#isi-tabel').innerHTML = hasil.map(p => {
      const habis = p.stok <= 0;
      const rendah = !habis && p.stok <= p.stok_min;
      return `
      <tr data-id="${p.id}">
        <td>
          <strong>${esc(p.nama)}</strong>
          ${p.kode ? `<span class="kode">${esc(p.kode)}</span>` : ''}
        </td>
        <td>${esc(p.kategori)}</td>
        <td class="kanan">${rp(p.harga)}<small> / ${esc(p.satuan)}</small></td>
        <td class="kanan">
          <span class="stok ${habis ? 'habis' : rendah ? 'rendah' : ''}">${angka(p.stok)} ${esc(p.satuan)}</span>
        </td>
        <td class="aksi">
          <button type="button" class="tombol-kecil" data-aksi="ubah">Ubah</button>
          <button type="button" class="tombol-kecil bahaya" data-aksi="hapus">Hapus</button>
        </td>
      </tr>`;
    }).join('');
  }

  // ---------- Form ----------
  function bukaForm(p) {
    editId = p ? p.id : null;
    const f = $('#form');
    f.reset();
    $('#galat-form').textContent = '';
    $('#form-judul').textContent = p ? 'Ubah barang' : 'Tambah barang';
    if (p) {
      for (const k of ['nama', 'kategori', 'kode', 'harga', 'satuan', 'stok', 'stok_min']) f.elements[k].value = p[k] ?? '';
    }
    $('#form-dialog').showModal();
    f.elements.nama.focus();
  }

  $('#tambah').addEventListener('click', () => bukaForm(null));
  $('#batal').addEventListener('click', () => $('#form-dialog').close());

  $('#form').addEventListener('submit', async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    $('#simpan').disabled = true;
    try {
      const res = await fetch(editId ? `/api/produk/${editId}` : '/api/produk', {
        method: editId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const hasil = await res.json();
      if (!res.ok) { $('#galat-form').textContent = hasil.error || 'Gagal menyimpan.'; return; }
      $('#form-dialog').close();
      toast(editId ? 'Perubahan disimpan.' : 'Barang ditambahkan.');
      await muat();
    } catch (err) {
      $('#galat-form').textContent = 'Tidak bisa terhubung ke server.';
    } finally {
      $('#simpan').disabled = false;
    }
  });

  // ---------- Tabel ----------
  $('#isi-tabel').addEventListener('click', async e => {
    const b = e.target.closest('[data-aksi]'); if (!b) return;
    const id = Number(b.closest('tr').dataset.id);
    const p = produk.find(x => x.id === id);
    if (b.dataset.aksi === 'ubah') bukaForm(p);
    if (b.dataset.aksi === 'hapus') {
      if (!confirm(`Hapus “${p.nama}” dari daftar barang?\nRiwayat transaksi lama tidak ikut terhapus.`)) return;
      const res = await fetch(`/api/produk/${id}`, { method: 'DELETE' });
      if (res.ok) { toast('Barang dihapus.'); muat(); }
      else toast('Gagal menghapus barang.', 'galat');
    }
  });

  $('#cari-barang').addEventListener('input', render);
  muat();
})();
