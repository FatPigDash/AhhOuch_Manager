// 用 Node.js 內建模組產生 PWA 所需的 PNG 圖示（純色底＋單字母，不需額外套件）
import { deflateSync } from 'zlib'
import { writeFileSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dir = dirname(fileURLToPath(import.meta.url))
const publicDir = join(__dir, '..', 'public')
mkdirSync(publicDir, { recursive: true })

function crc32(buf) {
  if (!crc32._t) {
    crc32._t = Array.from({ length: 256 }, (_, i) => {
      let c = i
      for (let k = 0; k < 8; k++) c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1
      return c >>> 0
    })
  }
  let crc = 0xffffffff
  for (const b of buf) crc = (crc32._t[(crc ^ b) & 0xff] ^ (crc >>> 8)) >>> 0
  return (crc ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const t = Buffer.from(type)
  const d = Buffer.isBuffer(data) ? data : Buffer.from(data)
  const len = Buffer.allocUnsafe(4); len.writeUInt32BE(d.length)
  const crcIn = Buffer.concat([t, d])
  const crcBuf = Buffer.allocUnsafe(4); crcBuf.writeUInt32BE(crc32(crcIn))
  return Buffer.concat([len, t, d, crcBuf])
}

// 產生單色 PNG（深藍色 #102a43）
function solidPNG(size) {
  const [R, G, B] = [16, 42, 67]          // #102a43
  const rowLen = 1 + size * 3             // filter byte + RGB per pixel
  const raw = Buffer.alloc(size * rowLen) // filter byte = 0 (None) per row
  for (let y = 0; y < size; y++) {
    const row = y * rowLen
    for (let x = 0; x < size; x++) {
      raw[row + 1 + x * 3]     = R
      raw[row + 1 + x * 3 + 1] = G
      raw[row + 1 + x * 3 + 2] = B
    }
  }
  const ihdr = Buffer.allocUnsafe(13)
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8; ihdr[9] = 2 // bit depth 8, RGB
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

const sizes = { 'icon-512.png': 512, 'icon-192.png': 192, 'apple-touch-icon.png': 180 }
for (const [name, size] of Object.entries(sizes)) {
  writeFileSync(join(publicDir, name), solidPNG(size))
  console.log(`✓ public/${name} (${size}×${size})`)
}
