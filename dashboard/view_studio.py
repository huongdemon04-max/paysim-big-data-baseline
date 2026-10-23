"""9C — Bàn phân tích giao dịch. Chỉ lựa chọn cách xem dữ liệu đã có."""
import altair as alt
import pandas as pd
import streamlit as st
from dashboard_core import PAGES, fmt_int, fmt_float, fmt_pct, render_page

PAGE_CONFIG=dict(page_title="PaySim | Transaction workspace",layout="wide",initial_sidebar_state="collapsed")

# BEFORE Start — 9C.1
# Sidebar + tiêu đề lớn + điều hướng dưới sáu KPI.
# BEFORE END — 9C.1
# AFTER Start — 9C.1: thanh công cụ gọn, dữ liệu giao dịch là trang đầu.
def setup():
    st.markdown('''<style>
    [data-testid="stAppViewContainer"] {background:#f3f5f8;}
    .block-container {padding-top:4.5rem;max-width:1800px;}
    [data-testid="stMetric"] {padding:8px 12px;border-top:2px solid #4f46e5;background:white;}
    [data-testid="stMetricValue"] {font-size:1.35rem;}
    h1,h2,h3 {color:#20243b;}
    .workspace-brand {font:700 20px sans-serif;color:#343168;padding-bottom:14px;border-bottom:1px solid #d3d7e3;}
    </style>''',unsafe_allow_html=True)
    st.markdown('<div class="workspace-brand">▦ PAYSIM　/　Transaction workspace</div>',unsafe_allow_html=True)
    order=[PAGES[3],PAGES[2],PAGES[0],PAGES[1]]
    return st.segmented_control("Không gian phân tích",order,default=order[0],key='dashboard_page') or order[0]
# AFTER END — 9C.1

# BEFORE Start — 9C.2
# Bảng giao dịch nằm dưới toàn bộ KPI và sơ đồ pipeline.
# BEFORE END — 9C.2
# AFTER Start — 9C.2: bảng là vùng làm việc chính, giữ đủ 60 giao dịch như gốc.
def ledger(s):
    st.markdown("### Giao dịch vừa đi qua Spark")
    st.caption("60 giao dịch gần nhất · thứ tự scored_at giảm dần")
    if not s.recent_transactions:
        st.info("Đang chờ batch giao dịch mới.");return
    frame=pd.DataFrame(s.recent_transactions)
    columns=[c for c in ['scored_at','event_id','type','amount','risk_score','prediction','source_cycle','source_row','end_to_end_latency_ms'] if c in frame]
    st.dataframe(frame[columns],hide_index=True,height=480,column_config={
        'risk_score':st.column_config.ProgressColumn('Risk score',min_value=0,max_value=1,format='%.4f'),
        'amount':st.column_config.NumberColumn('Amount',format='%.2f'),
    })
# AFTER END — 9C.2

# BEFORE Start — 9C.3
# Chi tiết giao dịch chỉ có trong các cột của bảng.
# BEFORE END — 9C.3
# AFTER Start — 9C.3: bộ xem chi tiết cạnh bảng; không sửa hay chấm điểm lại bản ghi.
def inspector(s):
    st.markdown("### Chi tiết giao dịch")
    if not s.recent_transactions:return
    rows=s.recent_transactions
    index=st.selectbox('Chọn bản ghi',range(len(rows)),format_func=lambda i:str(rows[i].get('event_id',i)),key='inspection_row')
    row=rows[index]
    st.caption(str(row.get('type','')))
    st.markdown(f"## {fmt_float(row.get('amount'),2)}")
    score=float(row.get('risk_score',0))
    st.progress(min(max(score,0),1),text=f"Risk score: {score:.4f}")
    st.write('Cảnh báo' if row.get('prediction') else 'Không cảnh báo')
    st.caption(f"Scored at: {row.get('scored_at','—')}")
    st.caption(f"E2E latency: {fmt_float(row.get('end_to_end_latency_ms'),0)} ms")

# AFTER END — 9C.3

# BEFORE Start — 9C.4
# Donut tổng hợp và scatter alerts nằm trên hai trang riêng.
# BEFORE END — 9C.4
# AFTER Start — 9C.4: hai biểu đồ đối chiếu ngay dưới bảng để đọc cùng giao dịch.
def context(s):
    left,right=st.columns([1,2])
    with left:
        st.markdown("#### Số giao dịch theo nghiệp vụ")
        if s.aggregates:
            chart=alt.Chart(pd.DataFrame(s.aggregates)).mark_bar(color='#6366f1').encode(
                x=alt.X('type:N',title=None),y=alt.Y('transactions:Q',title='Transactions'),tooltip=['type','transactions'],
            ).properties(height=150)
            st.altair_chart(chart)
    with right:
        st.markdown("#### Risk score · 300 alerts mới nhất")
        if s.recent_alerts:
            chart=alt.Chart(pd.DataFrame(s.recent_alerts)).mark_circle(size=35,opacity=.6).encode(
                x=alt.X('amount:Q',scale=alt.Scale(type='log'),title='Amount'),y=alt.Y('risk_score:Q',scale=alt.Scale(domain=[0,1])),
                color='type:N',tooltip=['event_id','type','amount','risk_score'],
            ).properties(height=150)
            st.altair_chart(chart)
# AFTER END — 9C.4

# BEFORE Start — 9C.5
# KPI và pipeline luôn đẩy bảng xuống phía dưới.
# BEFORE END — 9C.5
# AFTER Start — 9C.5: không gian bảng/inspector, dải trạng thái gọn ở cuối.
def render(s,page):
    st.caption(f"{s.run_id} · {s.status.upper()} · cập nhật mỗi 2 giây")
    if page==PAGES[3]:
        main,side=st.columns([4,1])
        with main:ledger(s)
        with side:
            with st.container(border=True):inspector(s)
        context(s)
    else:render_page(s,page)
    st.caption(f"TRẠNG THÁI RUN · cycle {s.run.get('source_cycle',1)} · dòng {fmt_int(s.run.get('source_row'))}/{fmt_int(s.run.get('dataset_rows'))} · tiến độ {min(float(s.run.get('source_progress_pct',0)),1.0):.2%}")
    items=[('Nguồn đã phát',fmt_int(s.emitted),None),('Spark đã xử lý',fmt_int(s.processed),f'{fmt_int(s.lag)} đang chờ'),
        ('Fraud alerts',fmt_int(s.alerts_count),fmt_pct(s.model['Alert rate'])),
        ('Ingest hiện tại',f"{fmt_float(s.run.get('instant_emission_rate'))} ev/s",None),
        ('Processing throughput',f"{fmt_float(s.latest_metric.get('processing_throughput'))} ev/s",None),
        ('End-to-end latency p95',f"{fmt_float(s.latest_metric.get('latency_p95_ms'),0)} ms",None)]
    for col,(label,value,delta) in zip(st.columns(6),items):col.metric(label,value,delta=delta)
# AFTER END — 9C.5
