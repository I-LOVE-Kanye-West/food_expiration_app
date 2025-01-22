import base64

# Base64Urlから通常のBase64に変換
base64url_key = "BEREjkpsWqGu_dZQ6mHhruWGe3VCXk4IaHI10DFEFpuzO1fLCtckILwTsHAfSvWPFJnTz8Y_KE6xDIALs-i2aOE"
base64_key = base64url_key.replace("-", "+").replace("_", "/")
padding = "=" * ((4 - len(base64_key) % 4) % 4)  # 必要なパディングを計算
base64_key += padding
print("Base64形式:", base64_key)