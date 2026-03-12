import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import re

st.set_page_config(layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =====================================================
# NORMALISASI FORMAT TANGGAL
# =====================================================

def normalize_date(date_str):

    bulan_map = {
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

        day=parts[0]
        month=bulan_map.get(parts[1],parts[1])
        year=parts[2]

        return f"{day} {month} {year}"

    except:
        return date_str


# =====================================================
# KONVERSI KE DATETIME
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
# FILTER KEBENCANAAN
# =====================================================

def filter_kebencanaan(df):

    df=df[
        df['Tag'].str.contains(
            'bencana|banjir|puting beliung|gelombang pasang|abrasi|longsor|kekeringan|gempa|gunung meletus|erupsi|kebakaran hutan',
            case=False,
            na=False
        )
    ]

    return df


# =====================================================
# SCRAPER DETIK
# =====================================================

def scrape_detik(keywords,start_date,end_date):

    data=[]
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
                        content = content.replace("SCROLL TO CONTINUE WITH CONTENT", "")

                    tags=""
                    tag_section=ns.find("div",class_="nav")

                    if tag_section:
                        tags=", ".join(t.text.strip() for t in tag_section.find_all("a"))

                    data.append([title,date,link,tags,content])

                except:
                    pass

            page+=1

    df=pd.DataFrame(data,columns=["Judul","Tanggal","Link","Tag","Isi Berita"])

    return filter_kebencanaan(df)


# =====================================================
# SCRAPER KOMPAS
# =====================================================

def scrape_kompas(keywords,start_date,end_date):

    data=[]
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

                    data.append([title,date,link,tags,content])

                    time.sleep(1)

                except:
                    pass

            page+=1

    df=pd.DataFrame(data,columns=["Judul","Tanggal","Link","Tag","Isi Berita"])

    return filter_kebencanaan(df)


# =====================================================
# SCRAPER METROTV
# =====================================================

def scrape_metrotv(keywords,start_date,end_date):

    data=[]
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
                        for read in section.find_all("div", class_="readother"):
                            read.decompose()
                        content=" ".join(p.text.strip() for p in section.find_all("p"))

                    tags=""
                    tag_section=ns.find("div",class_="tag-content")

                    if tag_section:
                        tags=", ".join(t.text.strip() for t in tag_section.find_all("a"))

                    data.append([title,date,link,tags,content])

                    time.sleep(1)

                except:
                    pass

            page+=1

    df=pd.DataFrame(data,columns=["Judul","Tanggal","Link","Tag","Isi Berita"])

    return filter_kebencanaan(df)


# =====================================================
# DASHBOARD
# =====================================================

st.title("🌍 Dashboard Scraping Berita Kebencanaan")

st.sidebar.header("Pengaturan Scraping")

websites=st.sidebar.multiselect(
    "Pilih Website",
    ["Detik","Kompas","MetroTV"]
)

keywords=st.sidebar.multiselect(
    "Pilih Keyword",
    [
        "Bencana","Banjir","Puting Beliung","Gelombang Pasang",
        "Abrasi","Tanah Longsor","Kekeringan","Gempa Bumi",
        "Gunung Meletus","Kebakaran Hutan"
    ]
)

start_date=st.sidebar.date_input("Tanggal Mulai")
end_date=st.sidebar.date_input("Tanggal Akhir")

run=st.sidebar.button("Mulai Scraping")


# =====================================================
# RUN SCRAPER
# =====================================================

if run:

    all_df=[]

    with st.spinner("Sedang scraping berita..."):

        for site in websites:

            st.write(f"Scraping {site}")

            if site=="Detik":
                df=scrape_detik(keywords,start_date,end_date)

            elif site=="Kompas":
                df=scrape_kompas(keywords,start_date,end_date)

            elif site=="MetroTV":
                df=scrape_metrotv(keywords,start_date,end_date)

            df["Website"]=site

            all_df.append(df)

    final_df=pd.concat(all_df,ignore_index=True)

    final_df["Tanggal_dt"]=final_df["Tanggal"].apply(parse_date_to_datetime)

    final_df=final_df.sort_values("Tanggal_dt",ascending=False)

    final_df=final_df.reset_index(drop=True)

    final_df["No"]=final_df.index+1

    final_df=final_df[
        ["No","Judul","Tanggal","Website","Tag","Link","Isi Berita"]
    ]

    st.session_state["data_scraping"]=final_df


# =====================================================
# TAMPILKAN DATA
# =====================================================

if "data_scraping" in st.session_state:

    final_df=st.session_state["data_scraping"]

    tab1,tab2=st.tabs(["📄 Data","📖 Detail Berita"])

    with tab1:

        st.dataframe(final_df,use_container_width=True)

        csv=final_df.to_csv(index=False,sep=";").encode("utf-8")

        st.download_button(
            "Download CSV",
            csv,
            "hasil_scraping_berita.csv",
            "text/csv"
        )

    with tab2:

        for i,row in final_df.iterrows():

            with st.expander(row["Judul"]):

                st.write("Tanggal :",row["Tanggal"])
                st.write("Website :",row["Website"])
                st.write("Tag :",row["Tag"])
                st.write("Link :",row["Link"])
                st.write("Isi Berita :")
                st.write(row["Isi Berita"])