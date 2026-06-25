// 備份加密（M6）— 選擇性 AES-GCM 加密，金鑰以 PBKDF2 由使用者密碼導出。
// 用瀏覽器內建 Web Crypto（GitHub Pages 為 HTTPS，iOS Safari / Android Chrome 皆支援）。
//
// 加密檔格式（位元組）：
//   magic(4) "AOB1" | salt(16) | iv(12) | ciphertext(AES-GCM，含驗證標籤)
// 明文備份則直接是 zip 位元組（開頭為 "PK"）。匯入時以此 magic 自動辨識是否加密。

const MAGIC = new Uint8Array([0x41, 0x4f, 0x42, 0x31]) // "AOB1"
const PBKDF2_ITER = 150000

function hasMagic(bytes) {
  if (bytes.length < MAGIC.length) return false
  for (let i = 0; i < MAGIC.length; i++) if (bytes[i] !== MAGIC[i]) return false
  return true
}

export function isEncrypted(bytes) {
  return hasMagic(bytes)
}

async function deriveKey(password, salt) {
  const enc = new TextEncoder()
  const baseKey = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITER, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

// 明文 zip 位元組 → 加密位元組（含 magic/salt/iv）。
export async function encryptBytes(plainBytes, password) {
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const key = await deriveKey(password, salt)
  const cipher = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, plainBytes))
  const out = new Uint8Array(MAGIC.length + salt.length + iv.length + cipher.length)
  let o = 0
  out.set(MAGIC, o); o += MAGIC.length
  out.set(salt, o); o += salt.length
  out.set(iv, o); o += iv.length
  out.set(cipher, o)
  return out
}

// 加密位元組 → 明文 zip 位元組。密碼錯誤時 AES-GCM 驗證失敗會丟例外。
export async function decryptBytes(encBytes, password) {
  if (!hasMagic(encBytes)) throw new Error('不是有效的加密備份檔')
  let o = MAGIC.length
  const salt = encBytes.slice(o, o + 16); o += 16
  const iv = encBytes.slice(o, o + 12); o += 12
  const cipher = encBytes.slice(o)
  const key = await deriveKey(password, salt)
  try {
    return new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, cipher))
  } catch {
    throw new Error('密碼錯誤或檔案毀損，無法解密。')
  }
}
