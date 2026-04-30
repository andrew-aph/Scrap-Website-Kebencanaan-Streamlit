import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from datetime import datetime
import re

# =====================================================
# CONFIG PAGE
# =====================================================

st.set_page_config(
    page_title="Berita Kebencanaan",
    page_icon="🌍",
    layout="wide"
)

# =====================================================
# SYSTEM THEME (AUTO LIGHT / DARK)
# =====================================================

st.markdown("""
<style>

/* Warna dasar mengikuti sistem */
.stApp{
background-color:transparent;
}

/* Text default */
.main h1,.main h2,.main h3,.main p,.main span,.main label,.main div{
color:inherit;
}

/* Button */
div.stButton > button,
div.stDownloadButton > button,
div.stLinkButton > a{
background-color:#38a169;
color:white;
border-radius:8px;
border:none;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover{
background-color:#48bb78;
}

/* METRIC CARD */
[data-testid="stMetric"]{
border-radius:12px;
padding:20px;
border:1px solid rgba(0,0,0,0.1);
}

/* DARK MODE STYLE */
@media (prefers-color-scheme: dark){

[data-testid="stMetric"]{
background:#1f2937;
border:1px solid #374151;
}

.stDataFrame thead tr th{
background:#1f2937 !important;
}

}

/* LIGHT MODE STYLE */
@media (prefers-color-scheme: light){

[data-testid="stMetric"]{
background:#f9fafb;
border:1px solid #e5e7eb;
}

.stDataFrame thead tr th{
background:#f3f4f6 !important;
}

}

</style>
""", unsafe_allow_html=True)

HEADERS={"User-Agent":"Mozilla/5.0"}

# =====================================================
# NORMALISASI TANGGAL
# =====================================================

def normalize_date(date_str):

    bulan_map={
        "Jan":"Januari","Feb":"Februari","Mar":"Maret","Apr":"April",
        "May":"Mei","Jun":"Juni","Jul":"Juli","Aug":"Agustus",
        "Sep":"September","Oct":"Oktober","Nov":"November","Dec":"Desember",
        "January":"Januari","February":"Februari","March":"Maret",
        "June":"Juni","July":"Juli","August":"Agustus",
        "October":"Oktober","December":"Desember"
    }

    try:
        date_str=date_str.replace("WIB","").strip()

        if "," in date_str:
            date_str=date_str.split(",")[1].strip()

        parts=date_str.split()

        day=str(int(parts[0]))
        month=bulan_map.get(parts[1],parts[1])
        year=parts[2]

        return f"{day} {month} {year}"

    except:
        return date_str


# =====================================================
# PARSE DATETIME
# =====================================================

def parse_date_to_datetime(date_str):

    bulan_map={
        "Januari":"01","Februari":"02","Maret":"03","April":"04",
        "Mei":"05","Juni":"06","Juli":"07","Agustus":"08",
        "September":"09","Oktober":"10","November":"11","Desember":"12"
    }

    try:

        parts=date_str.split()

        day=parts[0]
        month=bulan_map.get(parts[1],"01")
        year=parts[2]

        return pd.to_datetime(f"{year}-{month}-{day}")

    except:
        return None


# =====================================================
# FILTER TAG KEBENCANAAN
# =====================================================

def is_kebencanaan(tag):

    if tag is None:
        return False

    keywords=[
        "bencana","banjir","puting beliung","gelombang pasang",
        "abrasi","longsor","kekeringan","gempa",
        "gunung meletus","erupsi","kebakaran hutan"
    ]

    tag=tag.lower()

    return any(k in tag for k in keywords)

# =====================================================
# DAFTAR PROVINSI INDONESIA
# =====================================================

PROVINSI_LIST = [
"Aceh","Sumatera Utara","Sumatera Barat","Riau","Kepulauan Riau",
"Jambi","Sumatera Selatan","Bangka Belitung","Bengkulu","Lampung",
"DKI Jakarta","Jawa Barat","Jawa Tengah","DI Yogyakarta","Jawa Timur",
"Banten","Bali","Nusa Tenggara Barat","Nusa Tenggara Timur",
"Kalimantan Barat","Kalimantan Tengah","Kalimantan Selatan",
"Kalimantan Timur","Kalimantan Utara",
"Sulawesi Utara","Sulawesi Tengah","Sulawesi Selatan",
"Sulawesi Tenggara","Gorontalo","Sulawesi Barat",
"Maluku","Maluku Utara","Papua","Papua Barat",
"Papua Selatan","Papua Tengah","Papua Pegunungan","Papua Barat Daya"
]

# =====================================================
# EKSTRAKSI INFORMASI BENCANA
# =====================================================

def extract_disaster_info(row):
    text = row["Isi Berita"]
    if not text:
        return pd.Series({"Provinsi": "-", "Jenis Bencana": "-", "Kronologis": "-"})

    text_lower = text.lower()

    # --- FUNGSI PEMBANTU ---
    def clean_number(match_group):
        if match_group:
            # Menghapus titik ribuan agar "18.500" menjadi "18500"
            num_str = re.sub(r'[^\d]', '', match_group)
            return num_str
        return "-"

    # Pattern untuk angka dengan titik (1.000) atau angka biasa (1000)
    num_pattern = r'(\d{1,3}(?:\.\d{3})*|\d+)'

    # --- 1. TERDAMPAK ---
    terdampak_kk = "-"
    kk_match = re.search(num_pattern + r'\s*kk', text_lower)
    if kk_match:
        terdampak_kk = clean_number(kk_match.group(1))

    terdampak_jiwa = "-"
    # Menangkap: "18.500 jiwa", "500 orang", dsb.
    jiwa_match = re.search(num_pattern + r'\s*(jiwa|orang)', text_lower)
    if jiwa_match:
        terdampak_jiwa = clean_number(jiwa_match.group(1))

    # --- 2. MENGUNGSI ---
    mengungsi_kk = "-"
    kk_m_match = re.search(num_pattern + r'\s*kk.*mengungsi', text_lower)
    if kk_m_match:
        mengungsi_kk = clean_number(kk_m_match.group(1))

    mengungsi_jiwa = "-"
    jiwa_m_match = re.search(num_pattern + r'\s*(jiwa|orang).*mengungsi', text_lower)
    if jiwa_m_match:
        mengungsi_jiwa = clean_number(jiwa_m_match.group(1))

    # --- 3. RUMAH RUSAK ---
    rumah_rusak = "-"
    rumah_match = re.search(num_pattern + r'\s*rumah', text_lower)
    if rumah_match:
        rumah_rusak = clean_number(rumah_match.group(1))

    # --- 4. KORBAN MENINGGAL / HILANG ---
    korban_meninggal = "-"
    # Menambahkan 'hilang' karena angka 18.500 di teks Anda diikuti kata 'hilang'
    meninggal_match = re.search(num_pattern + r'\s*(orang|jiwa)?\s*(meninggal|tewas|hilang)', text_lower)
    if meninggal_match:
        korban_meninggal = clean_number(meninggal_match.group(1))

    # --- 5. KORBAN LUKA ---
    korban_luka = "-"
    luka_match = re.search(num_pattern + r'\s*(orang|jiwa)?\s*luka', text_lower)
    if luka_match:
        korban_luka = clean_number(luka_match.group(1))

    # --- 6. IDENTIFIKASI PROVINSI & JENIS (Tetap Sama) ---
    provinsi = "-"
    for prov in PROVINSI_LIST:
        if prov.lower() in text_lower:
            provinsi = prov
            break

    jenis = "-"
    mapping_bencana = {
        "banjir": "Banjir",
        "puting beliung": "Puting Beliung",
        "rob": "Gelombang Pasang",
        "abrasi": "Abrasi",
        "longsor": "Tanah Longsor",
        "kekeringan": "Kekeringan",
        "gempa": "Gempa Bumi",
        "erupsi": "Gunung Meletus",
        "karhutla": "Kebakaran Hutan"
    }
    
    for key, val in mapping_bencana.items():
        if key in text_lower:
            jenis = val
            break

    return pd.Series({
        "Provinsi": provinsi,
        "Jenis Bencana": jenis,
        "Kronologis": text[:300] + "...",
        "Link Berita": row["Link"] if row["Link"] else "-",
        "Terdampak KK": terdampak_kk,
        "Terdampak Jiwa": terdampak_jiwa,
        "Mengungsi KK": mengungsi_kk,
        "Mengungsi Jiwa": mengungsi_jiwa,
        "Korban Meninggal": korban_meninggal,
        "Korban Luka": korban_luka,
        "Rumah Rusak": rumah_rusak
    })

# =====================================================
# SCRAPER DETIK
# =====================================================

def scrape_detik(keywords,start_date,end_date):

    seen=set()

    for keyword in keywords:

        page=1
        stop=False

        while not stop:

            url=f"https://www.detik.com/search/searchnews?query={keyword}&sortby=time&page={page}"

            r=requests.get(url,headers=HEADERS)
            soup=BeautifulSoup(r.text,"html.parser")

            articles=soup.find_all("article")

            if len(articles)==0:
                break

            for article in articles:

                try:

                    link=article.find("a")["href"]
                    title=article.find("h3").text.strip()

                    if title in seen:
                        continue

                    seen.add(title)

                    news=requests.get(link,headers=HEADERS)
                    ns=BeautifulSoup(news.text,"html.parser")

                    date_elem=ns.find("div",class_="detail__date")
                    date=date_elem.text.strip() if date_elem else ""

                    date=normalize_date(date)
                    date_dt=parse_date_to_datetime(date)

                    if date_dt is None:
                        continue

                    if date_dt < pd.to_datetime(start_date):
                        stop=True
                        break

                    if not(pd.to_datetime(start_date)<=date_dt<=pd.to_datetime(end_date)):
                        continue

                    content=""
                    section=ns.find("div",class_="detail__body-text itp_bodycontent")

                    if section:
                        content=" ".join(p.text.strip() for p in section.find_all("p"))
                        content=content.replace("SCROLL TO CONTINUE WITH CONTENT","")

                    tags=""
                    tag_section=ns.find("div",class_="nav")

                    if tag_section:
                        tags=", ".join(t.text.strip() for t in tag_section.find_all("a"))

                    if not is_kebencanaan(tags):
                        continue

                    yield{
                        "Judul":title,
                        "Tanggal":date,
                        "Link":link,
                        "Tag":tags,
                        "Isi Berita":content
                    }

                except:
                    pass

            page+=1


# =====================================================
# SCRAPER KOMPAS
# =====================================================

def scrape_kompas(keywords,start_date,end_date):

    seen=set()

    for keyword in keywords:

        page=1
        stop=False

        while not stop:

            url=f"https://search.kompas.com/search?q={keyword}&sort=latest&page={page}"

            r=requests.get(url,headers=HEADERS)
            soup=BeautifulSoup(r.text,"html.parser")

            articles=soup.find_all("div",class_="articleItem")

            if len(articles)==0:
                break

            for article in articles:

                try:

                    title=article.find("h2",class_="articleTitle").text.strip()
                    link=article.find("a",class_="article-link")["href"]

                    if title in seen:
                        continue

                    seen.add(title)

                    date=article.find("div",class_="articlePost-date").text.strip()

                    date=normalize_date(date)
                    date_dt=parse_date_to_datetime(date)

                    if date_dt is None:
                        continue

                    if date_dt < pd.to_datetime(start_date):
                        stop=True
                        break

                    if not(pd.to_datetime(start_date)<=date_dt<=pd.to_datetime(end_date)):
                        continue

                    news=requests.get(link,headers=HEADERS)
                    ns=BeautifulSoup(news.text,"html.parser")

                    content=""
                    section=ns.find("div",class_="read__content")

                    if section:
                        content=" ".join(p.text.strip() for p in section.find_all("p"))

                    tags=""
                    tag_section=ns.find("div",class_="tagsCloud-tag")

                    if tag_section:
                        tags=", ".join(t.text.strip() for t in tag_section.find_all("a"))

                    if not is_kebencanaan(tags):
                        continue

                    yield{
                        "Judul":title,
                        "Tanggal":date,
                        "Link":link,
                        "Tag":tags,
                        "Isi Berita":content
                    }

                    time.sleep(1)

                except:
                    pass

            page+=1


# =====================================================
# SCRAPER METROTV
# =====================================================

def scrape_metrotv(keywords,start_date,end_date):

    seen=set()

    for keyword in keywords:

        page=0
        stop=False

        while not stop:

            url=f"https://www.metrotvnews.com/search?query={keyword}&page={page}"

            r=requests.get(url,headers=HEADERS)
            soup=BeautifulSoup(r.text,"html.parser")

            articles=soup.find_all("div",class_="item")

            if len(articles)==0:
                break

            for article in articles:

                try:

                    link=article.find("a")["href"]
                    title=article.find("h3").text.strip()

                    if link.startswith("/"):
                        link="https://www.metrotvnews.com"+link

                    if title in seen:
                        continue

                    seen.add(title)

                    news=requests.get(link,headers=HEADERS)
                    ns=BeautifulSoup(news.text,"html.parser")

                    date=""
                    date_tags=ns.select("p.date")

                    for tag in date_tags:

                        text=tag.get_text(strip=True)

                        if "•" in text:
                            date=text.split("•")[-1].strip()
                        else:
                            date=text

                    date=normalize_date(date)
                    date_dt=parse_date_to_datetime(date)

                    if date_dt is None:
                        continue

                    if date_dt < pd.to_datetime(start_date):
                        stop=True
                        break

                    if not(pd.to_datetime(start_date)<=date_dt<=pd.to_datetime(end_date)):
                        continue

                    content=""
                    section=ns.find("div",class_="news-text")

                    if section:

                        for table in section.find_all("table"):
                            table.decompose()

                        for read in section.find_all("div",class_="readother"):
                            read.decompose()

                        paragraphs=[]

                        for p in section.find_all("p"):

                            text=p.get_text(" ",strip=True)

                            if "baca juga" in text.lower():
                                continue

                            paragraphs.append(text)

                        content=" ".join(paragraphs)

                    tags=""
                    tag_section=ns.find("div",class_="tag-content")

                    if tag_section:
                        tags=", ".join(t.text.strip() for t in tag_section.find_all("a"))

                    if not is_kebencanaan(tags):
                        continue

                    yield{
                        "Judul":title,
                        "Tanggal":date,
                        "Link":link,
                        "Tag":tags,
                        "Isi Berita":content
                    }

                    time.sleep(1)

                except:
                    pass

            page+=1


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.title("⚙️ Settings")

    websites=st.multiselect(
        "🌐 Sumber Berita",
        ["Detik","Kompas","MetroTV"]
    )

    keywords=st.multiselect(
        "🔑 Keyword",
        [
        "Bencana","Banjir","Puting Beliung","Gelombang Pasang",
        "Abrasi","Tanah Longsor","Kekeringan","Gempa Bumi",
        "Gunung Meletus","Kebakaran Hutan"
        ]
    )

    col1,col2=st.columns(2)

    start_date=col1.date_input("Mulai")
    end_date=col2.date_input("Akhir")

    run=st.button("🚀 Mulai Scraping",use_container_width=True)


# =====================================================
# MAIN UI
# =====================================================

st.title("🌍 Berita Kebencanaan")
st.caption("Dashboard monitoring berita kebencanaan nasional")

m1,m2,m3=st.columns(3)

met_total=m1.empty()
met_site=m2.empty()
met_status=m3.empty()

tab1,tab2,tab3=st.tabs(["📊 Dataset","📖 Detail Berita","📋 Tabel Kejadian Bencana"])

with tab1:

    status_box=st.empty()
    table_box=st.empty()

    if "data_scraping" in st.session_state and not run:

        df_old=st.session_state["data_scraping"]

        table_box.dataframe(df_old,use_container_width=True)

        met_total.metric("Total Berita",len(df_old))
        met_site.metric("Sumber",df_old["Website"].nunique())
        met_status.metric("Status","Selesai")


# =====================================================
# RUN SCRAPER
# =====================================================

if run:

    temp_data=[]
    status_text=[]

    for site in websites:

        status_text.append(f"⏳ {site}")
        status_box.info(" | ".join(status_text))

        with st.spinner(f"Scraping {site}..."):

            if site=="Detik":
                generator=scrape_detik(keywords,start_date,end_date)
            elif site=="Kompas":
                generator=scrape_kompas(keywords,start_date,end_date)
            elif site=="MetroTV":
                generator=scrape_metrotv(keywords,start_date,end_date)

            for row in generator:

                row["Website"]=site

                temp_data.append(row)

                df=pd.DataFrame(temp_data)

                df["Tanggal_dt"]=df["Tanggal"].apply(parse_date_to_datetime)

                df=df.sort_values("Tanggal_dt",ascending=False).reset_index(drop=True)

                df["No"]=df.index+1

                df=df[["No","Judul","Tanggal","Website","Tag","Link","Isi Berita"]]

                table_box.dataframe(df,use_container_width=True)

                met_total.metric("Total Berita",len(df))

        status_text[-1]=f"✅ {site}"

        status_box.success(" | ".join(status_text))

    if len(temp_data)>0:

        st.session_state["data_scraping"]=df

        met_site.metric("Sumber",df["Website"].nunique())
        met_status.metric("Status","Selesai")

        # =====================================================
        # MEMBUAT TABEL KEJADIAN BENCANA
        # =====================================================

        disaster_df = df.copy()

        info = disaster_df.apply(extract_disaster_info, axis=1)

        disaster_df = pd.concat([disaster_df, info], axis=1)

        disaster_df["Waktu Kejadian"] = disaster_df["Tanggal"]

        disaster_df = disaster_df[[
            "No",
            "Provinsi",
            "Jenis Bencana",
            "Waktu Kejadian",
            "Terdampak KK",
            "Terdampak Jiwa",
            "Mengungsi KK",
            "Mengungsi Jiwa",
            "Korban Meninggal",
            "Korban Luka",
            "Rumah Rusak",
            "Kronologis",
            "Link Berita"
        ]]

        st.session_state["tabel_bencana"] = disaster_df



# =====================================================
# DETAIL BERITA
# =====================================================

if "data_scraping" in st.session_state:

    final_df = st.session_state["data_scraping"]

    with tab2:

        search = st.text_input("🔍 Cari judul berita...", placeholder="Ketik judul...")

        if search:
            view_df = final_df[final_df["Judul"].str.contains(search, case=False)]
        else:
            view_df = final_df

        for i, row in view_df.iterrows():

            with st.expander(f"[{row['Website']}] {row['Judul']}"):

                col_left, col_right = st.columns([3,1])

                # KIRI = ISI BERITA
                with col_left:
                    st.write(row["Isi Berita"])

                # KANAN = META DATA
                with col_right:
                    st.info(f"📅 {row['Tanggal']}")
                    st.caption(f"🏷️ {row['Tag']}")

                    st.link_button(
                        "🔗 Kunjungi Berita",
                        row["Link"],
                        use_container_width=True
                    )

    st.divider()

    csv = final_df.to_csv(index=False, sep=";").encode("utf-8")

    st.download_button(
        "📥 Download CSV",
        csv,
        "hasil_scraping_berita.csv",
        "text/csv",
        use_container_width=True
    )

# =====================================================
# TABEL KEJADIAN BENCANA
# =====================================================

if "tabel_bencana" in st.session_state:

    with tab3:

        st.subheader("📋 Informasi Kejadian Bencana")

        tabel = st.session_state["tabel_bencana"]

        st.dataframe(
            tabel,
            use_container_width=True
        )

        csv2 = tabel.to_csv(index=False, sep=";").encode("utf-8")

        st.download_button(
            "📥 Download Tabel Bencana",
            csv2,
            "tabel_kejadian_bencana.csv",
            "text/csv",
            use_container_width=True
        )    