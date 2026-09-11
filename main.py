import os, json, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
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

@app.get("/")
def home():
    return FileResponse(BASE/"web"/"index.html")

@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(BASE/"web"/"manifest.webmanifest", media_type="application/manifest+json")

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
