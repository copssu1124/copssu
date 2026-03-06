import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

cid = os.getenv("CLIENT_ID_1")
csec = os.getenv("CLIENT_SECRET_1")

headers = {
    "X-Naver-Client-Id": cid.strip(),
    "X-Naver-Client-Secret": csec.strip(),
}

res_shop = requests.get("https://openapi.naver.com/v1/search/shop.json?query=test&display=1", headers=headers)
print("Shop Headers:")
for k, v in res_shop.headers.items():
    print(f"{k}: {v}")
