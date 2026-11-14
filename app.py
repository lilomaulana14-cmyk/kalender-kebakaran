"""
Kalender Aktivitas Kebakaran — harmonisasi MODIS & VIIRS
NASA Space Apps Challenge 2026 · Local Event Yogyakarta
"""

import pandas as pd
import plotly.express as px
import streamlit as st

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
         "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

st.set_page_config(page_title="Kalender Kebakaran", layout="wide")
st.title("Kalender Aktivitas Kebakaran")
st.caption("Harmonisasi MODIS & VIIRS · data titik api NASA FIRMS · 2000–2026")


# ======================================================================
# 1. BACA DATA
# ======================================================================

AREA = {
    "Kalimantan Tengah": "agregat_kalteng.csv",
    "Indonesia": "agregat_indonesia.csv",
}

kolom_kiri, kolom_kanan = st.columns(2)
with kolom_kiri:
    nama_area = st.selectbox("Area", list(AREA.keys()))
with kolom_kanan:
    satuan = st.radio("Satuan kalender", ["Skala VIIRS", "Skala MODIS"],
                      horizontal=True)

d = pd.read_csv(AREA[nama_area])


# ======================================================================
# 2. SUSUN JADI TABEL tahun-bulan x sensor
# ======================================================================

# PILIHAN METODE: semua pita kepercayaan dipakai (l, n, h).
# Kalau mau menyaring, ganti baris di bawah ini, misalnya:
#     d = d[d["pita"].isin(["n", "h"])]

per_sensor = (
    d.groupby(["tahun", "bulan", "sensor"])["n"].sum()
    .unstack("sensor")
    .fillna(0)
)

for s in ["MODIS", "VIIRS_SNPP", "VIIRS_NOAA20"]:
    if s not in per_sensor.columns:
        per_sensor[s] = 0.0

# Gabungkan dua satelit VIIRS jadi satu kolom.
# S-NPP dipakai lebih dulu; NOAA-20 mengisi saat S-NPP tidak ada
# (S-NPP berhenti 2 November 2026).
per_sensor["VIIRS"] = per_sensor["VIIRS_SNPP"].where(
    per_sensor["VIIRS_SNPP"] > 0, per_sensor["VIIRS_NOAA20"]
)


# ======================================================================
# 3. HITUNG RASIO DARI PERIODE TUMPANG-TINDIH
# ======================================================================

# Hanya bulan-bulan ketika KEDUA sensor sama-sama mendeteksi.
tumpang = per_sensor[(per_sensor["MODIS"] > 0) & (per_sensor["VIIRS"] > 0)]

# PILIHAN METODE: rasio dihitung dari TOTAL, bukan rata-rata rasio bulanan.
# Alasan: bulan dengan sedikit kebakaran menghasilkan rasio yang liar
# (3 banding 1 = 3,0), dan merata-ratakannya memberi bobot sama pada
# bulan sepi dan bulan puncak. Total memberi bobot sesuai aktivitas.
rasio = tumpang["VIIRS"].sum() / tumpang["MODIS"].sum()


# ======================================================================
# 4. HARMONISASI
# ======================================================================

# Aturan: pakai VIIRS bila ada (lebih tajam); bila tidak ada,
# naikkan MODIS dengan rasio supaya setara skala VIIRS.
harmoni_viirs = per_sensor["VIIRS"].where(
    per_sensor["VIIRS"] > 0, per_sensor["MODIS"] * rasio
)

if satuan == "Skala MODIS":
    harmoni = harmoni_viirs / rasio
    mentah = per_sensor["MODIS"] + per_sensor["VIIRS"]
else:
    harmoni = harmoni_viirs
    mentah = per_sensor["MODIS"] + per_sensor["VIIRS"]


# ======================================================================
# 5. TAMPILKAN
# ======================================================================

# ---- angka pembuka: yang membuat orang berhenti menggulir ----
per_tahun = harmoni.groupby("tahun").sum()
per_bulan = harmoni.groupby("bulan").sum()

tahun_ini = int(per_tahun.index.max())
peringkat = int((per_tahun > per_tahun.loc[tahun_ini]).sum()) + 1
musim = per_bulan.loc[[8, 9, 10]].sum() / per_bulan.sum() * 100
bulan_puncak = BULAN[int(per_bulan.idxmax()) - 1]

h1, h2, h3 = st.columns(3)
h1.metric(f"Kebakaran terjadi di Agu–Okt", f"{musim:.0f}%",
          help="Bagian dari seluruh deteksi 26 tahun yang jatuh di tiga bulan ini")
h2.metric(f"Peringkat {tahun_ini} dalam 26 tahun", f"ke-{peringkat}",
          help="Semakin kecil, semakin parah")
h3.metric("Bulan terparah sepanjang sejarah", bulan_puncak)

st.markdown(
    f"""
Kebakaran gambut Indonesia tidak menyebar seperti kebakaran hutan biasa.
Apinya **membara di bawah permukaan** — tanpa nyala, pada suhu jauh lebih
rendah, dan bisa bertahan berbulan-bulan setelah asap di permukaan hilang.

Jejak panas permukaannya kecil. Justru karena itu, satelit dengan piksel
besar sering **melewatkannya**.

> *[ISI SENDIRI — satu paragraf: kenapa ini penting bagi orang yang tinggal
> di sana, dan apa yang bisa dilakukan petugas dengan kalender ini.]*
"""
)

with st.expander("Bagaimana dua sensor ini disatukan"):
    st.markdown(
        f"""
NASA mendeteksi titik api dengan dua instrumen berbeda:

| | piksel | mulai |
|---|---|---|
| **MODIS** (Terra, Aqua) | ~1 km | 2000 |
| **VIIRS** (Suomi NPP, NOAA-20) | ~375 m | 2012 |

Piksel VIIRS luasnya sekitar **tujuh kali lebih kecil**, jadi api yang sama
mengisi bagian yang jauh lebih besar dari satu piksel dan terdeteksi lebih
mudah. Akibatnya, pada wilayah dan periode yang sama VIIRS mencatat
**{rasio:.2f}× lebih banyak** titik api daripada MODIS — diukur dari
**{len(tumpang)} bulan** ketika keduanya beroperasi bersamaan.

Selisih itu berasal dari sensornya, bukan dari jumlah kebakaran. Menjumlahkan
keduanya mentah-mentah akan memunculkan lonjakan palsu pada 2012, saat VIIRS
mulai mengudara. Rasio di atas dipakai untuk menghapus lonjakan itu.
        """
    )


def jadi_kalender(seri):
    """Ubah seri (tahun, bulan) jadi grid tahun x bulan."""
    g = seri.unstack("bulan").reindex(columns=range(1, 13)).fillna(0)
    g.columns = BULAN
    return g


def gambar(grid, judul):
    fig = px.imshow(
        grid,
        labels=dict(x="Bulan", y="Tahun", color="Titik api"),
        color_continuous_scale="Reds",   # satu warna, terang -> gelap
        aspect="auto",
    )
    fig.update_yaxes(dtick=1)
    fig.update_layout(title=judul, margin=dict(l=0, r=0, t=40, b=0), height=620)
    return fig


tab1, tabp, tab2, tab3, tab4 = st.tabs(
    ["Kalender harmonisasi", "Peta", "Bulan berjalan",
     "Sebelum vs sesudah", "Data"]
)

with tab1:
    # penggeser rentang tahun
    th_min = int(harmoni.index.get_level_values("tahun").min())
    th_maks = int(harmoni.index.get_level_values("tahun").max())
    dari, sampai = st.slider("Rentang tahun", th_min, th_maks,
                             (th_min, th_maks))

    pilih_tahun = harmoni[
        harmoni.index.get_level_values("tahun").isin(range(dari, sampai + 1))
    ]
    st.plotly_chart(gambar(jadi_kalender(pilih_tahun),
                           f"Setelah harmonisasi — {satuan.lower()}"),
                    width='stretch')


with tabp:
    # ---- peta sebaran titik api ----
    BERKAS_PETA = {
        "Kalimantan Tengah": "peta_kalteng.csv",
        "Indonesia": "peta_indonesia.csv",
    }

    try:
        p = pd.read_csv(BERKAS_PETA[nama_area])
    except FileNotFoundError:
        p = None
        st.warning("File peta belum ada. Jalankan `py agregasi_peta.py` dulu.")

    if p is not None:
        kiri, kanan = st.columns([1, 2])
        with kiri:
            sensor_peta = st.selectbox(
                "Sensor", sorted(p["sensor"].unique()),
                index=sorted(p["sensor"].unique()).index("VIIRS_SNPP")
                if "VIIRS_SNPP" in p["sensor"].values else 0,
                key="sensor_peta",
            )
        with kanan:
            p_min, p_maks = int(p["tahun"].min()), int(p["tahun"].max())
            th_dari, th_sampai = st.slider(
                "Rentang tahun", p_min, p_maks, (p_min, p_maks),
                key="tahun_peta",
            )

        titik = (
            p[(p["sensor"] == sensor_peta)
              & p["tahun"].between(th_dari, th_sampai)]
            .groupby(["lat", "lon"], as_index=False)["n"].sum()
        )

        if len(titik) == 0:
            st.info("Tidak ada deteksi pada pilihan ini.")
        else:
            # st.map membaca size dalam METER, sedangkan n bisa puluhan ribu.
            # Jadi diskalakan ke rentang 600 m - 11 km (kotaknya sendiri 25 km).
            n_maks = titik["n"].max()
            titik["ukuran"] = 600 + (titik["n"] / n_maks) * 10_400

            st.map(titik, latitude="lat", longitude="lon",
                   size="ukuran", color="#d62728")
            m1, m2, m3 = st.columns(3)
            m1.metric("Kotak dengan titik api", f"{len(titik):,}")
            m2.metric("Total deteksi", f"{int(titik['n'].sum()):,}")
            m3.metric("Kotak terpadat", f"{int(titik['n'].max()):,}")

        st.caption(
            f"Tiap lingkaran = satu kotak 0,25° (±25 km). Ukurannya "
            f"sebanding dengan jumlah deteksi {sensor_peta} pada "
            f"{th_dari}–{th_sampai}. Peta menampilkan deteksi mentah per "
            f"sensor, bukan angka hasil harmonisasi — harmonisasi dipakai "
            f"untuk membandingkan **waktu**, sedangkan peta menunjukkan "
            f"**tempat**."
        )


with tab2:
    # ---- bulan berjalan dibanding median historis ----
    # Ini yang diminta challenge: bandingkan aktivitas bulan berjalan
    # dengan median historis bulan yang sama.
    tahun_akhir = int(harmoni.index.get_level_values("tahun").max())
    terakhir = harmoni.loc[tahun_akhir]
    bulan_akhir = int(terakhir.index.max())

    nilai_kini = float(terakhir.loc[bulan_akhir])

    # median bulan yang sama, dari semua tahun SEBELUMNYA
    sejarah = harmoni[
        (harmoni.index.get_level_values("bulan") == bulan_akhir)
        & (harmoni.index.get_level_values("tahun") < tahun_akhir)
    ]
    median_sejarah = float(sejarah.median())

    st.subheader(f"{BULAN[bulan_akhir - 1]} {tahun_akhir}")

    k1, k2, k3 = st.columns(3)
    k1.metric("Bulan ini", f"{nilai_kini:,.0f}")
    k2.metric(f"Median {BULAN[bulan_akhir - 1]} ({th_min}–{tahun_akhir - 1})",
              f"{median_sejarah:,.0f}")

    if median_sejarah > 0:
        selisih = (nilai_kini - median_sejarah) / median_sejarah * 100
        k3.metric("Selisih dari median", f"{selisih:+.0f}%",
                  delta=f"{selisih:+.0f}%")
        if selisih > 50:
            st.error(f"Aktivitas kebakaran **jauh di atas** median historis "
                     f"untuk bulan {BULAN[bulan_akhir - 1]}.")
        elif selisih < -50:
            st.success("Aktivitas kebakaran jauh di bawah median historis.")
        else:
            st.info("Aktivitas kebakaran mendekati median historis.")

    # perbandingan bulan ini terhadap semua tahun
    banding = sejarah.droplevel("bulan").rename("historis").to_frame()
    banding.loc[tahun_akhir] = nilai_kini
    st.bar_chart(banding, height=320)
    st.caption(
        f"Jumlah titik api bulan {BULAN[bulan_akhir - 1]} di tiap tahun. "
        f"Batang terakhir adalah bulan berjalan."
    )
    st.warning(
        f"**Keterbatasan:** bulan {BULAN[bulan_akhir - 1]} {tahun_akhir} belum "
        f"selesai — datanya berhenti pada tanggal unduhan. Median dihitung dari "
        f"bulan-bulan penuh, jadi perbandingan ini bukan setara dan cenderung "
        f"**merendahkan** aktivitas bulan berjalan."
    )

with tab3:
    st.markdown(
        "Tanpa harmonisasi, grafik melonjak tajam saat VIIRS mulai mengudara "
        "pada 2012 — lonjakan itu **palsu**, berasal dari sensornya, bukan "
        "dari kebakarannya."
    )
    tahunan = pd.DataFrame({
        "Dijumlahkan mentah": mentah.groupby("tahun").sum(),
        "Setelah harmonisasi": harmoni.groupby("tahun").sum(),
    })
    st.line_chart(tahunan)

with tab4:
    grid = jadi_kalender(harmoni).round(0).astype(int)
    st.dataframe(grid, width='stretch')
    st.download_button(
        "Unduh CSV",
        grid.to_csv().encode("utf-8"),
        file_name=f"kalender_{nama_area.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
