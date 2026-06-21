# Telegram 



## 申請機器人

請按照以下步驟操作，大約 2 分鐘內就能拿到你的機器人金鑰（Token）。

**1.尋找官方機器人管家 @BotFather：**請認明藍色勾勾認證標章。

打開你的 Telegram，在上方搜尋列輸入 `@BotFather`。

> **⚠️ 注意：** 網路上有很多山寨帳號。請務必認明名稱旁有**藍色官方認證勾勾**、且使用者名稱完全一致的才是正牌的 BotFather。

**2.啟動對話並輸入建立指令：**開啟新機器人流程。

點擊進入與 @BotFather 的對話視窗，按下底部的 **Start**（或手動輸入 `/start`）。

接著，在對話框輸入並發送指令：

```
/newbot
```

**3.設定機器人的「顯示名稱」 (Display Name)：**這是大家在聊天介面看到的名稱。

BotFather 會回覆你 "Alright, a new bot. How are we going to call it?..."。

這時候請輸入你想幫機器人取的**顯示名稱**（允許中文、英文、空格，之後隨時可以修改）。

- *例如：* `我的軟體推播助手`

**4.設定機器人的「使用者名稱」 (Username)：**這是全 Telegram 唯一的 ID，結尾必須是 bot。

BotFather 會接著要求 "Now let's choose a username for your bot..."。

請輸入機器人的 **Username**（只能是英文、數字、底線，且**結尾必須是 bot 或 _bot**，不可重複）。

- *例如：* `my_software_notification_bot`

**5.獲取機器人金鑰 (API Token)：**請妥善保管此字串。

如果名稱沒有重複，BotFather 就會發送一封成功訊息。

訊息中會包含一段類似這樣的程式碼字串：

```
123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

**這串 HTTP API Token 就是你的機器人金鑰。** 請將它複製並妥善保存，這就是你接下來要填入軟體中的核心資訊。



## 獲取群組的 Chat ID

由於 Telegram 官方為了隱私，預設不會在介面上顯示群組 ID，你可以透過以下最簡單的方法取得：

1. **邀請機器人：** 把你剛剛建好的機器人拉進你的目標群組中。

2. **設定權限：** 給予機器人管理員權限

   如果你未來的軟體需要常常推播，建議直接給它權限。

   在群組設定中，把你的機器人升級為「**管理員（Administrator）**」。

3. **在群組發送任意訊息：** 在該群組隨便打個字（例如：`test`）。

4. **透過瀏覽器查詢：** 打開瀏覽器，將網址列替換成以下網址（將 `<你的機器人金鑰>` 換成剛剛步驟 5 拿到那串），然後按下 Enter：

   Plaintext

   ```
   https://api.telegram.org/bot<你的機器人金鑰>/getUpdates
   ```

```
5. **尋找 ID：** 網頁會顯示一串 JSON 格式的文字。在裡面尋找 `"chat"` 物件，你會看到 `"id": -100xxxxxxxxxx`。這個**帶有負號的長數字**就是你群組的 **Chat ID**。

把這兩個欄位（Token 與 Chat ID）記下來，填入你的軟體中，就可以開始測試發送訊息了！

<FollowUp label="需要我用你熟悉的程式語言（如 Python、C#）寫一段發送訊息的範例程式碼嗎？" query="請
```