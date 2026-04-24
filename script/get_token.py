import teslapy

# 請輸入你的 Tesla 帳號 Email（或設定環境變數 TESLA_EMAIL）
import os
email = os.environ.get('TESLA_EMAIL') or input('請輸入你的 Tesla 帳號 Email: ').strip()

# 初始化 Tesla 類，這會自動處理授權流程
with teslapy.Tesla(email) as tesla:
    if not tesla.authorized:
        # 1. 獲取授權 URL
        auth_url = tesla.authorization_url()
        print("\n" + "="*60)
        print("請在瀏覽器中打開以下網址並登入你的 Tesla 帳號:")
        print(auth_url)
        print("="*60)
        
        # 2. 獲取回傳的 URL
        print("\n登入成功後，頁面會顯示 'Page Not Found'。")
        redir_url = input("請複製瀏覽器地址欄中的完整網址 (URL) 並貼到這裡: ").strip()
        
        # 3. 換取 Token
        tesla.fetch_token(authorization_response=redir_url)

    # 4. 輸出結果
    if tesla.authorized:
        token_data = tesla.token
        print("\n" + "✅ 授權成功！".center(50, "-"))
        print(f"Access Token:  {token_data.get('access_token')}")
        print(f"Refresh Token: {token_data.get('refresh_token')}")
        print("-" * 50)
        print("請將上述兩串 Token 貼回 TeslaMate (Port 4000) 的介面中。")
    else:
        print("\n❌ 授權失敗，請檢查 URL 是否複製完整。")
