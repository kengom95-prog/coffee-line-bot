import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import anthropic

app = Flask(__name__)

configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """あなたはコーヒーの専門家です。
ユーザーがコーヒーの産地や種類を教えてくれたら、以下を日本語で答えてください：

① おすすめ焙煎度（浅煎り／中煎り／深煎りなど理由も一言）
② 味の特徴（酸味・苦味・甘み・香りを具体的に）
③ おすすめ粒度（細挽き／中挽き／粗挽きなど）
④ ハンドドリップレシピ
   - 豆の量
   - お湯の温度
   - 蒸らし時間
   - 総抽出時間
   - お湯の量（出来上がり量）

コーヒー以外の話題には「コーヒーの産地と種類を教えてください☕」と返してください。
回答はスマホで読みやすいよう、改行を適切に使ってください。"""


@app.route("/")
def health():
    return "Coffee Bot OK", 200


@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_text}],
    )

    reply_text = response.content[0].text

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
