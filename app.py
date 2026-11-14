import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Kalender Kebakaran", layout="wide")

st.title("Kalender Aktivitas Kebakaran")
st.caption("Lahan gambut Kalimantan Tengah · data titik api NASA FIRMS")

# ---- baca data ----
d = pd.read_csv("agregat_kalteng.csv")

# ---- pilihan pengguna ----
sensor = st.selectbox("Sensor", sorted(d["sensor"].unique()))

# ---- saring dan susun jadi tahun x bulan ----
pilih = d[d["sensor"] == sensor]

tabel = (
    pilih.pivot_table(index="tahun", columns="bulan", values="n", aggfunc="sum")
    .reindex(columns=range(1, 13))      # pastikan 12 bulan selalu ada
    .fillna(0)
)

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
         "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
tabel.columns = BULAN

# ---- gambar kalender ----
fig = px.imshow(
    tabel,
    labels=dict(x="Bulan", y="Tahun", color="Titik api"),
    color_continuous_scale="Reds",     # satu warna, terang -> gelap
    aspect="auto",
)
fig.update_yaxes(dtick=1)
fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=600)

st.plotly_chart(fig, use_container_width=True)

# ---- tabel angkanya, bagi yang mau baca persis ----
with st.expander("Lihat angkanya"):
    st.dataframe(tabel.astype(int), use_container_width=True)
