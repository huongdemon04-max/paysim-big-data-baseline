"""9A — Trung tâm vận hành. Năm vùng AFTER chỉ thay cách trình bày."""
import altair as alt
import pandas as pd
import streamlit as st
from dashboard_core import PAGES, fmt_int, fmt_float, fmt_pct, render_page

PAGE_CONFIG = dict(page_title="PaySim | Operations", layout="wide", initial_sidebar_state="expanded")

# BEFORE Start — 9A.1
# Tiêu đề lớn + sidebar System UIs của dashboard gốc.
# BEFORE END — 9A.1
# AFTER Start — 9A.1: khung điều hành tối, thanh điều hướng dọc.
def setup():
    st.markdown('''<style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#0b1726;color:#e0ecf5;}
    [data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,
    [data-testid="stMain"] p,[data-testid="stMetricValue"] {color:#e0ecf5;}
    [data-testid="stMetric"] {padding:12px;border-left:2px solid #2dd4bf;background:#12283c;}
    [data-testid="stMetricValue"] {font-size:1.65rem;}
    [data-testid="stMetricDelta"] {color:#a7f3d0;}
    [data-testid="stHeader"] button {color:#e0ecf5;}
    .block-container {padding-top:4.5rem;}
    [data-testid="stExpander"] summary {background:#12283c;color:#e0ecf5;}
    .ops-label {color:#63d9cc;font:12px monospace;letter-spacing:3px;}
    </style>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("## PAYSIM\n**OPERATIONS CONSOLE**")
        st.caption("Giám sát luồng giao dịch")
        page = st.radio("Không gian vận hành", PAGES, key="dashboard_page", label_visibility="collapsed")
        st.divider()
        st.link_button("HDFS ↗", "http://127.0.0.1:9870")
        st.link_button("Spark ↗", "http://127.0.0.1:4040")
    return page
# AFTER END — 9A.1

# BEFORE Start — 9A.2
# Sáu KPI nằm trong lưới 3 × 2 trước tất cả biểu đồ.
# BEFORE END — 9A.2
# AFTER Start — 9A.2: dải tốc độ trên cùng, số liệu rủi ro ở cột giám sát.
def summary(s):
    st.markdown('<div class="ops-label">STREAM MONITOR / PAYSIM</div>', unsafe_allow_html=True)
    st.markdown("## Trung tâm vận hành")
    st.caption(f"{s.status.upper()} · {s.run_id} · cập nhật mỗi 2 giây")
    a,b,c = st.columns(3)
    a.metric("Spark đã xử lý",fmt_int(s.processed),delta=f"{fmt_int(s.lag)} đang chờ")
    b.metric("Ingest hiện tại",f"{fmt_float(s.run.get('instant_emission_rate'))} ev/s")
    c.metric("Processing throughput",f"{fmt_float(s.latest_metric.get('processing_throughput'))} ev/s")
# AFTER END — 9A.2

# BEFORE Start — 9A.3
# Bốn biểu đồ đường cùng kích thước trên nền trắng.
# BEFORE END — 9A.3
# AFTER Start — 9A.3: biểu đồ tốc độ lớn, hai biểu đồ phụ trên nền tối.
def signal(s, fields, title, unit, height=250):
    frame=pd.DataFrame(s.metrics)
    available=[f for f in fields if f in frame]
    if frame.empty or not available:
        st.info("Đang chờ micro-batch telemetry đầu tiên."); return
    data=frame[['created_at',*available]].melt('created_at',var_name='Metric',value_name='Value')
    data['Metric']=data['Metric'].replace({'ingest_throughput':'Ingest','processing_throughput':'Processing','consumer_lag':'Events đang chờ','ingest_latency_p95_ms':'Ingest p95','latency_p95_ms':'End-to-end p95','batch_duration_seconds':'Batch duration'})
    chart=alt.Chart(data).mark_line(point=True,strokeWidth=2).encode(
        x=alt.X('created_at:T',title=None),y=alt.Y('Value:Q',title=unit),
        color=alt.Color('Metric:N',scale=alt.Scale(range=['#2dd4bf','#fbbf24']),legend=alt.Legend(orient='top')),
        tooltip=['created_at:T','Metric:N','Value:Q'],
    ).properties(height=height,title=title).configure(
        background='#12283c',view={'stroke':None},
        axis={'labelColor':'#b3c6d8','titleColor':'#b3c6d8','gridColor':'#243a50'},
        legend={'labelColor':'#b3c6d8','titleColor':'#b3c6d8'},title={'color':'#e0ecf5','anchor':'start'},
    )
    st.altair_chart(chart,theme=None)
# AFTER END — 9A.3

# BEFORE Start — 9A.4
# Pipeline dạng sơ đồ ngang luôn chiếm phần đầu trang.
# BEFORE END — 9A.4
# AFTER Start — 9A.4: cột giám sát và tiến độ nằm cạnh biểu đồ chính.
def watch(s):
    st.markdown("### Giám sát")
    st.metric("Fraud alerts",fmt_int(s.alerts_count),delta=fmt_pct(s.model['Alert rate']))
    st.metric("End-to-end latency p95",f"{fmt_float(s.latest_metric.get('latency_p95_ms'),0)} ms")
    st.metric("Nguồn đã phát",fmt_int(s.emitted))
    st.caption(f"Vòng dữ liệu {s.run.get('source_cycle',1)}")
    st.progress(min(float(s.run.get('source_progress_pct',0)),1.0))
    st.caption(f"Dòng {fmt_int(s.run.get('source_row'))}/{fmt_int(s.run.get('dataset_rows'))}")
    st.caption("Đối soát dữ liệu")
    st.write("PASS" if s.display_correct else "SYNCING")
# AFTER END — 9A.4

# BEFORE Start — 9A.5
# Một khung nội dung tuyến tính dùng chung cho mọi phiên bản.
# BEFORE END — 9A.5
# AFTER Start — 9A.5: workspace biểu đồ + cột giám sát, nhật ký batch ở cuối.
def render(s,page):
    summary(s)
    main,aside=st.columns([4,1])
    with aside: watch(s)
    with main:
        if page==PAGES[0]:
            signal(s,['ingest_throughput','processing_throughput'],'Tốc độ ingest và xử lý','Events/s',300)
            left,right=st.columns(2)
            with left: signal(s,['consumer_lag'],'Kafka consumer lag','Events',180)
            with right: signal(s,['ingest_latency_p95_ms','latency_p95_ms'],'Latency p95','ms',180)
            with st.expander("Micro-batch duration và nhật ký",expanded=True):
                signal(s,['batch_duration_seconds'],'Thời gian mỗi micro-batch','Seconds',100)
                if s.metrics:
                    frame=pd.DataFrame(s.metrics).sort_values('batch_id',ascending=False)
                    columns=[c for c in ['batch_id','created_at','input_rows','processed_rows','consumer_lag','processing_throughput','latency_p95_ms','invalid_rows','duplicate_removed','alerts'] if c in frame]
                    st.dataframe(frame[columns],hide_index=True,height=180)
        else:
            render_page(s,page)
# AFTER END — 9A.5
