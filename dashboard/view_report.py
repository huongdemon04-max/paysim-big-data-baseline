"""9B — Báo cáo nghiệp vụ. Năm vùng AFTER, không thay phép tính."""
import altair as alt
import pandas as pd
import streamlit as st
from dashboard_core import PAGES, fmt_int, fmt_float, fmt_pct, detector_metrics, render_page, render_confusion_matrix

PAGE_CONFIG=dict(page_title="PaySim | Business review",layout="centered",initial_sidebar_state="collapsed")

# BEFORE Start — 9B.1
# Dashboard rộng với sidebar và tiêu đề vận hành.
# BEFORE END — 9B.1
# AFTER Start — 9B.1: trang báo cáo có khổ đọc, typography serif, mục lục ngang.
def setup():
    st.markdown('''<style>
    [data-testid="stAppViewContainer"],[data-testid="stHeader"] {background:#faf7ef;}
    .block-container {max-width:1120px;padding-top:4.5rem;}
    h1,h2,h3 {font-family:Georgia,serif!important;color:#302c23!important;}
    [data-testid="stMetric"] {padding:10px 0;border-bottom:1px solid #d9cfb9;}
    [data-testid="stMetricValue"] {font-family:Georgia,serif;font-size:2.3rem;color:#624d28;}
    .report-masthead {font:12px monospace;letter-spacing:4px;border-bottom:3px solid #302c23;padding-bottom:12px;}
    </style>''',unsafe_allow_html=True)
    st.markdown('<div class="report-masthead">NHOM 2 / BUSINESS INTELLIGENCE</div>',unsafe_allow_html=True)
    st.title("Giao dịch & rủi ro")
    st.caption("Báo cáo kết quả xử lý và chất lượng phát hiện gian lận")
    return st.selectbox("Mục lục báo cáo",PAGES,key="dashboard_page")
# AFTER END — 9B.1

# BEFORE Start — 9B.2
# Sáu thẻ KPI giống nhau, ưu tiên tốc độ vận hành.
# BEFORE END — 9B.2
# AFTER Start — 9B.2: hai số liệu chủ đạo, số liệu vận hành đưa xuống cuối báo cáo.
def headline(s):
    st.caption(f"RUN {s.run_id}  /  {s.status.upper()}")
    left,right=st.columns([3,2])
    with left:
        st.markdown("### 01 / Quy mô xử lý")
        st.metric("Spark đã xử lý",fmt_int(s.processed),delta=f"{fmt_int(s.lag)} đang chờ")
        st.caption(f"Nguồn đã phát {fmt_int(s.emitted)} giao dịch trong run này.")
    with right:
        st.markdown("### 02 / Cảnh báo gian lận")
        
        st.metric(
            "Fraud alerts",
            fmt_int(s.alerts_count),
            delta=fmt_pct(s.model['Alert rate']),
            delta_color="inverse",
        )
        st.caption("Alert là kết quả dự đoán, không đồng nghĩa fraud c tế.")
# AFTER END — 9B.2

# BEFORE Start — 9B.3
# So sánh model bằng bảng trên một trang riêng.
# BEFORE END — 9B.3
# AFTER Start — 9B.3: đối chiếu chất lượng bằng thanh ngang trên trang báo cáo chính.
def comparison(s):
    st.markdown("### 03 / Chất lượng phát hiện")
    rows=[]
    for key,name in [('rule','Spark SQL rule'),('model','Spark MLlib')]:
        values=detector_metrics(s.evaluation,key)
        rows.extend({'Chỉ số':metric,'Detector':name,'Giá trị':values[metric]} for metric in ['Precision','Recall','F1'])
    chart=alt.Chart(pd.DataFrame(rows)).mark_bar(size=13).encode(
        y=alt.Y('Chỉ số:N',title=None),x=alt.X('Giá trị:Q',scale=alt.Scale(domain=[0,1]),axis=alt.Axis(format='%'),title=None),
        yOffset='Detector:N',color=alt.Color('Detector:N',scale=alt.Scale(range=["#dac097",'#38665b']),legend=alt.Legend(orient='bottom')),
        tooltip=['Chỉ số','Detector',alt.Tooltip('Giá trị:Q',format='.2%')],
    ).properties(height=210)
    st.altair_chart(chart)
# AFTER END — 9B.3

# BEFORE Start — 9B.4
# Phân phối giao dịch là donut ở trang dòng dữ liệu.
# BEFORE END — 9B.4
# AFTER Start — 9B.4: phân phối bằng thanh ngang, confusion matrix đặt cạnh kết quả model.
def business(s):
    left,right=st.columns([3,2])
    with left: comparison(s)
    with right:
        st.markdown("### Kết quả phân loại")
        render_confusion_matrix(s.model)
    st.markdown("### 04 / Cơ cấu giao dịch")
    if s.aggregates:
       
        chart = (
            alt.Chart(pd.DataFrame(s.aggregates))
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                y=alt.Y(
                    "type:N",
                    sort="-x",
                    title=None,
                    axis=alt.Axis(labelOverlap=False),
                ),
                x=alt.X(
                    "transactions:Q",
                    title="Số giao dịch",
                ),
                color=alt.Color(
                    "type:N",
                    title="Loại giao dịch",
                    scale=alt.Scale(
                        domain=[
                            "TRANSFER",
                            "CASH_OUT",
                            "PAYMENT",
                            "CASH_IN",
                            "DEBIT",
                        ],
                        range=[
                            "#EF4444",
                            "#F59E0B",
                            "#64748B",
                            "#2B6CB0",
                            "#A0AEC0",
                        ],
                    ),
                    legend=None,
                ),
                tooltip=[
                    "type",
                    "transactions",
                    "total_amount",
                    "model_alerts",
                    "rule_alerts",
                ],
            )
            .properties(
                height=210,
                background="#faf7ef",
            )
        )
        st.altair_chart(chart, use_container_width=True)

# AFTER END — 9B.4

# BEFORE Start — 9B.5
# Biểu đồ vận hành và sơ đồ pipeline đứng trước phần nghiệp vụ.
# BEFORE END — 9B.5
# AFTER Start — 9B.5: báo cáo nghiệp vụ trước; chỉ số vận hành và phụ lục ở cuối.
def render(s,page):
    headline(s)
    if page==PAGES[0]: business(s)
    else: render_page(s,page)
    st.markdown("### Thông số vận hành")
    a,b,c,d=st.columns(4)
    a.metric('Nguồn đã phát',fmt_int(s.emitted))
    b.metric('Ingest hiện tại',f"{fmt_float(s.run.get('instant_emission_rate'))} ev/s")
    c.metric('Processing throughput',f"{fmt_float(s.latest_metric.get('processing_throughput'))} ev/s")
    d.metric('End-to-end latency p95',f"{fmt_float(s.latest_metric.get('latency_p95_ms'),0)} ms")
    with st.expander("Phụ lục: telemetry theo micro-batch"):
        render_page(s,PAGES[0])
    st.caption(f"Dataset cycle {s.run.get('source_cycle',1)} · dòng {fmt_int(s.run.get('source_row'))}/{fmt_int(s.run.get('dataset_rows'))} · tiến độ {min(float(s.run.get('source_progress_pct',0)),1.0):.2%}")
    st.caption("Nguồn: snapshot MongoDB của run đang hiển thị · cập nhật mỗi 2 giây")
# AFTER END — 9B.5
