// 上次備份時間（M6）— 存 localStorage（裝置本機、與業務資料分離），供每月提醒橫幅判斷。

const KEY = 'ahhouch_last_backup_at'
const MONTH_DAYS = 30

export function getLastBackup() {
  return localStorage.getItem(KEY) || null
}

export function setLastBackupNow() {
  localStorage.setItem(KEY, new Date().toISOString())
}

// 是否該提醒備份：從未備份、或距上次超過一個月。
export function backupOverdue() {
  const last = getLastBackup()
  if (!last) return true
  return Date.now() - new Date(last).getTime() > MONTH_DAYS * 86400000
}
