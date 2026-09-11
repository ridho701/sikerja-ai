import os, json, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

BASE=Path(__file__).resolve().parent.parent
app=FastAPI(title="SIKERJA AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def client():
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise HTTPException(500,"OPENAI_API_KEY belum diatur di server.")
    return OpenAI(api_key=key)

class GenRequest(BaseModel):
    identity: dict
    date: str
    spoken_text: str

from fastapi.responses import HTMLResponse

INDEX_HTML = r"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f766e">
<link rel="manifest" href="/manifest.webmanifest">
<title>SIKERJA AI</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f1f5f9;color:#0f172a}
.app{max-width:720px;margin:auto;min-height:100vh;background:white}.top{background:#0f766e;color:white;padding:22px 18px 18px;position:sticky;top:0;z-index:3}
.top h1{margin:0;font-size:25px}.top p{margin:5px 0 0;opacity:.9;font-size:14px}
main{padding:16px}.card{border:1px solid #e2e8f0;border-radius:18px;padding:16px;margin-bottom:14px;box-shadow:0 3px 14px #00000008}
label{display:block;font-weight:700;font-size:13px;margin:10px 0 6px}input,textarea,select{width:100%;border:1px solid #cbd5e1;border-radius:12px;padding:12px;font:inherit;background:#fff}
textarea{min-height:130px;resize:vertical}.row{display:flex;gap:10px}.row>*{flex:1}
button{border:0;border-radius:13px;padding:13px 15px;font-weight:800;font-size:15px;cursor:pointer}
.primary{background:#0f766e;color:#fff}.secondary{background:#e2e8f0;color:#0f172a}.danger{background:#fee2e2;color:#991b1b}
.micwrap{text-align:center;padding:10px 0 4px}.mic{width:118px;height:118px;border-radius:60px;background:#0f766e;color:white;font-size:48px;box-shadow:0 10px 25px #0f766e33}.mic.recording{background:#dc2626;animation:pulse 1.1s infinite}
@keyframes pulse{50%{transform:scale(1.05)}}.hint{text-align:center;color:#64748b;font-size:13px;margin:10px 0}
.status{padding:10px;border-radius:10px;background:#f8fafc;color:#475569;font-size:13px;display:none}.status.show{display:block}
.small{font-size:12px;color:#64748b}.hidden{display:none!important}.history-item{padding:12px;border-top:1px solid #e2e8f0}.history-item:first-child{border-top:0}
.badge{display:inline-block;background:#ccfbf1;color:#115e59;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:700}
</style>
</head>
<body>
<div class="app">
<header class="top"><h1>SIKERJA AI</h1><p>Laporan Kinerja Harian ASN</p></header>
<main>
<section id="identity" class="card">
<h2 style="margin:0 0 4px">Identitas ASN</h2>
<p class="small">Diisi sekali. Data tersimpan di HP/browser ini.</p>
<label>Nama ASN</label><input id="nama" placeholder="Nama lengkap">
<label>Jabatan</label><input id="jabatan" placeholder="Jabatan">
<label>Unit Kerja</label><input id="unit" placeholder="Unit kerja">
<button class="primary" style="width:100%;margin-top:14px" onclick="saveIdentity()">Simpan Identitas</button>
</section>

<section id="work" class="card hidden">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><b id="who"></b><div class="small" id="where"></div></div>
<button class="secondary" onclick="editIdentity()">Edit</button>
</div>
<hr style="border:0;border-top:1px solid #e2e8f0;margin:14px 0">
<label>Tanggal</label><input type="date" id="tanggal">
<div class="micwrap">
<button id="mic" class="mic" onclick="toggleRecord()">🎙️</button>
<div class="hint">Tekan mikrofon, bicara tentang pekerjaan hari ini, lalu tekan lagi untuk berhenti.</div>
</div>
<div id="status" class="status"></div>
<label>Hasil AI / Uraian Kinerja</label>
<textarea id="uraian" placeholder="Hasil transkripsi dan uraian formal akan muncul di sini. Bapak/Ibu tetap dapat mengeditnya."></textarea>
<div class="row" style="margin-top:10px">
<button class="primary" onclick="generateAI()">✨ Susun dengan AI</button>
<button class="secondary" onclick="saveReport()">💾 Simpan</button>
</div>
</section>

<section class="card hidden" id="result">
<h3 style="margin-top:0">Hasil Laporan</h3>
<label>Target Kinerja</label><input id="target">
<label>Uraian Kegiatan/Kinerja Harian</label><textarea id="hasil"></textarea>
<label>Output</label><input id="output" value="Dokumen/Laporan/Notulen/Rekomendasi">
<div class="row"><div><label>Kuantitas</label><input id="kuantitas" value="1"></div><div><label>Realisasi</label><input id="realisasi" value="1"></div><div><label>Persentase</label><input id="persen" value="100%"></div></div>
<button class="primary" style="width:100%;margin-top:14px" onclick="saveReport()">💾 Simpan Laporan</button>
</section>

<section class="card">
<div style="display:flex;justify-content:space-between;align-items:center"><h3 style="margin:0">Riwayat</h3><button class="danger" onclick="clearHistory()">Hapus Riwayat</button></div>
<div id="history" class="small" style="margin-top:10px">Belum ada laporan.</div>
</section>
</main>
</div>
<script>
const $=id=>document.getElementById(id);
let mediaRecorder=null, chunks=[], audioBlob=null, stream=null;
function today(){return new Date().toISOString().slice(0,10)}
function init(){
 $("tanggal").value=today();
 const x=JSON.parse(localStorage.getItem("sikerja_identity")||"null");
 if(x){showWork(x)} else {$("identity").classList.remove("hidden")}
 renderHistory();
}
function saveIdentity(){
 const x={nama:$("nama").value.trim(),jabatan:$("jabatan").value.trim(),unit:$("unit").value.trim()};
 if(!x.nama||!x.jabatan||!x.unit){alert("Lengkapi Nama ASN, Jabatan, dan Unit Kerja.");return}
 localStorage.setItem("sikerja_identity",JSON.stringify(x)); showWork(x);
}
function showWork(x){$("identity").classList.add("hidden");$("work").classList.remove("hidden");$("who").textContent=x.nama+" — "+x.jabatan;$("where").textContent=x.unit}
function editIdentity(){const x=JSON.parse(localStorage.getItem("sikerja_identity"));$("nama").value=x.nama;$("jabatan").value=x.jabatan;$("unit").value=x.unit;$("identity").classList.remove("hidden");$("work").classList.add("hidden")}
function setStatus(t){$("status").textContent=t;$("status").classList.add("show")}
async function toggleRecord(){
 if(mediaRecorder && mediaRecorder.state==="recording"){mediaRecorder.stop(); if(stream)stream.getTracks().forEach(t=>t.stop()); $("mic").classList.remove("recording"); setStatus("Memproses rekaman…"); return}
 try{
  stream=await navigator.mediaDevices.getUserMedia({audio:true});
  chunks=[]; mediaRecorder=new MediaRecorder(stream);
  mediaRecorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
  mediaRecorder.onstop=async()=>{audioBlob=new Blob(chunks,{type:mediaRecorder.mimeType||"audio/webm"});await transcribe()};
  mediaRecorder.start();$("mic").classList.add("recording");setStatus("Sedang merekam… Tekan lagi untuk berhenti.");
 }catch(e){setStatus("Mikrofon tidak dapat digunakan. Pastikan situs dibuka melalui HTTPS dan izin mikrofon diberikan.");}
}
async function transcribe(){
 const fd=new FormData();fd.append("audio",audioBlob,"laporan.webm");
 try{const r=await fetch("/api/ai/transcribe",{method:"POST",body:fd});const d=await r.json();if(!r.ok)throw Error(d.detail||"Gagal transkripsi");$("uraian").value=d.text||"";setStatus("Suara berhasil diubah menjadi teks. Silakan susun dengan AI.");}
 catch(e){setStatus("Gagal transkripsi: "+e.message)}
}
async function generateAI(){
 const x=JSON.parse(localStorage.getItem("sikerja_identity")||"null");const spoken=$("uraian").value.trim();
 if(!spoken){alert("Bicara melalui mikrofon atau isi uraian terlebih dahulu.");return}
 setStatus("AI sedang menyusun uraian kinerja…");
 try{
  const r=await fetch("/api/ai/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({identity:x,date:$("tanggal").value,spoken_text:spoken})});
  const d=await r.json();if(!r.ok)throw Error(d.detail||"Gagal AI");
  $("result").classList.remove("hidden");$("target").value=d.target||"";$("hasil").value=d.uraian||spoken;$("output").value=d.output||"Dokumen/Laporan/Notulen/Rekomendasi";
  $("kuantitas").value=d.kuantitas||1;$("realisasi").value=d.realisasi||1;$("persen").value=d.persentase||"100%";setStatus("Laporan berhasil disusun. Periksa dan edit bila diperlukan.");
 }catch(e){setStatus("Gagal AI: "+e.message)}
}
function saveReport(){
 const x=JSON.parse(localStorage.getItem("sikerja_identity")||"null");if(!x)return;
 const item={id:Date.now(),date:$("tanggal").value,nama:x.nama,jabatan:x.jabatan,unit:x.unit,target:$("target").value,uraian:$("hasil").value||$("uraian").value,output:$("output").value,kuantitas:$("kuantitas").value,realisasi:$("realisasi").value,persentase:$("persen").value};
 if(!item.uraian){alert("Belum ada uraian kinerja.");return}
 const h=JSON.parse(localStorage.getItem("sikerja_history")||"[]");h.unshift(item);localStorage.setItem("sikerja_history",JSON.stringify(h.slice(0,200)));renderHistory();setStatus("Laporan tersimpan di HP ini.");alert("Laporan berhasil disimpan.");
}
function renderHistory(){
 const h=JSON.parse(localStorage.getItem("sikerja_history")||"[]");const el=$("history");
 if(!h.length){el.textContent="Belum ada laporan.";return}
 el.innerHTML=h.map((x,i)=>`<div class="history-item"><span class="badge">${x.date}</span><br><b>${esc(x.target||"Kinerja Harian")}</b><br>${esc(x.uraian)}<br><span class="small">${esc(x.nama)} • ${esc(x.unit)}</span></div>`).join("")
}
function clearHistory(){if(confirm("Hapus seluruh riwayat pada HP ini?")){localStorage.removeItem("sikerja_history");renderHistory()}}
function esc(s){return String(s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
init();
</script>
</body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return INDEX_HTML

@app.get("/manifest.webmanifest")
def manifest():
    return {"name":"SIKERJA AI","short_name":"SIKERJA","start_url":"/","display":"standalone","background_color":"#f1f5f9","theme_color":"#0f766e","lang":"id"}

@app.post("/api/ai/transcribe")
async def transcribe(audio: UploadFile=File(...)):
    suffix=Path(audio.filename or "audio.webm").suffix or ".webm"
    data=await audio.read()
    if not data: raise HTTPException(400,"Audio kosong.")
    with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as f:
        f.write(data); path=f.name
    try:
        with open(path,"rb") as af:
            result=client().audio.transcriptions.create(
                model=os.getenv("OPENAI_TRANSCRIBE_MODEL","gpt-4o-mini-transcribe"),
                file=af,
                language="id"
            )
        return {"text":result.text}
    finally:
        try: os.unlink(path)
        except OSError: pass

@app.post("/api/ai/generate")
def generate(req: GenRequest):
    ident=req.identity or {}
    prompt=f"""Anda adalah asisten penyusun Laporan Kinerja Harian ASN Pemerintah Daerah Indonesia.

IDENTITAS:
Nama: {ident.get('nama','')}
Jabatan: {ident.get('jabatan','')}
Unit Kerja: {ident.get('unit','')}
Tanggal: {req.date}

UBAH CATATAN LISAN ASN MENJADI URAIAN KINERJA HARIAN YANG FORMAL, SPESIFIK, TERUKUR, DAN SESUAI TUGAS JABATAN. Jangan mengarang kegiatan yang tidak disebutkan. Jika catatan masih umum, rapikan tanpa menambah fakta material.

Contoh gaya:
- Menelaah disposisi surat dan arahan pimpinan serta menentukan tindak lanjut sesuai tugas dan fungsi Bagian.
- Melaksanakan koordinasi dengan perangkat daerah terkait untuk menindaklanjuti agenda dan penyelesaian pekerjaan.
- Menyusun/menelaah dokumen kedinasan berdasarkan hasil koordinasi dan arahan pimpinan.

KATEGORI TARGET YANG BOLEH DIPILIH SESUAI ISI:
Terlaksananya Perencanaan dan pengendalian internal
Terlaksananya Pengendalian inflasi/TPID
Terlaksananya Pembinaan BUMD
Terlaksananya UMKM dan pengembangan ekonomi daerah
Terlaksananya TPAKD dan akses keuangan daerah
Terlaksananya Kesejahteraan rakyat
Terlaksananya Administrasi dan disposisi pimpinan
Terlaksananya Monitoring dan evaluasi program
Terlaksananya Koordinasi lintas perangkat daerah
Terlaksananya Pelaporan dan tindak lanjut arahan pimpinan

Kembalikan JSON valid saja dengan field:
target, uraian, output, kuantitas, realisasi, persentase.
Output biasanya salah satu dari Dokumen/Laporan/Notulen/Rekomendasi, tetapi pilih yang paling sesuai.

CATATAN LISAN:
{req.spoken_text}
"""
    try:
        resp=client().responses.create(
            model=os.getenv("OPENAI_TEXT_MODEL","gpt-5.6-luna"),
            input=prompt,
            text={"format":{"type":"json_object"}}
        )
        return json.loads(resp.output_text)
    except Exception as e:
        raise HTTPException(500,f"Gagal menyusun laporan: {e}")
