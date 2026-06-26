import pandas as pd

a = pd.read_excel("store_a.xlsx").rename(
    columns={"날짜": "날짜", "품목": "상품", "금액": "금액"}
)
a["지점"] = "A"

b = pd.read_excel("store_b.xlsx").rename(
    columns={"거래일": "날짜", "상품명": "상품", "매출(원)": "금액"}
)
b["지점"] = "B"

merged = pd.concat([a, b], ignore_index=True)
merged["날짜"] = pd.to_datetime(merged["날짜"], format="mixed").dt.strftime("%Y-%m-%d")
merged = merged[["날짜", "지점", "상품", "금액"]]

merged.to_excel("merged_sales.xlsx", index=False)
print(f"{len(merged)} rows merged -> merged_sales.xlsx")
