import streamlit as st
import subprocess
import os

st.set_page_config(page_title="Chafiq Stream Panel", layout="wide")
st.title("📺 Chafiq Multi-Stream Control Panel")

# مخزن العمليات (Processes) باش نقدروا نحبسوهم
if 'processes' not in st.session_state:
    st.session_state.processes = {}

# واجهة إضافة بث جديد
with st.sidebar:
    st.header("➕ Add New Stream")
    stream_name = st.text_input("Stream Name (e.g. Channel 1)")
    m3u8_url = st.text_input("M3U8 Link")
    stream_key = st.text_input("Stream Key", type="password")
    
    if st.button("Save & Add"):
        if stream_name and m3u8_url and stream_key:
            if 'streams' not in st.session_state:
                st.session_state.streams = []
            st.session_state.streams.append({
                "name": stream_name,
                "url": m3u8_url,
                "key": stream_key
            })
            st.success(f"Added {stream_name}")

# عرض البثوث المضافة والتحكم فيها بالأزرار
if 'streams' in st.session_state:
    cols = st.columns(3) # عرض 3 بثوث فكل سطر
    for i, stream in enumerate(st.session_state.streams):
        with cols[i % 3]:
            st.info(f"**{stream['name']}**")
            
            # زرار التشغيل
            if st.button(f"▶️ Start {stream['name']}", key=f"start_{i}"):
                # كود FFmpeg مع اللوغو (Watermark)
                cmd = f'ffmpeg -re -i "{stream["url"]}" -i "logo.png" -filter_complex "overlay=W-w-10:10" -c:v libx264 -preset superfast -b:v 2500k -c:a aac -f flv "rtmp://a.rtmp.youtube.com/live2/{stream["key"]}"'
                
                # تشغيل في الخلفية
                process = subprocess.Popen(cmd, shell=True)
                st.session_state.processes[stream['name']] = process
                st.success(f"Stream {stream['name']} is LIVE!")

            # زرار الإيقاف
            if st.button(f"🛑 Stop {stream['name']}", key=f"stop_{i}"):
                if stream['name'] in st.session_state.processes:
                    st.session_state.processes[stream['name']].terminate()
                    st.warning(f"Stream {stream['name']} Stopped.")
