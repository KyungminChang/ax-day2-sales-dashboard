from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="매출 대시보드", page_icon="📊", layout="wide")

DATA_PATH = Path(__file__).parent / "merged_sales.xlsx"

st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    div[data-testid="stMetric"] {
        background-color: #F4F6FA;
        border: 1px solid #EAECF1;
        border-radius: 12px;
        padding: 20px 24px;
    }
    div[data-testid="stMetricValue"] {
        color: #FF6B6B;
    }
    h1 {
        font-weight: 700;
        padding-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780


@st.cache_data(ttl=600)
def load_weather() -> dict:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": SEOUL_LAT,
            "longitude": SEOUL_LON,
            "current": "temperature_2m",
            "hourly": "temperature_2m",
            "timezone": "Asia/Seoul",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data
def load_data(file) -> pd.DataFrame:
    data = pd.read_excel(file)
    data = data.rename(columns={"금액": "매출액"})
    data["날짜"] = pd.to_datetime(data["날짜"])
    return data[["날짜", "지점", "상품", "매출액"]]


data_file = None

if DATA_PATH.exists():
    data_file = DATA_PATH
else:
    st.title("매출 대시보드")
    st.info(
        f"이 앱은 공개 저장소로 배포되어 민감한 매출 데이터(`{DATA_PATH.name}`)는 "
        "저장소에 포함하지 않았습니다.\n\n"
        "로컬에서는 `merge_sales.py`를 먼저 실행해 같은 폴더에 파일을 생성하거나, "
        "아래에 직접 업로드해주세요."
    )
    data_file = st.file_uploader(f"{DATA_PATH.name} 업로드", type="xlsx")
    if data_file is None:
        st.stop()

df = load_data(data_file)

st.title("매출 대시보드")

st.subheader("🌤 서울 날씨")
try:
    weather = load_weather()
    current_temp = weather["current"]["temperature_2m"]
    current_unit = weather["current_units"]["temperature_2m"]

    hourly_weather = pd.DataFrame(
        {
            "시간": pd.to_datetime(weather["hourly"]["time"]),
            "기온": weather["hourly"]["temperature_2m"],
        }
    )
    today = pd.Timestamp.now(tz="Asia/Seoul").tz_localize(None).normalize()
    hourly_weather = hourly_weather[hourly_weather["시간"].dt.normalize() == today]

    st.metric("현재 기온", f"{current_temp:.1f}{current_unit}")

    weather_chart = (
        alt.Chart(hourly_weather)
        .mark_line(point=True, strokeWidth=3, color="#4D96FF")
        .encode(
            x=alt.X("시간:T", title="시간", axis=alt.Axis(format="%H시")),
            y=alt.Y("기온:Q", title="기온 (°C)"),
            tooltip=[alt.Tooltip("시간:T", format="%H시"), "기온"],
        )
        .properties(height=300)
    )
    st.altair_chart(weather_chart, width="stretch")
except requests.exceptions.RequestException:
    st.warning("날씨 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")

min_date = df["날짜"].min().date()
max_date = df["날짜"].max().date()

with st.sidebar:
    st.header("필터")

    branch_options = sorted(df["지점"].unique())
    selected_branches = st.multiselect(
        "지점 선택", options=branch_options, default=branch_options
    )

    date_range = st.date_input(
        "날짜 범위",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered_df = df[
    df["지점"].isin(selected_branches)
    & (df["날짜"].dt.date >= start_date)
    & (df["날짜"].dt.date <= end_date)
]

total_sales = filtered_df["매출액"].sum()
st.metric("전체 매출 합계", f"{total_sales:,.0f} 원")

st.subheader("지점별 월별 매출 추이")
monthly_sales = filtered_df.copy()
monthly_sales["월"] = monthly_sales["날짜"].dt.to_period("M").dt.to_timestamp()
monthly_sales = monthly_sales.groupby(["월", "지점"], as_index=False)["매출액"].sum()
monthly_sales["매출액_표시"] = monthly_sales["매출액"].apply(lambda x: f"{x:,.0f} 원")

monthly_chart = (
    alt.Chart(monthly_sales)
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("월:T", title="월"),
        y=alt.Y(
            "매출액:Q",
            title="매출 합계 (원)",
            axis=alt.Axis(labelExpr="format(datum.value, ',') + ' 원'"),
        ),
        color=alt.Color(
            "지점:N",
            scale=alt.Scale(range=["#FF6B6B", "#4D96FF"]),
            legend=alt.Legend(title="지점"),
        ),
        tooltip=["월", "지점", alt.Tooltip("매출액_표시:N", title="매출액")],
    )
    .properties(height=350)
)
st.altair_chart(monthly_chart, width="stretch")

st.subheader("상품별 매출 표")
product_sales = (
    filtered_df.groupby("상품")["매출액"]
    .sum()
    .reset_index()
    .sort_values("매출액", ascending=False)
    .reset_index(drop=True)
)
st.dataframe(
    product_sales,
    width="stretch",
    column_config={
        "매출액": st.column_config.ProgressColumn(
            "매출액",
            format="%d 원",
            min_value=0,
            max_value=int(product_sales["매출액"].max()),
        )
    },
)
