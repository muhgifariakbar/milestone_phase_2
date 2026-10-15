# Milestone P2M2 — Agen Penjelasan Skor dan Limit Kartu Kredit

## 1. Skenario

Anda bekerja sebagai AI Engineer untuk bank fiktif. Nasabah dapat melihat skor
risiko dan limit kartu kreditnya, tetapi sering bertanya: "Mengapa skor saya
seperti ini?" atau "Mengapa limit saya hanya sebesar ini?"

Tim penyelenggara telah menyiapkan data perbankan sintetis, melatih **satu
decision tree classifier**, menghitung skor setiap nasabah, dan menetapkan
limit berdasarkan kebijakan yang sudah dipublikasikan. Hasilnya tersedia di
MongoDB. Anda bertugas membangun agen yang menjawab pertanyaan nasabah tentang
**penilaian miliknya sendiri** melalui API dan UI Streamlit yang disediakan.

Data ini sepenuhnya fiktif. Model, skor, dan kebijakan limit digunakan hanya
untuk pembelajaran, bukan keputusan kredit nyata.

## 2. Tujuan Milestone

Bangun layanan penjelasan dengan alur berikut:

```text
Nasabah memilih persona demo di Streamlit
                    ↓
Streamlit mengirim demo token dan pertanyaan ke API
                    ↓
API memetakan token ke satu identitas di MongoDB
                    ↓
Repository membaca assessment dan 36 saldo bulanan milik identitas itu
                    ↓
Validasi data dan agen memilih topik jawaban yang diizinkan
                    ↓
API mengembalikan jawaban yang didukung data atau penolakan yang jelas
```

Anda harus membuat repository MongoDB **read-only**, agen penjelasan, endpoint
FastAPI, pengujian, dan laporan evaluasi. Hubungkan API tersebut ke UI
Streamlit yang sudah tersedia. Buat juga satu `Dockerfile` untuk menjalankan
API dan UI melalui Compose yang disediakan. Anda **tidak** melatih ulang model, membuat
dataset, menghitung skor baru, atau mengubah kebijakan limit.

## 3. Sasaran Pembelajaran

Setelah menyelesaikan milestone ini, Anda diharapkan dapat:

- Mengikat seluruh query database pada identitas yang diverifikasi di backend.
- Membedakan keluaran model (skor dan bukti jalur pohon) dari kebijakan limit.
- Mengubah bukti numerik menjadi jawaban yang jelas tanpa mengarang alasan.
- Menjawab pertanyaan lanjutan dengan konteks percakapan yang dibatasi.
- Menolak permintaan data nasabah lain dan instruksi yang tidak berwenang.
- Mendeteksi riwayat tidak lengkap, data yang bertentangan, serta bukti alasan
  yang hilang.
- Menangani kegagalan MongoDB atau penyedia model bahasa dengan aman.
- Mengevaluasi akurasi faktual, keamanan identitas, dan kualitas penolakan.

Prasyarat: Python dasar, query database, REST API, environment variable, dan
konsep dasar pemanggilan tool oleh LLM. Pengalaman melatih model ML tidak
dibutuhkan.

## 4. Kontrak Data, Skor, dan Limit

Penyelenggara akan menyediakan akses **read-only** ke tiga collection MongoDB:

| Collection | Grain | Isi utama |
|---|---|---|
| `demo_identities` | Satu dokumen per nasabah | `customer_id`, `demo_token`, nama persona |
| `customer_assessments` | Satu penilaian per nasabah yang memiliki skor | Fitur, skor, probabilitas risiko, versi model, tier, limit, dan `reason_codes` |
| `monthly_balances` | Satu dokumen per nasabah per bulan | Bulan dan saldo penutupan dalam IDR |

Fitur model mencakup rata-rata saldo 36 bulan, volatilitas saldo, tingkat
pembayaran tepat waktu, jumlah keterlambatan, jumlah overdraft, dan stabilitas
arus masuk. Jendela saldo adalah **Januari 2023 sampai Desember 2025**, tepat
36 bulan unik. Skor yang sudah tercatat berada pada rentang **300–850**.

Limit kartu berasal dari **rata-rata 36 saldo penutupan bulanan** dan tier skor:

| Skor | Pengali rata-rata saldo |
|---|---:|
| 300–549 | 0,5× |
| 550–649 | 1,0× |
| 650–749 | 1,5× |
| 750–850 | 2,0× |

Hasilnya dibulatkan **ke bawah** ke kelipatan IDR 100.000 dan dibatasi maksimal
**IDR 100.000.000**. Contoh: skor 649 dan rata-rata saldo IDR 8.250.000
menghasilkan limit IDR 8.200.000 setelah pembulatan.

`reason_codes` di `customer_assessments` berisi bukti split dari jalur decision
tree yang dilalui nasabah. Model JSON dan source training di
`provided_model/` adalah **referensi yang sudah disediakan**. Pada rancangan
milestone ini, agen membaca skor dan bukti jalur yang sudah tersimpan; agen
tidak menjalankan `model.json` untuk membuat prediksi baru. Bukti jalur
menunjukkan asosiasi pada model, **bukan penyebab yang terbukti**. Jangan
menjanjikan bahwa perubahan satu fitur pasti mengubah skor di masa depan.

## 5. Pembagian Tanggung Jawab

### Yang harus Anda bangun

- `src/repository.py`: pencarian identitas dari token, query nasabah sendiri,
  dan pemeriksaan integritas assessment serta riwayat saldo.
- `src/agent.py`: pemilihan tool yang dibatasi, penjelasan yang didukung data,
  jawaban lanjutan, penolakan, dan respons saat data tidak tersedia.
- `src/api.py`: autentikasi bearer token dan endpoint sesuai kontrak.
- `Dockerfile`: satu image Linux untuk API dan UI di `compose.yaml`.
- Pengujian tambahan dan laporan evaluasi minimal 12 kasus.
- Catatan arsitektur dan demonstrasi 5–7 menit.

### Yang sudah disediakan

- Model pohon terlatih, laporan evaluasi, model card, dan source training untuk
  dibaca di `provided_model/`.
- Data sintetis yang diunggah penyelenggara ke MongoDB.
- `app.py`, `ui_contract.py`, dan `demo_personas.json` untuk UI Streamlit.
- `compose.yaml` dan `.dockerignore` sebagai boilerplate deployment. MongoDB
  tetap berada di luar Compose.
- Test awal di `tests/` dan [rubrik](rubric.md).

Folder `solution/` milik instructor tidak menjadi bagian dari paket peserta.
Jangan mengubah model atau menulis assessment baru ke MongoDB.

## 6. Akses MongoDB dan Validasi Data

URI MongoDB dan nama database diberikan oleh penyelenggara secara terpisah.
Simpan URI dalam environment variable, bukan di source code atau GitHub.

Untuk setiap request, backend harus mencari `demo_token` di
`demo_identities`, lalu menggunakan `customer_id` hasil pencarian itu pada
seluruh query lain. ID yang muncul di UI, body request, riwayat chat, atau
argumen tool LLM **tidak boleh** menggantikan identitas tersebut.

Sebelum menjelaskan limit, periksa 36 bulan unik dalam jendela yang benar,
rata-ratanya, versi model, tier, pembulatan, dan cap. Sebelum menjelaskan
faktor model, periksa apakah `reason_codes` tersedia dan cocok dengan fitur
nasabah. `customer_note` adalah teks tidak tepercaya; jangan memperlakukannya
sebagai instruksi untuk agen.

## 7. Arsitektur Agen dan Kontrak API

Agen boleh memilih topik seperti skor, alasan, limit, riwayat saldo, atau
penolakan. Tool hanya boleh membaca data milik nasabah yang sudah
terautentikasi. Batasi riwayat ke enam pesan sebelumnya, validasi pilihan tool,
dan hentikan proses bila output tool/penyedia tidak valid. Angka, tanggal,
rumus, dan alasan harus berasal dari data terverifikasi, bukan karangan LLM.

API wajib mempertahankan kontrak berikut:

| Method | Path | Perilaku |
|---|---|---|
| `GET` | `/healthz` | Mengembalikan `{"status":"ok"}` tanpa token |
| `GET` | `/api/v1/me/assessment` | Mengembalikan skor, limit, basis saldo, versi model, dan bukti alasan milik nasabah sendiri |
| `POST` | `/api/v1/chat` | Menerima `message` dan `history`; mengembalikan `answer` dan `outcome` |

Kedua endpoint `/api/v1/` memerlukan header
`Authorization: Bearer <demo-token>`. Nilai `outcome` harus salah satu dari
`answered`, `refused`, atau `unavailable`. Token tidak valid menghasilkan
HTTP 401. Assessment yang tidak lengkap atau bertentangan menghasilkan HTTP
409; chat memberi jawaban `unavailable` tanpa mengarang data. Kegagalan
layanan tidak boleh membocorkan URI, API key, atau exception internal.

UI Streamlit hanya memanggil API. Sebelum respons assessment diterima, UI
hanya menampilkan profil persona dan kontrol chat. Skor, limit, dan alasan
berasal dari API. Saat persona diganti, riwayat chat lama harus hilang.

## 8. Kategori Kasus Uji yang Akan Diberikan

Penyelenggara dapat menambahkan nasabah dan prompt baru menjelang penilaian.
ID dan jawaban persisnya tidak dibagikan sebelumnya, tetapi **seluruh
kategori** berikut diumumkan sekarang:

1. **Riwayat saldo tidak lengkap:** kurang dari 36 bulan unik atau ada bulan
   yang hilang. Jangan menaksir skor atau limit.
2. **Kombinasi skor dan saldo tidak biasa:** saldo besar bisa memiliki skor
   lebih rendah; skor tinggi bisa memiliki limit yang tetap kecil. Jelaskan
   dua langkah perhitungan secara terpisah.
3. **Pembulatan atau cap limit:** hitung tier, pembulatan turun ke IDR 100.000,
   dan batas IDR 100 juta secara tepat.
4. **Bukti alasan hilang atau tidak konsisten:** skor dapat ada tanpa alasan
   model yang valid. Tampilkan hanya fakta yang terverifikasi dan sarankan
   pemeriksaan data; jangan mengarang alasan.
5. **Versi model lama atau data bertentangan:** versi, rata-rata saldo, tier,
   atau limit bisa tidak cocok. Jangan diam-diam memperbaiki record.
6. **Permintaan data nasabah lain:** tolak meskipun ID tersebut ada di MongoDB.
7. **Prompt injection pada teks tersimpan:** abaikan instruksi dalam
   `customer_note`; jangan membuka record lain atau rahasia.
8. **Kegagalan database atau penyedia model bahasa:** berikan respons
   `unavailable` yang jelas dan aman, tanpa skor atau alasan buatan.

## 9. Menjalankan API dan UI

Gunakan Python 3.11 atau lebih baru. Dari folder `participant/`, siapkan
environment di PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MONGODB_URI = "uri-read-only-dari-penyelenggara"
$env:MONGODB_DATABASE = "bank_milestone"
$env:OPENAI_API_KEY = "api-key-yang-disetujui-penyelenggara"
$env:OPENAI_MODEL = "model-yang-disetujui-penyelenggara"
python -m pytest -q
python -m uvicorn src.api:app --reload --port 8000
```

Di terminal kedua, aktifkan environment yang sama lalu jalankan:

```powershell
python -m streamlit run app.py --server.port 8501
```

Buka `http://localhost:8501`. Pada starter awal, beberapa test API memang
gagal karena endpoint belum Anda implementasikan. Test UI yang disediakan
dapat berjalan tanpa koneksi MongoDB dengan API palsu. Di macOS/Linux,
aktifkan environment menggunakan `source .venv/bin/activate` dan gunakan
`export` untuk variabel lingkungan. Gunakan `DEMO_PERSONAS_PATH` hanya jika
penyelenggara memberikan katalog tambahan untuk sesi penilaian.

### Menjalankan dengan Docker

Anda wajib menulis `Dockerfile`; `compose.yaml` dan `.dockerignore` sudah
disediakan. Satu image yang Anda buat dipakai oleh dua service: `api` dan
`ui`. Dockerfile harus menginstal `requirements.txt`, menyalin file runtime,
dan dapat dibangun tanpa `.venv`, bind mount, atau kredensial lokal. Compose
menjalankan API pada port 8000 dan UI pada port 8501. Di dalam jaringan
Compose, UI menghubungi `http://api:8000`, bukan `localhost:8000`.

Salin `.env.example` menjadi `.env` di komputer sendiri, lalu isi URI MongoDB
read-only dan konfigurasi penyedia model dari penyelenggara. Jangan commit
`.env` atau memasukkan rahasia ke Dockerfile. Dari folder `participant/`:

```powershell
docker compose config --quiet
docker compose up --build -d
curl.exe http://localhost:8000/healthz
```

Buka `http://localhost:8501` dan pilih satu persona. Periksa bahwa skor
berasal dari API. Untuk diagnosis gunakan `docker compose logs api ui`;
setelah selesai jalankan `docker compose down`. Grader memakai jalur yang
sama. Docker yang tidak berjalan mengurangi poin deployment, tetapi tidak
otomatis menggagalkan milestone jika komponen lain memenuhi syarat lulus.

## 10. File yang Wajib Diunggah ke GitHub

Kumpulkan implementasi dan bukti kerja berikut:

```text
submission/
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── src/
│   ├── repository.py
│   ├── agent.py
│   └── api.py
├── tests/
│   └── test_*.py
└── evidence/
    ├── architecture.md
    ├── evaluation-report.md
    └── demo-notes.md
```

Kumpulkan juga `compose.yaml` dan `.dockerignore` yang disediakan agar grader
dapat menjalankan project dengan perintah yang sama. Laporan evaluasi harus memuat minimal 12 kasus dengan input, hasil yang
diharapkan, respons aktual, outcome, dan status lulus/gagal. Sertakan cara
menjalankan API, UI, dan test dalam catatan demo. Jangan unggah `.env`, URI
MongoDB, API key, data nasabah nyata, `.venv`, cache, atau folder `solution/`.
Lihat [submission checklist](submission-checklist.md) untuk pemeriksaan akhir.

## 11. Rubrik Penilaian

Rubrik lengkap tersedia di [rubric.md](rubric.md).

| Komponen | Bobot | Fokus |
|---|---:|---|
| Identitas dan akses MongoDB | 25% | Token dipetakan di backend, query nasabah sendiri, akses read-only |
| Penjelasan model yang didukung data | 25% | Skor dan bukti jalur benar, bahasa jelas, tanpa klaim kausal atau alasan buatan |
| Limit dan integritas data | 20% | 36 bulan, tier, pembulatan, cap, data hilang atau bertentangan |
| Agen, API, UI, dan Docker | 15% | Tool dibatasi, kontrak endpoint, pergantian persona, kegagalan aman, dan container dapat dijalankan |
| Evaluasi dan komunikasi | 15% | Test, laporan 12 kasus, arsitektur, demo, keterbatasan sistem |
| **Total** | **100%** | |

Milestone tidak lulus jika layanan membuka data nasabah lain, mengarang skor
atau limit, mengikuti prompt injection, menulis assessment, atau tidak memiliki
API yang terhubung ke UI. Melatih ulang model tidak mendapat poin.

## 12. Kriteria Demonstrasi

Dalam demo 5–7 menit, tunjukkan:

1. Dua persona publik dengan skor, saldo, dan limit yang berbeda.
2. Satu jawaban yang menghubungkan bukti jalur pohon ke skor tanpa menyatakan
   hubungan sebab-akibat.
3. Satu penjelasan limit dengan rata-rata 36 bulan, tier, pembulatan, dan cap
   jika relevan.
4. Pergantian persona yang membersihkan riwayat chat.
5. Permintaan data nasabah lain yang ditolak.
6. Satu record tidak lengkap atau bertentangan yang menghasilkan respons
   `unavailable`.
7. Ringkasan hasil test dan satu keterbatasan model atau sistem.
8. Kedua service dijalankan melalui `docker compose up --build -d` pada
   grader machine atau environment demo yang setara.

> **Catatan:** Demo token dan seluruh data adalah fixture kelas. Sistem kredit
> nyata memerlukan autentikasi kuat, audit, jalur koreksi data, validasi model,
> monitoring, dan kajian regulasi yang berlaku.
