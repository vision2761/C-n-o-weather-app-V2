# app_V2.py —— 昆岛（Côn Đảo）气象系统 （最新版）
# 包含：天气预报 / METAR解析 / 降水过程记录（含强度时间序列图）/ 历史分析

import streamlit as st
import pandas as pd
import re
from datetime import datetime, time

from db_V2 import (
    init_db,
    insert_forecast,
    get_forecasts,
    insert_metar,
    get_recent_metars,
    insert_rain_event,
    get_rain_events,
    get_rain_stats_by_day,
)
from metar_parser_V2 import parse_metar

st.set_page_config(page_title="昆岛机场气象记录系统", layout="wide")

# 初始化数据库
init_db()

# ============================================================
#  1）天气预报
# ============================================================
def page_forecast():
    st.header("📋 昆岛天气预报录入与查询")

    st.subheader("录入天气预报（最低温 / 最高温）")

    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("预报日期")
    with c2:
        wind = st.text_input("风向/风速（如：030/05，30° 风速 5 m/s）")

    c3, c4 = st.columns(2)
    with c3:
        temp_min = st.number_input("最低气温 (℃)", value=25.0, format="%.1f")
    with c4:
        temp_max = st.number_input("最高气温 (℃)", value=28.0, format="%.1f")

    weather = st.text_input("天气现象（自由填写，如：分散对流伴短时阵雨）")

    if st.button("保存预报记录"):
        if temp_max < temp_min:
            st.warning("最高温不能低于最低温")
        else:
            insert_forecast(str(date_val), wind, temp_min, temp_max, weather)
            st.success("✅ 天气预报已保存")

    st.markdown("---")
    st.subheader("📑 历史天气预报查询")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期", key="fc_start")
    with s2:
        end = st.date_input("结束日期", key="fc_end")

    if st.button("查询历史预报"):
        rows = get_forecasts(str(start), str(end))
        if not rows:
            st.info("无记录")
        else:
            df = pd.DataFrame(
                rows,
                columns=["日期", "风向风速", "最低温", "最高温", "天气现象"],
            )
            st.dataframe(df, use_container_width=True)

            # 平均温度图
            df["日期"] = pd.to_datetime(df["日期"])
            df["平均温"] = (df["最低温"] + df["最高温"]) / 2
            st.line_chart(df.set_index("日期")["平均温"], height=300)

# ============================================================
#  2）METAR 解析
# ============================================================
def page_metar():
    st.header("🛬 METAR/SPECI 报文解析")

    raw = st.text_area("输入 METAR 报文：", height=120)

    if st.button("解析并保存"):
        if not raw.strip():
            st.warning("请输入报文")
        else:
            rec = parse_metar(raw)
            insert_metar(rec)
            st.success("解析成功")
            st.json(rec)

    st.markdown("---")
    st.subheader("📑 最近解析记录")

    rows = get_recent_metars(100)
    if rows:
        df = pd.DataFrame(
            rows,
            columns=[
                "报文时间",
                "站号",
                "原始报文",
                "风向",
                "风速",
                "阵风",
                "能见度",
                "温度",
                "露点",
                "天气",
                "是否雨",
                "雨型",
                "云量1",
                "云高1",
                "云量2",
                "云高2",
                "云量3",
                "云高3",
            ],
        )
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无 METAR 数据")

# ============================================================
#  3）降水过程记录（含强度时间序列图）
# ============================================================
def page_rain():
    st.header("🌧 降水过程记录（精确到分钟）")

    st.subheader("记录降水变化节点")

    # 日期 + 手动时间输入
    c1, c2 = st.columns(2)
    with c1:
        date_val = st.date_input("日期")
    with c2:
        time_input = st.text_input("时间（HH:MM，例如：12:06）")
    
    # 合成最终时间格式
    time_str = f"{date_val} {time_input}"


    rain_level = st.selectbox(
        "雨强",
        ["毛毛雨", "小雨", "中雨", "大雨", "暴雨", "雷阵雨", "雨停"],
    )

    rain_code = st.text_input("对应报文代码（如 -RA、RA、+RA、TSRA 等，可选）")
    note = st.text_input("备注（可选）")

    if st.button("保存记录"):
        try:
            datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            insert_rain_event(time_str, rain_level, rain_code, note)
            st.success(f"记录成功：{time_str} — {rain_level}")
        except:
            st.error("时间格式错误，应为 YYYY-MM-DD HH:MM")

    st.markdown("---")
    st.subheader("📑 历史降水过程查询（含降雨强度图）")

    d1, d2 = st.columns(2)
    with d1:
        start = st.date_input("开始日期", key="rain_start")
    with d2:
        end = st.date_input("结束日期", key="rain_end")

    if st.button("查询降水历史"):
        rows = get_rain_events(str(start), str(end))
        if not rows:
            st.info("无记录")
            return

        df = pd.DataFrame(rows, columns=["时间", "雨强", "报文代码", "备注"])
        df = df.sort_values("时间")

        st.dataframe(df, use_container_width=True)

        # 映射雨强为数值
        strength_map = {
            "雨停": 0,
            "毛毛雨": 0.5,
            "小雨": 1,
            "中雨": 2,
            "大雨": 3,
            "暴雨": 4,
            "雷阵雨": 3.5,
        }

        df["强度"] = df["雨强"].map(strength_map)
        df["时间"] = pd.to_datetime(df["时间"])

        df_chart = df.set_index("时间")

        st.line_chart(df_chart["强度"], height=280)
        st.caption("📈 上图为降水强度随时间变化趋势（雨停强度为0）")

# ============================================================
#  4）历史分析
# ============================================================
def page_analysis():
    st.header("📊 降水统计分析")

    s1, s2 = st.columns(2)
    with s1:
        start = st.date_input("开始日期", key="ana_start")
    with s2:
        end = st.date_input("结束日期", key="ana_end")

    if st.button("生成统计图"):
        rows = get_rain_stats_by_day(str(start), str(end))
        if not rows:
            st.info("无记录")
            return

        df = pd.DataFrame(rows, columns=["日期", "次数"])
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.set_index("日期")

        st.bar_chart(df, height=350)
        st.dataframe(df.reset_index(), use_container_width=True)

# ============================================================
# 主程序入口
# ============================================================
def main():
    st.title("✈ 昆岛机场气象记录与分析系统 Côn Đảo Weather System")

    page = st.sidebar.radio(
        "功能选择",
        ["昆岛天气预报", "METAR 报文解析", "降水记录", "历史分析"],
    )

    if page == "昆岛天气预报":
        page_forecast()
    elif page == "METAR 报文解析":
        page_metar()
    elif page == "降水记录":
        page_rain()
    elif page == "历史分析":  
        page_analysis()

if __name__ == "__main__":
    main()
