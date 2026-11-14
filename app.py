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

a, b, c = st.columns(3)
a.metric("Rasio VIIRS : MODIS", f"{rasio:.2f}×")
b.metric("Bulan tumpang-tindih", f"{len(tumpang)}")
c.metric("Rentang", f"{int(per_sensor.index.get_level_values('tahun').min())}–"
                    f"{int(per_sensor.index.get_level_values('tahun').max())}")

st.info(
    f"VIIRS mendeteksi **{rasio:.2f}× lebih banyak** titik api daripada MODIS "
    f"pada periode dan wilayah yang sama. Selisih ini berasal dari ukuran "
    f"piksel (375 m vs 1 km), bukan dari jumlah kebakaran yang berbeda."
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
