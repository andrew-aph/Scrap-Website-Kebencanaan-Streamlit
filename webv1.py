import streamlit as st
import requests
from bs4 import BeautifulSoup
import csv
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
        "Jan": "Januari","Feb": "Februari","Mar": "Maret","Apr": "April",
        "May": "Mei","Jun": "Juni","Jul": "Juli","Aug": "Agustus",
        "Sep": "September","Oct": "Oktober","Nov": "November","Dec": "Desember",
        "January": "Januari","February": "Februari","March": "Maret","April": "April",
        "June": "Juni","July": "Juli","August": "Agustus","September": "September",
        "October": "Oktober","November": "November","December": "Desember"
    }

    try:
        date_str = date_str.replace("WIB", "").strip()

        if "," in date_str:
            date_str = date_str.split(",")[1].strip()
            parts = date_str.split()

            day = parts[0]
            month = bulan_map.get(parts[1], parts[1])
            year = parts[2]

            return f"{day} {month} {year}"

        elif re.search(r"\d{4}", date_str):

            parts = date_str.split()

            day = parts[0]
            month = bulan_map.get(parts[1], parts[1])
            year = parts[2]

            return f"{day} {month} {year}"

        else:
            return date_str

    except:
        return date_str


# =====================================================
# KONVERSI KE DATETIME
# =====================================================

def convert_to_datetime(df):

    bulan_map = {
        "Januari":"01","Februari":"02","Maret":"03","April":"04",
        "Mei":"05","Juni":"06","Juli":"07","Agustus":"08",
        "September":"09","Oktober":"10","November":"11","Desember":"12"
    }

    def parse_date(date_str):
        try:
            parts = date_str.split()

            day = parts[0]
            month = bulan_map.get(parts[1], "01")
            year = parts[2]

            return pd.to_datetime(f"{year}-{month}-{day}")

        except:
            return pd.NaT

    df["Tanggal_dt"] = df["Tanggal"].apply(parse_date)

    return df


# =====================================================
# SAVE CSV
# =====================================================

def save_to_csv(data, filename):

    with open(filename,"w",newline="",encoding="utf-8") as f:

        writer = csv.writer(f,delimiter=";")

        writer.writerow(["No","Judul","Tanggal","Link","Tag","Isi Berita"])

        writer.writerows(data)

    return filename


# =====================================================
# FILTER KEBENCANAAN
# =====================================================

def filter_kebencanaan(filename):

    df = pd.read_csv(filename,delimiter=";",encoding="utf-8")

    df_filtered = df[
        df['Tag'].str.contains(
            'bencana|banjir|puting beliung|gelombang pasang|abrasi|longsor|kekeringan|gempa|gunung meletus|erupsi|kebakaran hutan',
            case=False,
            na=False
        )
    ]

    return df_filtered


# =====================================================
# SCRAPER DETIK
# =====================================================

def scrape_detik(keywords, num_pages):

    data_list=[]
    seen_titles=set()
    index=1

    for keyword in keywords:

        base_url=f"https://www.detik.com/search/searchnews?query={keyword}&sortby=time&page={{}}"

        for page in range(1,num_pages+1):

            url=base_url.format(page)

            response=requests.get(url,headers=HEADERS)

            soup=BeautifulSoup(response.text,"html.parser")

            articles=soup.find_all("article")

            for article in articles:

                try:

                    link_tag=article.find("a")
                    title_tag=article.find("h3")

                    if not link_tag or not title_tag:
                        continue

                    link=link_tag["href"]
                    headline=title_tag.text.strip()

                    if headline in seen_titles:
                        continue

                    seen_titles.add(headline)

                    news=requests.get(link,headers=HEADERS)
                    news_soup=BeautifulSoup(news.text,"html.parser")

                    date_elem=news_soup.find("div",class_="detail__date")
                    date=date_elem.text.strip() if date_elem else ""
                    date=normalize_date(date)

                    content_section=news_soup.find("div",class_="detail__body-text")

                    content=""
                    if content_section:
                        paragraphs=content_section.find_all("p")
                        content=" ".join(p.text.strip() for p in paragraphs)

                    tag_section=news_soup.find("div",class_="nav")

                    tags=""
                    if tag_section:
                        tag_items=tag_section.find_all("a",class_="nav__item")
                        tag_list=[tag.text.strip() for tag in tag_items]
                        tags=", ".join(tag_list)

                    data_list.append([index,headline,date,link,tags,content])

                    index+=1

                except:
                    pass

    filename="detik_news.csv"
    save_to_csv(data_list,filename)

    return filter_kebencanaan(filename)


# =====================================================
# SCRAPER KOMPAS
# =====================================================

def scrape_kompas(keywords,num_pages):

    data_list=[]
    seen_titles=set()
    index=1

    for keyword in keywords:

        base_url=f"https://search.kompas.com/search?q={keyword}&sort=latest&page={{}}"

        for page in range(1,num_pages+1):

            url=base_url.format(page)

            response=requests.get(url,headers=HEADERS)

            soup=BeautifulSoup(response.text,"html.parser")

            articles=soup.find_all("div",class_="articleItem")

            for article in articles:

                try:

                    title_tag=article.find("h2",class_="articleTitle")
                    link_tag=article.find("a")

                    if not title_tag or not link_tag:
                        continue

                    headline=title_tag.text.strip()
                    link=link_tag["href"]

                    if headline in seen_titles:
                        continue

                    seen_titles.add(headline)

                    date_tag=article.find("div",class_="articlePost-date")
                    date=date_tag.text.strip() if date_tag else ""
                    date=normalize_date(date)

                    news=requests.get(link,headers=HEADERS)
                    news_soup=BeautifulSoup(news.text,"html.parser")

                    content_section=news_soup.find("div",class_="read__content")

                    content=""
                    if content_section:
                        paragraphs=content_section.find_all("p")
                        content=" ".join(p.text.strip() for p in paragraphs)

                    tag_section=news_soup.find("div",class_="tagsCloud-tag")

                    tags=""
                    if tag_section:
                        tag_items=tag_section.find_all("a")
                        tag_list=[tag.text.strip() for tag in tag_items]
                        tags=", ".join(tag_list)

                    data_list.append([index,headline,date,link,tags,content])

                    index+=1
                    time.sleep(1)

                except:
                    pass

    filename="kompas_news.csv"
    save_to_csv(data_list,filename)

    return filter_kebencanaan(filename)


# =====================================================
# SCRAPER METROTV
# =====================================================

def scrape_metrotv(keywords,num_pages):

    data_list=[]
    seen_titles=set()
    index=1

    for keyword in keywords:

        base_url=f"https://www.metrotvnews.com/search?query={keyword}&page={{}}"

        for page in range(1,num_pages+1):

            url=base_url.format(page)

            response=requests.get(url,headers=HEADERS)

            soup=BeautifulSoup(response.text,"html.parser")

            articles=soup.find_all("div",class_="item")

            for article in articles:

                try:

                    link_tag=article.find("a")
                    title_tag=article.find("h3")

                    if not link_tag or not title_tag:
                        continue

                    link=link_tag["href"]
                    title=title_tag.text.strip()

                    if link.startswith("/"):
                        link="https://www.metrotvnews.com"+link

                    if title in seen_titles:
                        continue

                    seen_titles.add(title)

                    news=requests.get(link,headers=HEADERS)
                    news_soup=BeautifulSoup(news.text,"html.parser")

                    date=""
                    date_tags=news_soup.select("p.date")

                    for tag in date_tags:
                        text=tag.get_text(strip=True)

                        if "•" in text:
                            date=text.split("•")[-1].strip()
                        else:
                            date=text

                    date=normalize_date(date)

                    content_section=news_soup.find("div",class_="news-text")

                    content=""
                    if content_section:
                        paragraphs=content_section.find_all("p")
                        content=" ".join(p.text.strip() for p in paragraphs)

                    tag_section=news_soup.find("div",class_="tag-content")

                    tags=""
                    if tag_section:
                        tag_items=tag_section.find_all("a")
                        tag_list=[tag.text.strip() for tag in tag_items]
                        tags=", ".join(tag_list)

                    data_list.append([index,title,date,link,tags,content])

                    index+=1
                    time.sleep(1)

                except:
                    pass

    filename="metrotv_news.csv"
    save_to_csv(data_list,filename)

    return filter_kebencanaan(filename)


# =====================================================
# STREAMLIT DASHBOARD
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

pages=st.sidebar.number_input(
    "Jumlah halaman scraping",
    min_value=1,
    max_value=20,
    value=1
)

run=st.sidebar.button("Mulai Scraping")


# =====================================================
# PROSES SCRAPING
# =====================================================

if run:

    all_df=[]

    with st.spinner("Sedang scraping berita..."):

        for site in websites:

            st.write(f"Scraping {site}")

            if site=="Detik":
                df=scrape_detik(keywords,pages)

            elif site=="Kompas":
                df=scrape_kompas(keywords,pages)

            elif site=="MetroTV":
                df=scrape_metrotv(keywords,pages)

            df["Website"]=site

            all_df.append(df)

    final_df=pd.concat(all_df,ignore_index=True)

    final_df=convert_to_datetime(final_df)

    final_df=final_df.sort_values(by="Tanggal_dt",ascending=False)

    st.session_state["data_scraping"]=final_df


# =====================================================
# TAMPILKAN DATA
# =====================================================

if "data_scraping" in st.session_state:

    final_df=st.session_state["data_scraping"]

    st.success("Scraping selesai")

    st.subheader("Filter Data Berdasarkan Tanggal")

    col1,col2=st.columns(2)

    with col1:
        start_date=st.date_input(
            "Tanggal Mulai",
            value=final_df["Tanggal_dt"].min()
        )

    with col2:
        end_date=st.date_input(
            "Tanggal Akhir",
            value=final_df["Tanggal_dt"].max()
        )

    filtered_df=final_df[
        (final_df["Tanggal_dt"]>=pd.to_datetime(start_date)) &
        (final_df["Tanggal_dt"]<=pd.to_datetime(end_date))
    ]

    filtered_df=filtered_df.sort_values(by="Tanggal_dt",ascending=False)

    filtered_df=filtered_df.reset_index(drop=True)

    filtered_df["No"]=filtered_df.index+1

    filtered_df=filtered_df.drop(columns=["Tanggal_dt"])

    tab1,tab2=st.tabs(["📄 Data","📖 Detail Berita"])

    with tab1:

        st.dataframe(filtered_df,use_container_width=True)

        csv=filtered_df.to_csv(index=False,sep=";").encode("utf-8")

        st.download_button(
            "Download CSV",
            csv,
            "hasil_scraping_semua_website.csv",
            "text/csv"
        )

    with tab2:

        for i,row in filtered_df.iterrows():

            with st.expander(row["Judul"]):

                st.write("Tanggal :",row["Tanggal"])
                st.write("Website :",row["Website"])
                st.write("Tag :",row["Tag"])
                st.write("Link :",row["Link"])

                st.write("Isi Berita :")
                st.write(row["Isi Berita"])
