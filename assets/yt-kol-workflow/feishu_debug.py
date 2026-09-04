import requests, json, os
# 凭据从环境变量读取（.env 示例见 assets/yt-kol-workflow/.env.example），勿提交真实值
APP_ID=os.environ.get("FEISHU_APP_ID",""); APP_SECRET=os.environ.get("FEISHU_APP_SECRET","")
BASE=os.environ.get("FEISHU_BASE_TOKEN",""); TBL="tbl1opmlkmE3veas"
r=requests.post(f"https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id":APP_ID,"app_secret":APP_SECRET},timeout=20)
H={"Authorization":f"Bearer {r.json()['tenant_access_token']}","Content-Type":"application/json"}
URL=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE}/tables/{TBL}"

# create a throwaway field then delete it
j=requests.post(URL+"/fields", headers=H, json={"field_name":"_dbg_del","type":1}, timeout=30).json()
fid=j["data"]["field"]["field_id"]
print("created", fid)
resp=requests.delete(URL+f"/fields/{fid}", headers=H, timeout=30)
print("DELETE status", resp.status_code, "body", resp.text[:200])
try:
    print("  json:", resp.json())
except: pass
