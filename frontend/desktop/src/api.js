// API 介面（Local-First）— 全部操作改為本機 IndexedDB，無後端呼叫

import * as db from './db.js'

export const api = {
  meta: () => Promise.resolve({ title: 'AhhOuch_Manager v2.1.0' }),

  // ===== 美容師資訊卡片 =====
  listCadreCards:   ()           => db.listCards(),
  createCadreCard:  (name)       => db.createCard(name),
  getCadreCard:     (id)         => db.getCard(id),
  updateCadreCard:  (id, data)   => db.updateCard(id, data),
  deleteCadreCard:  (id)         => db.deleteCard(id),
  uploadCadreImage: (cardId, file)    => db.addImage(cardId, file),
  setCadreCover:    (imageId)    => db.setCover(imageId),
  deleteCadreImage: (imageId)    => db.deleteImage(imageId),
  publishText: (cardId, variant) => db.cardPublishText(cardId, variant).then(text => ({ text })),

  // ===== 班表 =====
  listSchedules:       ()                    => db.listSchedules(),
  createSchedule:      (title = '')          => db.createSchedule(title),
  getSchedule:         (id)                  => db.getSchedule(id),
  updateSchedule:      (id, data)            => db.updateSchedule(id, data),
  deleteSchedule:      (id)                  => db.deleteSchedule(id),
  addEntry:            (scheduleId, cardId)  => db.addEntry(scheduleId, cardId),
  updateEntry:         (entryId, data)       => db.updateEntry(entryId, data),
  deleteEntry:         (entryId)             => db.deleteEntry(entryId),
  shiftSlots:          (start)               => Promise.resolve({ slots: db.calcShiftSlots(start) }),
  schedulePublishText: (id)                  => db.schedulePublishText(id).then(text => ({ text })),
  markSchedulePublished: (id)                => db.markSchedulePublished(id),

  // ===== 文字模板 =====
  listTextTemplates:   (kind) => db.listTextTemplates(kind),
  createTextTemplate:  (data) => db.createTextTemplate(data),
  updateTextTemplate:  (id, data) => db.updateTextTemplate(id, data),
  deleteTextTemplate:  (id) => db.deleteTextTemplate(id),

  // 發布改由各視窗以 Web Share API（src/share.js）在使用者手勢中直接呼叫（M4）。
}
